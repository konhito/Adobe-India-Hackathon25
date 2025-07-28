Adobe Hackathon 2025 - Challenge 1a: PDF Outline Extractor
Docker Container Version – Digital Text Only
Optimized for fast processing (≤10 seconds for a 50-page PDF) on CPU-only, meeting hackathon constraints.

Overview
This solution extracts structured outlines (headings hierarchy) from PDF documents and generates JSON output for each PDF.
It is optimized for:

No OCR (digital text only)

Performance: Sub-10-second execution for 50-page PDFs

Resource Constraints: CPU-only, ≤16 GB RAM, no internet during execution

Hackathon Guidelines: Open source, reproducible, and containerized using Docker

Features
✅ Fully offline – no external calls during runtime

✅ Processes all PDFs in /app/input automatically

✅ Outputs filename.json in /app/output for each PDF

✅ Detects headings using font size, boldness, and semantic rules

✅ Lightweight & optimized for AMD64 architecture

Approach
Text Extraction: Uses PyMuPDF (fitz) for high-speed PDF parsing (no OCR).

Block Grouping: Groups related text lines into semantic blocks for accurate hierarchy.

Heading Detection:

Font size comparison (relative to body text average)

Bold text detection

Short, meaningful phrases filtering

Heading Levels: Dynamically assigns H1, H2, H3 levels based on size clusters.

JSON Output:

json
Copy
Edit
{
  "title": "Document Title",
  "outline": [
    {"level": "H1", "text": "Main Heading", "page": 1},
    {"level": "H2", "text": "Sub Heading", "page": 1}
  ]
}
Directory Structure
pgsql
Copy
Edit
Challenge_1a/
├── input/                 # Input PDFs (mounted read-only)
├── output/                # Generated JSON files
├── Dockerfile             # Docker container configuration
├── pdf_outline_extractor.py  # Main Python script
└── README.md              # This file
Build & Run Instructions
1. Build Docker Image
bash
Copy
Edit
docker build --platform linux/amd64 -t pdf-outline-extractor .
2. Run Container
bash
Copy
Edit
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output \
  --network none \
  pdf-outline-extractor
Input & Output
Input Directory: /app/input (read-only)

Output Directory: /app/output

File Mapping: filename.pdf → filename.json

Example Output
For sample.pdf:

json
Copy
Edit
{
  "title": "Sample",
  "outline": [
    {"level": "H1", "text": "Introduction", "page": 1},
    {"level": "H2", "text": "Overview", "page": 2},
    {"level": "H2", "text": "Details", "page": 3}
  ]
}
Performance
Tested on 50-page PDFs

Execution Time: ~8-10 seconds

Memory: < 1 GB

CPU: Utilizes 8 cores efficiently

Dependencies
PyMuPDF (fast PDF parsing)

NumPy (efficient calculations)

Python 3.10+

Ubuntu 22.04 base image

Hackathon Compliance
✔ Works offline (no internet needed at runtime)

✔ Open Source libraries only

✔ CPU-only (no GPU requirement)

✔ Tested on AMD64 architecture

✔ Output conforms to JSON schema provided

Next Steps
Extend for OCR-based PDFs (requires PaddleOCR – note: model size constraints apply)

Enhance table/figure detection for advanced hierarchy extraction

Maintainer: Adobe Hackathon Team
Version: 5.0
