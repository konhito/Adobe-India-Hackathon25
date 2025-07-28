import fitz  # PyMuPDF

def extract_text_sections(pdf_path):
    doc = fitz.open(pdf_path)
    sections = []
    
    title = doc.metadata.get("title") or "Untitled Document"
    font_stats = {}

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]

        for block in blocks:
            if "lines" not in block:
                continue
            for line in block["lines"]:
                line_text = ""
                for span in line["spans"]:
                    line_text += span["text"].strip() + " "
                    font_size = round(span["size"])
                    font_stats[font_size] = font_stats.get(font_size, 0) + 1

                line_text = line_text.strip()
                if len(line_text.split()) < 2:
                    continue  # likely not a real heading

                heading_level = classify_heading_level(span["size"], font_stats)
                if heading_level:
                    sections.append({
                        "title": line_text,
                        "text": extract_context(doc, page_num, line_text),
                        "page": page_num + 1,
                        "heading_level": heading_level
                    })
    return sections

def classify_heading_level(font_size, font_stats):
    # Dynamically define size thresholds
    if not font_stats:
        return None
    sorted_sizes = sorted(font_stats.items(), key=lambda x: -x[1])
    if len(sorted_sizes) < 2:
        return "H1"
    max_size = sorted_sizes[0][0]
    if font_size == max_size:
        return "H1"
    elif font_size >= max_size * 0.9:
        return "H2"
    elif font_size >= max_size * 0.8:
        return "H3"
    else:
        return None

def extract_context(doc, page_num, heading_text, context_lines=5):
    """Get some text below the heading to represent its content"""
    page = doc.load_page(page_num)
    full_text = page.get_text()
    lines = full_text.split('\n')

    for idx, line in enumerate(lines):
        if heading_text.strip().lower() in line.strip().lower():
            start = idx + 1
            end = min(start + context_lines, len(lines))
            return " ".join(lines[start:end]).strip()
    return ""
