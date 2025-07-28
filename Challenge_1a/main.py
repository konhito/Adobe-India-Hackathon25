# Adobe 1A Hackathon - PDF Outline Extractor (v5 - with Smarter Heading Detection)
#
# This script intelligently extracts a hierarchical outline from a PDF document.
#
# Key Features:
#   - Smart Processing: Prioritizes fast, native text extraction and uses OCR as a fallback.
#   - Advanced Heading Detection: Uses font size, weight, and vertical gap analysis.
#   - CORRECTED: Smarter Heuristics: Exceptionally large text is now correctly identified as a
#     heading, regardless of length, fixing previous errors.
#   - Line Consolidation: Groups horizontally separated text on the same vertical level.
#   - Structured Output: Generates a clean JSON file with the document title and outline.
#

import fitz  # PyMuPDF
import cv2
import numpy as np
import os
import json
from pathlib import Path
import time
import traceback
import re

# --- Optional Dependency: PaddleOCR for scanned pages ---
try:
    from paddleocr import PaddleOCR
    PADDLE_AVAILABLE = True
except ImportError:
    PADDLE_AVAILABLE = False
    print("⚠️  PaddleOCR not installed. OCR functionality for scanned PDFs will be disabled.")
    print("   To enable, run: pip install paddlepaddle-gpu paddleocr")

class TextBlock:
    def __init__(self, text, bbox, page_num, size, is_bold=False):
        self.text = text.strip()
        self.bbox = fitz.Rect(bbox)  # Ensure it's a fitz.Rect for easy manipulation
        self.page_num = page_num
        self.size = round(size, 2)
        self.is_bold = is_bold
        self.is_heading = False
        self.heading_level = None

    def __repr__(self):
        return f"TextBlock(page={self.page_num + 1}, text='{self.text[:30]}...', size={self.size}, bold={self.is_bold})"

