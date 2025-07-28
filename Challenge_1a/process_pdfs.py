# Adobe Hackathon 2025 - Challenge 1a: PDF Outline Extractor
# Docker Container Version - Digital Text Only
#
# This script processes all PDFs from /app/input and generates JSON outlines in /app/output
# Optimized for performance: ≤10 seconds for 50-page PDFs, ≤16GB RAM, CPU-only

import fitz  # PyMuPDF
import numpy as np
import os
import json
from pathlib import Path
import time
import traceback
import re
import sys

class TextBlock:
    def __init__(self, text, bbox, page_num, size, is_bold=False):
        self.text = text.strip()
        self.bbox = fitz.Rect(bbox)
        self.page_num = page_num
        self.size = round(size, 2)
        self.is_bold = is_bold
        self.is_heading = False
        self.heading_level = None

    def __repr__(self):
        return f"TextBlock(page={self.page_num + 1}, text='{self.text[:30]}...', size={self.size}, bold={self.is_bold})"

class PDFOutlineExtractor:
    """
    High-performance PDF outline extractor optimized for Adobe Hackathon constraints.
    """
    def __init__(self, char_threshold=50, gap_threshold=0.3, line_merge_threshold=0.5):
        self.char_threshold = char_threshold
        self.gap_threshold = gap_threshold
        self.line_merge_threshold = line_merge_threshold

    def _is_bold(self, font_name):
        return any(x in font_name.lower() for x in ['bold', 'black', 'heavy', 'condb'])

    def _parse_digital_page(self, page, page_num):
        """Fast text extraction optimized for performance."""
        blocks = []
        try:
            text_page = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)
            for block in text_page["blocks"]:
                if block["type"] == 0:  # Text block
                    for line in block["lines"]:
                        if not line["spans"]: 
                            continue
                        full_text = " ".join(s["text"].strip() for s in line["spans"] if s["text"].strip())
                        if not full_text: 
                            continue
                        
                        line_bbox = fitz.Rect()
                        for span in line["spans"]: 
                            line_bbox.include_rect(span["bbox"])
                        
                        first_span = line["spans"][0]
                        line_size = first_span["size"]
                        line_is_bold = self._is_bold(first_span["font"]) or (first_span['flags'] & 2**4)
                        blocks.append(TextBlock(full_text, tuple(line_bbox), page_num, line_size, line_is_bold))
        except Exception as e:
            print(f"      - Warning: Error parsing page {page_num + 1}: {e}")
        return blocks

    def _group_lines_into_semantic_blocks(self, blocks):
        """Memory-efficient line grouping."""
        if not blocks: 
            return []
        
        grouped_blocks = []
        current_group = [blocks[0]]
        
        for i in range(1, len(blocks)):
            prev_block, current_block = current_group[-1], blocks[i]
            same_page = prev_block.page_num == current_block.page_num
            similar_size = abs(prev_block.size - current_block.size) < 1.0
            vertical_gap = current_block.bbox.y0 - prev_block.bbox.y1
            is_close = 0 <= vertical_gap < prev_block.size * self.line_merge_threshold
            
            if same_page and similar_size and is_close:
                current_group.append(current_block)
            else:
                # Process current group
                if len(current_group) > 1:
                    merged_text = " ".join(b.text for b in current_group)
                    merged_bbox = fitz.Rect()
                    for b in current_group: 
                        merged_bbox.include_rect(b.bbox)
                    first_block = current_group[0]
                    grouped_blocks.append(TextBlock(merged_text, merged_bbox, first_block.page_num, first_block.size, first_block.is_bold))
                else:
                    grouped_blocks.append(current_group[0])
                current_group = [current_block]
        
        # Handle last group
        if len(current_group) > 1:
            merged_text = " ".join(b.text for b in current_group)
            merged_bbox = fitz.Rect()
            for b in current_group: 
                merged_bbox.include_rect(b.bbox)
            first_block = current_group[0]
            grouped_blocks.append(TextBlock(merged_text, merged_bbox, first_block.page_num, first_block.size, first_block.is_bold))
        else:
            grouped_blocks.append(current_group[0])
            
        return grouped_blocks

    def _detect_headings(self, all_blocks):
        """Optimized heading detection with performance focus."""
        if not all_blocks:
            return

        sorted_blocks = sorted(all_blocks, key=lambda b: (b.page_num, b.bbox.y0))
        semantic_blocks = self._group_lines_into_semantic_blocks(sorted_blocks)
        num_blocks = len(semantic_blocks)
        
        # Fast average size calculation
        body_text_sizes = [b.size for b in semantic_blocks if len(b.text.split()) > 3 and b.size > 6]
        avg_size = np.mean(body_text_sizes) if body_text_sizes else 12.0
        
        # Precompile regex patterns for performance
        skip_patterns = [
            re.compile(r'^\s*RSVP[:\-]?', re.IGNORECASE),
            re.compile(r'^\s*www\.[\w\.-]+\.[a-z]{2,}$', re.IGNORECASE),
            re.compile(r'^\s*https?://[\w\.-]+', re.IGNORECASE),
            re.compile(r'^\s*email[:\-]?\s*[\w\.-]+@[\w\.-]+$', re.IGNORECASE),
            re.compile(r'^\s*phone[:\-]?\s*\+?\d[\d\-\s]+$', re.IGNORECASE),
            re.compile(r'^\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$', re.IGNORECASE),
            re.compile(r'^\s*(tel|fax)[:\-]?\s*\+?\d[\d\-\s]+$', re.IGNORECASE),
            re.compile(r'^\s*(address|location)[:\-]?\s*.*$', re.IGNORECASE),
            re.compile(r'^\s*\d{1,3}(\.\d+)*\s*$', re.IGNORECASE),
            re.compile(r'^\s*page\s*\d+\s*$', re.IGNORECASE),
            re.compile(r'^\s*(copyright|©)\s*.*$', re.IGNORECASE),
            re.compile(r'^\s*(confidential|disclaimer).*$', re.IGNORECASE),
            re.compile(r'^\s*(figure|table)\s*\d+\s*[:\-]?.*$', re.IGNORECASE),
            re.compile(r'^\s*(date|time)[:\-]?\s*.*$', re.IGNORECASE),
            re.compile(r'^\s*contact\s*(us)?[:\-]?\s*.*$', re.IGNORECASE),
        ]
        
        months = {'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'}
        number_pattern = re.compile(r'^\d+(\.\d+)*\s+')
        
        potential_headings = []
        for i, block in enumerate(semantic_blocks):
            text_content = block.text.strip()
            
            # Quick filters
            if text_content.replace('.', '', 1).isdigit() and len(text_content.split()) < 2:
                continue
            
            if any(pattern.match(text_content) for pattern in skip_patterns):
                continue
            
            # Date filter
            words = text_content.lower().split()
            if any(word.strip('.,') in months for word in words) and any(word.isdigit() and len(word) == 4 for word in words):
                continue

            # Heading logic
            is_exceptionally_large = block.size > avg_size * 1.8
            is_moderately_large = block.size > avg_size * 1.15
            is_short = len(block.text.split()) < 20 and len(block.text) < 200
            starts_with_number = number_pattern.match(block.text)
            
            if not (is_exceptionally_large or (is_moderately_large and is_short) or (block.is_bold and is_short) or starts_with_number):
                continue

            # Gap detection
            is_last_on_page = (i + 1 == num_blocks) or (semantic_blocks[i+1].page_num != block.page_num)
            if not is_exceptionally_large and not is_last_on_page:
                next_block = semantic_blocks[i+1]
                vertical_gap = next_block.bbox.y0 - block.bbox.y1
                min_required_gap = block.size * self.gap_threshold
                if vertical_gap < min_required_gap:
                    continue
            
            block.is_heading = True
            potential_headings.append(block)

        if not potential_headings:
            return

        # Fast heading level assignment
        heading_sizes = sorted(list(set(h.size for h in potential_headings)), reverse=True)
        size_levels = []
        if heading_sizes:
            current_level_avg = heading_sizes[0]
            current_level_count = 1
            for size in heading_sizes[1:]:
                if (current_level_avg - size) < 1.5:
                    current_level_avg = (current_level_avg * current_level_count + size) / (current_level_count + 1)
                else:
                    size_levels.append(current_level_avg)
                    current_level_avg = size
                    current_level_count = 1
            size_levels.append(current_level_avg)

        for block in potential_headings:
            level_idx = min(range(len(size_levels)), key=lambda i: abs(size_levels[i] - block.size))
            block.heading_level = f"H{level_idx + 1}"

    def process(self, pdf_path):
        """Main processing function optimized for Docker container."""
        start_time = time.time()
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"   ❌ Error opening PDF: {e}", file=sys.stderr)
            return None

        all_blocks = []
        total_pages = len(doc)
        
        for page_num, page in enumerate(doc):
            page_text_length = len(page.get_text())
            if page_text_length < self.char_threshold:
                continue
            else:
                page_blocks = self._parse_digital_page(page, page_num)
                all_blocks.extend(page_blocks)
            
            # Memory management for large PDFs
            if page_num % 10 == 0 and page_num > 0:
                import gc
                gc.collect()
        
        if not all_blocks:
            doc.close()
            return None
        
        self._detect_headings(all_blocks)

        outline = []
        for block in all_blocks:
            if block.is_heading:
                outline.append({
                    "level": block.heading_level,
                    "text": block.text,
                    "page": block.page_num + 1,
                })

        outline.sort(key=lambda x: x["page"])
        
        # Generate title
        title = doc.metadata.get("title")
        if not title and outline and outline[0]['level'] == 'H1':
            title = outline[0]['text']
        else:
            title = Path(pdf_path).stem.replace("_", " ").replace("-", " ").title()

        result = {
            "title": title,
            "outline": outline,
        }
        
        doc.close()
        
        processing_time = time.time() - start_time
        print(f"   ✅ Processed {total_pages} pages in {processing_time:.2f}s. Found {len(outline)} headings.")
        
        return result

