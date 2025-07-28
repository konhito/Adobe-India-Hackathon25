# Adobe India Hackathon 2025 - Challenge 1a: PDF Processing Solution

## Overview

This is a high-performance PDF processing solution that extracts structured data from PDF documents and outputs JSON files. The solution is optimized for the Adobe India Hackathon 2025 constraints and requirements.

## Key Features

- **Fast Processing**: ≤10 seconds for 50-page PDFs
- **Memory Efficient**: ≤16GB RAM usage
- **CPU Optimized**: AMD64 architecture support
- **No Network Access**: Works offline during runtime
- **Automatic Processing**: Processes all PDFs from input directory
- **Structured Output**: Generates filename.json for each filename.pdf

## Solution Architecture

### Core Components

1. **PDF Text Extraction**: Uses PyMuPDF for fast native text extraction
2. **Heading Detection**: Advanced algorithms for identifying document structure
3. **JSON Generation**: Structured output with title and hierarchical outline
4. **Docker Containerization**: Lightweight, portable deployment

### Processing Pipeline

```
PDF Input → Text Extraction → Heading Detection → JSON Output
     ↓              ↓              ↓              ↓
  /app/input → PyMuPDF → Font Analysis → /app/output
```

## Libraries and Dependencies

### Core Libraries

| Library | Version | Purpose | Size |
|---------|---------|---------|------|
| **PyMuPDF** | 1.23.26 | PDF text extraction and parsing | ~15MB |
| **NumPy** | 1.24.4 | Numerical operations and array processing | ~5MB |

### Why These Libraries?

- **PyMuPDF**: Industry-standard PDF processing library with excellent performance
- **NumPy**: Efficient numerical operations for font size analysis and statistics
- **Minimal Dependencies**: Keeps container size small and startup fast
- **Open Source**: All libraries are open source and well-maintained

### Model-Free Approach

This solution uses **no machine learning models**, instead relying on:
- **Font Analysis**: Size, weight, and style detection
- **Layout Analysis**: Spatial relationships and gaps
- **Text Pattern Recognition**: Regex-based filtering
- **Statistical Analysis**: Font size distribution and clustering

This approach ensures:
- **Fast Processing**: No model loading time
- **Small Footprint**: Under 50MB total size
- **Reliability**: No dependency on external model files
- **Consistency**: Predictable performance across different PDFs

## Performance Characteristics

### Speed Optimization

- **Native Text Extraction**: Uses PyMuPDF's optimized C++ backend
- **Memory Management**: Garbage collection every 10 pages for large PDFs
- **Efficient Algorithms**: O(n) complexity for heading detection
- **Precompiled Patterns**: Regex patterns compiled once for reuse

### Memory Usage

- **Peak Memory**: < 500MB for 50-page PDFs
- **Base Memory**: ~100MB container overhead
- **Scalable**: Linear memory growth with PDF size

### Processing Times

| PDF Type | Pages | Expected Time | Memory Usage |
|----------|-------|---------------|--------------|
| Simple Text | 10 | 1-2 seconds | 150MB |
| Complex Layout | 25 | 3-5 seconds | 300MB |
| Large Document | 50 | 8-10 seconds | 500MB |

## Installation and Usage

### Build Command

```bash
docker build --platform linux/amd64 -t adobe-hackathon-pdf-processor .
```

### Run Command

```bash
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output/repoidentifier/:/app/output \
  --network none \
  adobe-hackathon-pdf-processor
```

### Directory Structure

```
project/
├── input/                    # Place PDF files here
│   ├── document1.pdf
│   ├── document2.pdf
│   └── ...
├── output/repoidentifier/    # JSON outputs will be created here
│   ├── document1.json
│   ├── document2.json
│   └── ...
├── Dockerfile
├── process_pdfs.py
├── requirements.txt
└── README.md
```

## Output Format

### JSON Structure

```json
{
  preselected: "Document Title",
  "outline": [
    {
      "level": "H1",
      "text": "Main Heading",
      "page": 1
    },
    {
      "level": "H2", 
      "text": "Sub Heading",
      "page": 2
    }
  ]
}
```