class PDFOutlineExtractor:
    """
    Extracts a structured outline from a PDF file using advanced heuristics.
    """
    def __init__(self, char_threshold=100, gap_threshold=0.3, line_merge_threshold=0.5):
        self.ocr_model = None
        self.char_threshold = char_threshold
        self.gap_threshold = gap_threshold
        self.line_merge_threshold = line_merge_threshold

    def _lazy_load_ocr(self):
        """Loads PaddleOCR model on demand."""
        if not PADDLE_AVAILABLE:
            raise ImportError("PaddleOCR is required for processing scanned images but is not installed.")
        if self.ocr_model is None:
            print("   ⏳ Initializing OCR model (this may take a moment)...")
            self.ocr_model = PaddleOCR(use_angle_cls=False, lang="en", show_log=False)
            print("   ✅ OCR model loaded.")

    def _is_bold(self, font_name):
        return any(x in font_name.lower() for x in ['bold', 'black', 'heavy', 'condb'])

    def _parse_digital_page(self, page, page_num):
        """Extracts text by consolidating all spans on the same line into a single TextBlock."""
        blocks = []
        text_page = page.get_text("dict", flags=fitz.TEXTFLAGS_DICT)
        for block in text_page["blocks"]:
            if block["type"] == 0:  # This is a text block
                for line in block["lines"]:
                    if not line["spans"]: continue
                    full_text = " ".join(s["text"].strip() for s in line["spans"] if s["text"].strip())
                    if not full_text: continue
                    line_bbox = fitz.Rect()
                    for span in line["spans"]: line_bbox.include_rect(span["bbox"])
                    first_span = line["spans"][0]
                    line_size = first_span["size"]
                    line_is_bold = self._is_bold(first_span["font"]) or (first_span['flags'] & 2**4)
                    blocks.append(TextBlock(full_text, tuple(line_bbox), page_num, line_size, line_is_bold))
        return blocks
    
    def _parse_scanned_page(self, page, page_num):
        self._lazy_load_ocr()
        print(f"      - Rendering page {page_num + 1} for OCR (300 DPI)...")
        pix = page.get_pixmap(dpi=300)
        img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.h, pix.w, 3)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        print("      - Running OCR...")
        ocr_results = self.ocr_model.ocr(gray_img, cls=False)
        if not ocr_results or not ocr_results[0]: return []
        scale_x = page.rect.width / pix.w
        scale_y = page.rect.height / pix.h
        ocr_segments = []
        for line_data in ocr_results[0]:
            points, (text, confidence) = line_data
            if confidence < 0.8: continue
            bbox = (min(p[0] for p in points) * scale_x, min(p[1] for p in points) * scale_y,
                    max(p[0] for p in points) * scale_x, max(p[1] for p in points) * scale_y)
            height = bbox[3] - bbox[1]
            ocr_segments.append(TextBlock(text, bbox, page_num, height))
        return ocr_segments

    def _group_lines_into_semantic_blocks(self, blocks):
        """Merges consecutive lines into a single block if they are stylistically similar and close together."""
        if not blocks: return []
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
                if len(current_group) > 1:
                    merged_text = " ".join(b.text for b in current_group)
                    merged_bbox = fitz.Rect()
                    for b in current_group: merged_bbox.include_rect(b.bbox)
                    first_block = current_group[0]
                    grouped_blocks.append(TextBlock(merged_text, merged_bbox, first_block.page_num, first_block.size, first_block.is_bold))
                else:
                    grouped_blocks.append(current_group[0])
                current_group = [current_block]
        
        # Add the last group
        if len(current_group) > 1:
            merged_text = " ".join(b.text for b in current_group)
            merged_bbox = fitz.Rect()
            for b in current_group: merged_bbox.include_rect(b.bbox)
            first_block = current_group[0]
            grouped_blocks.append(TextBlock(merged_text, merged_bbox, first_block.page_num, first_block.size, first_block.is_bold))
        else:
            grouped_blocks.append(current_group[0])
            
        return grouped_blocks

    def _detect_headings(self, all_blocks):
        """Identifies headings using style, length, and vertical gap analysis."""
        if not all_blocks:
            return

        sorted_blocks = sorted(all_blocks, key=lambda b: (b.page_num, b.bbox.y0))
        semantic_blocks = self._group_lines_into_semantic_blocks(sorted_blocks)
        num_blocks = len(semantic_blocks)
        
        # Calculate average font size of plausible body text
        all_sizes = [b.size for b in semantic_blocks if len(b.text.split()) > 3 and b.size > 6]
        avg_size = np.mean(all_sizes) if all_sizes else 12.0
        print(f"   ℹ️ Average body font size: {avg_size:.2f}pt")
        
        potential_headings = []
        for i, block in enumerate(semantic_blocks):
            text_content = block.text.strip()
            # Skip blocks that are just a number or look like a date.
            if text_content.replace('.', '', 1).isdigit() and len(text_content.split()) < 2:
                continue
            skip_patterns = [
                r'^\s*RSVP[:\-]?',                           # RSVP or RSVP:
                r'^\s*www\.[\w\.-]+\.[a-z]{2,}$',            # Websites like www.topjump.com
                r'^\s*https?://[\w\.-]+',                    # Full URLs (http/https)
                r'^\s*email[:\-]?\s*[\w\.-]+@[\w\.-]+$',     # Email addresses
                r'^\s*phone[:\-]?\s*\+?\d[\d\-\s]+$',        # Phone numbers
                r'^\s*\(?\d{3}\)?[\s\-]?\d{3}[\s\-]?\d{4}$', # US-style phone numbers
                r'^\s*(tel|fax)[:\-]?\s*\+?\d[\d\-\s]+$',    # Tel/Fax numbers
                r'^\s*(address|location)[:\-]?\s*.*$',       # Address labels
                r'^\s*\d{1,3}(\.\d+)*\s*$',                  # Pure section numbers (1, 1.1, etc.)
                r'^\s*page\s*\d+\s*$',                       # "Page 1", "Page 2"
                r'^\s*(copyright|©)\s*.*$',                  # Copyright info
                r'^\s*(confidential|disclaimer).*$',         # Confidential disclaimers
                r'^\s*(figure|table)\s*\d+\s*[:\-]?.*$',     # Figure/Table labels
                r'^\s*(date|time)[:\-]?\s*.*$',              # Date/Time labels
                r'^\s*contact\s*(us)?[:\-]?\s*.*$',          # Contact info
            ]
            if any(re.match(pattern, text_content, re.IGNORECASE) for pattern in skip_patterns):
                continue
            words = text_content.lower().split()
            months = {'january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december'}
            contains_month = any(word.strip('.,') in months for word in words)
            contains_year = any(word.isdigit() and len(word) == 4 for word in words)
            if contains_month and contains_year:
                continue

            # --- CORRECTED HEADING LOGIC ---
            is_exceptionally_large = block.size > avg_size * 1.8
            is_moderately_large = block.size > avg_size * 1.15
            is_short = len(block.text.split()) < 20 and len(block.text) < 200
            starts_with_number = re.match(r'^\d+(\.\d+)*\s+', block.text)
            
            # A block is a heading if it's EXCEPTIONALLY large, OR moderately large and short, OR bold and short
            if not (is_exceptionally_large or (is_moderately_large and is_short) or (block.is_bold and is_short) or starts_with_number):
                continue

            # --- CRUCIAL: GAP DETECTION STRATEGY ---
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
            print("   ⚠️ No headings found after applying all filters.")
            return

        # Cluster heading font sizes to determine levels (H1, H2, etc.)
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
        
        print(f"   ℹ️ Detected {len(size_levels)} heading levels with effective sizes: {[round(s, 1) for s in size_levels]}")

        for block in potential_headings:
            level_idx = min(range(len(size_levels)), key=lambda i: abs(size_levels[i] - block.size))
            block.heading_level = f"H{level_idx + 1}"

    def process(self, pdf_path):
        """Main processing function for a single PDF."""
        print(f"\n📄 Processing: {Path(pdf_path).name}")
        start_time = time.time()
        
        try:
            doc = fitz.open(pdf_path)
        except Exception as e:
            print(f"   ❌ Error opening PDF: {e}")
            return None

        all_blocks = []
        for page_num, page in enumerate(doc):
            print(f"   - Analyzing page {page_num + 1}/{len(doc)}...")
            if len(page.get_text()) < self.char_threshold:
                print(f"      - Page has little text. Attempting OCR.")
                if not PADDLE_AVAILABLE: continue
                try: page_blocks = self._parse_scanned_page(page, page_num)
                except Exception as e:
                    print(f"      - OCR failed for page {page_num + 1}: {e}")
                    page_blocks = []
            else:
                print(f"      - Page is digital. Extracting text natively.")
                page_blocks = self._parse_digital_page(page, page_num)
            all_blocks.extend(page_blocks)
        
        print(f"\n   🔎 Found {len(all_blocks)} raw text lines. Identifying headings...")
        self._detect_headings(all_blocks)

        outline = []
        for block in all_blocks:
            if block.is_heading:
                outline.append({
                    "level": block.heading_level,
                    "text": block.text,
                    "page": block.page_num + 1,
                })

        outline.sort(key=lambda x: (x["page"]))
        title = doc.metadata.get("title") or (outline[0]['text'] if outline and outline[0]['level'] == 'H1' else Path(pdf_path).stem.replace("_", " ").title())

        result = {
            "title": title,
            "outline": outline,
        }
        
        doc.close()
        print(f"   ✅ Finished processing. Found {len(outline)} headings.")
        return result

def main():
    print("🚀 PDF Outline Extractor v5 (with Smarter Heading Detection) 🚀")
    print("================================================================")
    
    input_dir = "./input"
    output_dir = "./output"
    
    if not os.path.exists(input_dir):
        os.makedirs(input_dir)
        print(f"❗ Created input directory '{input_dir}'. Please add your PDF files there.")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    pdf_files = [f for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]
    if not pdf_files:
        print(f"🤷 No PDF files found in '{input_dir}'.")
        return
        
    print(f"📚 Found {len(pdf_files)} PDF(s) to process.\n")
    
    extractor = PDFOutlineExtractor()
    
    for pdf_file in pdf_files:
        pdf_path = os.path.join(input_dir, pdf_file)
        try:
            result = extractor.process(pdf_path)
            if result:
                output_filename = os.path.join(output_dir, f"{Path(pdf_file).stem}_outline.json")
                with open(output_filename, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"   💾 Successfully saved outline to: {output_filename}")
        except Exception as e:
            print(f"   🔥🔥🔥 A critical error occurred while processing {pdf_file}: {e}")
            traceback.print_exc()

    print("\n🎉 All files processed. Check the 'output' directory for results.")

if __name__ == "__main__":
    main()