def main():
    """Main Docker container entry point."""
    print("🚀 Adobe Hackathon 2025 - PDF Outline Extractor 🚀")
    print("=" * 55)
    
    input_dir = Path("/app/input")
    output_dir = Path("/app/output")
    
    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if not input_dir.exists():
        print(f"❌ Input directory {input_dir} not found!")
        sys.exit(1)
    
    pdf_files = list(input_dir.glob("*.pdf"))
    if not pdf_files:
        print(f"🤷 No PDF files found in {input_dir}")
        return
        
    print(f"📚 Found {len(pdf_files)} PDF(s) to process")
    
    extractor = PDFOutlineExtractor()
    processed_count = 0
    total_start_time = time.time()
    
    for pdf_file in pdf_files:
        print(f"\n📄 Processing: {pdf_file.name}")
        try:
            result = extractor.process(pdf_file)
            if result:
                output_filename = output_dir / f"{pdf_file.stem}.json"
                with open(output_filename, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"   💾 Saved: {output_filename}")
                processed_count += 1
            else:
                print(f"   ⚠️  No outline extracted from {pdf_file.name}")
        except Exception as e:
            print(f"   🔥 Error processing {pdf_file.name}: {e}", file=sys.stderr)
            traceback.print_exc()

    total_time = time.time() - total_start_time
    print(f"\n🎉 Processing complete!")
    print(f"   📊 Processed: {processed_count}/{len(pdf_files)} PDFs")
    print(f"   ⏱️  Total time: {total_time:.2f} seconds")
    print(f"   📁 Output directory: {output_dir}")

if __name__ == "__main__":
    main()