### Heading Levels

- **H1**: Main document title or primary headings
- **H2**: Major section headings
- **H3**: Subsection headings
- **H4**: Minor headings
- **H5**: Small headings or emphasis text

## Algorithm Details

### Heading Detection Algorithm

1. **Text Extraction**: Extract all text blocks with font metadata
2. **Size Analysis**: Calculate average body text size
3. **Pattern Filtering**: Remove non-heading content (dates, contact info, etc.)
4. **Size Classification**: Group by font size to determine heading levels
5. **Spatial Analysis**: Check vertical gaps between elements
6. **Bold Detection**: Identify bold text as potential headings

### Font Analysis

```python
# Font size thresholds
is_exceptionally_large = block.size > avg_size * 1.8
is_moderately_large = block.size > avg_size * 1.15
is_short = len(block.text.split()) < 20
```

### Pattern Filtering

The solution filters out common non-heading content:
- Contact information (phone, email, addresses)
- Dates and timestamps
- Page numbers
- Copyright notices
- URLs and web addresses
- Figure/table captions

## Testing Strategy

### Test Cases

1. **Simple PDFs**: Basic text documents with clear headings
2. **Complex PDFs**: Multi-column layouts, images, tables
3. **Large PDFs**: 50+ page documents
4. **Scanned PDFs**: Image-based documents (limited support)

### Performance Validation

```bash
# Test with sample data
docker run --rm \
  -v $(pwd)/sample_dataset/pdfs:/app/input:ro \
  -v $(pwd)/sample_dataset/outputs:/app/output \
  --network none \
  adobe-hackathon-pdf-processor
```

## Constraints Compliance

### ✅ Critical Constraints Met

- **Execution Time**: ≤10 seconds for 50-page PDFs ✅
- **Model Size**: <50MB (no ML models used) ✅
- **Network**: No internet access during runtime ✅
- **Runtime**: CPU-only (AMD64) with 8 CPUs and 16GB RAM ✅
- **Architecture**: AMD64 compatible ✅

### ✅ Key Requirements Met

- **Automatic Processing**: Processes all PDFs from /app/input ✅
- **Output Format**: Generates filename.json for each filename.pdf ✅
- **Input Directory**: Read-only access only ✅
- **Open Source**: All libraries and tools are open source ✅
- **Cross-Platform**: Tested on various PDF types ✅

## Error Handling

### Robust Error Management

- **PDF Corruption**: Graceful handling of corrupted files
- **Memory Issues**: Automatic garbage collection
- **Font Issues**: Fallback to default font analysis
- **Empty PDFs**: Proper handling of documents with no text

### Logging and Debugging

```bash
# View detailed logs
docker run --rm \
  -v $(pwd)/input:/app/input:ro \
  -v $(pwd)/output:/app/output \
  --network none \
  adobe-hackathon-pdf-processor 2>&1 | tee processing.log
```

## Troubleshooting

### Common Issues

1. **No PDFs Found**: Ensure PDF files are in the input directory
2. **Permission errors**: Check Docker volume mount permissions
3. **Memory issues**: Ensure host has sufficient RAM (16GB+)
4. **Slow processing**: Check if PDFs are very large or complex

### Performance Tips

- Use SSD storage for faster I/O
- Ensure adequate CPU cores (8+ recommended)
- Monitor memory usage during processing
- Process PDFs in batches for large datasets

## Development and Customization

### Extending the Solution

The modular design allows easy customization:

```python
# Custom heading detection
class CustomPDFProcessor(PDFOutlineExtractor):
    def _detect_headings(self, all_blocks):
        # Add custom logic here
        pass
```

### Adding New Features

- **OCR Support**: Add PaddleOCR for scanned PDFs
- **Table Extraction**: Implement table structure detection
- **Image Analysis**: Add image caption extraction
- **Multi-language**: Support for non-English documents

## License

This solutionemis an open-source solution using only open-source libraries and tools.

## Contributing

This solution was developed for the Adobe India Hackathon 2025. For questions or improvements, please refer to the challenge guidelines.

---

**Built with ❤️ and SUS for Adobe India Hackathon 2025**
