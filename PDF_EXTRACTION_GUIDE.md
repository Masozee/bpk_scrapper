# PDF Text Extraction Guide

## Overview

The `pdf_text_extractor.py` tool extracts text from PDF files, supporting both:
- **Regular PDFs** with embedded text (using PyPDF2 and pdfplumber)
- **Scanned PDFs** that require OCR (using Tesseract OCR)

## Installation

### Basic Installation (No OCR)

```bash
pip install PyPDF2 pdfplumber
```

This allows extraction from regular PDFs with embedded text.

### Full Installation (With OCR Support)

For scanned PDFs, you need additional dependencies:

1. **Install Python packages:**
   ```bash
   pip install PyPDF2 pdfplumber pytesseract pdf2image Pillow
   ```

2. **Install system dependencies:**

   **Windows:**
   - Download and install [Tesseract OCR](https://github.com/UB-Mannheim/tesseract/wiki)
   - Download and install [Poppler for Windows](https://github.com/oschwartz10612/poppler-windows/releases/)
   - Add both to your system PATH

   **Linux (Ubuntu/Debian):**
   ```bash
   sudo apt-get install tesseract-ocr tesseract-ocr-ind tesseract-ocr-eng poppler-utils
   ```

   **macOS:**
   ```bash
   brew install tesseract tesseract-lang poppler
   ```

## Usage

### Basic Usage

Extract text from all PDFs in a directory:
```bash
python pdf_text_extractor.py --input docs/bpk --output extracted_texts
```

### With OCR Support

Enable OCR for scanned PDFs:
```bash
python pdf_text_extractor.py --input docs/bpk --output extracted_texts --ocr
```

Force OCR for all PDFs (slower, but ensures best quality):
```bash
python pdf_text_extractor.py --input docs/bpk --output extracted_texts --force-ocr
```

### Process Single File

Extract from a specific PDF:
```bash
python pdf_text_extractor.py --file docs/bpk/2024/Bandung/regulation.pdf
```

### Advanced Options

Use more workers for faster processing:
```bash
python pdf_text_extractor.py --input docs --workers 8 --ocr
```

Process only top-level directory (no subdirectories):
```bash
python pdf_text_extractor.py --input docs/bpk --no-recursive
```

## Command-Line Options

| Option | Description |
|--------|-------------|
| `--input, -i` | Input directory containing PDFs |
| `--file, -f` | Single PDF file to process |
| `--output, -o` | Output directory (default: `extracted_texts`) |
| `--workers, -w` | Number of worker threads (default: 4) |
| `--ocr` | Enable OCR for scanned PDFs |
| `--force-ocr` | Force OCR for all PDFs (even with embedded text) |
| `--no-recursive` | Don't process subdirectories |

## Output Format

For each PDF file, the extractor creates:

1. **Text file** (`filename.txt`):
   - Header with metadata (filename, method, date, statistics)
   - Extracted text content
   - Page separators

2. **Metadata JSON** (`filename_metadata.json`):
   - Extraction details
   - Character and word counts
   - Method used
   - Any errors encountered

### Example Output

```
extracted_texts/
├── 2024/
│   └── Bandung/
│       ├── Peraturan_Daerah_Nomor_1.txt
│       ├── Peraturan_Daerah_Nomor_1_metadata.json
│       ├── Peraturan_Daerah_Nomor_2.txt
│       └── Peraturan_Daerah_Nomor_2_metadata.json
```

## Extraction Methods

The tool tries multiple methods in order:

1. **pdfplumber** - Best for complex layouts and tables
2. **PyPDF2** - Fallback for simple PDFs
3. **OCR (Tesseract)** - For scanned documents (if enabled)

## Performance

- **Without OCR:** ~10-50 PDFs per minute (depending on file size)
- **With OCR:** ~1-5 PDFs per minute (significantly slower)

OCR is only used when:
- `--ocr` flag is enabled AND
- Text extraction methods find insufficient text (< 100 characters)

OR when `--force-ocr` is used.

## Examples

### Extract from BPK regulations:
```bash
python pdf_text_extractor.py --input docs/bpk --output extracted_texts/bpk --workers 8
```

### Extract from peraturan.go.id regulations with OCR:
```bash
python pdf_text_extractor.py --input docs/2024 --output extracted_texts/peraturan --ocr --workers 4
```

### Re-process failed extractions with OCR:
```bash
python pdf_text_extractor.py --input docs/bpk --force-ocr --workers 2
```

## Troubleshooting

### "No text found and OCR not available"
- Install OCR dependencies (see Full Installation above)
- Use `--ocr` flag

### "Tesseract not found"
- Ensure Tesseract is installed and in system PATH
- On Windows, add Tesseract installation directory to PATH

### "Unable to get page count"
- PDF file may be corrupted
- Try opening the PDF in a viewer to verify

### Low text quality from OCR
- Increase DPI in `extract_with_ocr()` method (default: 300)
- Ensure PDF scans are high quality
- Install language packs for Tesseract: `tesseract-ocr-ind` for Indonesian

## Integration with Scraper

You can integrate text extraction into your scraping workflow:

```python
from pdf_text_extractor import PDFTextExtractor

# After downloading PDFs
extractor = PDFTextExtractor(output_dir="extracted_texts", use_ocr=True)
result = extractor.process_single_pdf(pdf_path)

if result['success']:
    # Store extracted text in database
    db.update_perda(perda_id, text=result['text'])
```

## Tips

1. **Start without OCR** - Try basic extraction first, then use OCR only for failed PDFs
2. **Use appropriate workers** - 4-8 workers for text extraction, 2-4 for OCR
3. **Check output** - Review `_metadata.json` files to see which method was used
4. **Incremental processing** - Tool skips already-processed files by default
5. **Monitor progress** - Progress bar shows success/failed/OCR statistics in real-time
