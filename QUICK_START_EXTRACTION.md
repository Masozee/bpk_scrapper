# Quick Start: PDF Text Extraction

## ✅ What's Already Done

You now have a fully functional PDF text extractor at `pdf_text_extractor.py`!

**Dependencies installed:**
- ✅ PyPDF2
- ✅ pdfplumber

## 🚀 Quick Commands

### Extract from a single PDF:
```bash
python pdf_text_extractor.py --file "docs/bpk/2024/Bandung/regulation.pdf"
```

### Extract from entire BPK directory:
```bash
python pdf_text_extractor.py --input docs/bpk --output extracted_texts/bpk --workers 8
```

### Extract from peraturan.go.id directory:
```bash
python pdf_text_extractor.py --input docs/2024 --output extracted_texts/peraturan --workers 6
```

### Extract from ALL downloaded PDFs:
```bash
python pdf_text_extractor.py --input docs --output extracted_texts --workers 8
```

## 📊 What You'll Get

For each PDF, two files are created:

1. **`filename.txt`** - Extracted text with metadata header
2. **`filename_metadata.json`** - Extraction details and statistics

### Example Output Structure:
```
extracted_texts/
├── bpk/
│   ├── 2024/
│   │   └── Bandung/
│   │       ├── Peraturan_Daerah_Nomor_1.txt
│   │       └── Peraturan_Daerah_Nomor_1_metadata.json
│   └── 2013/
│       └── Kabupaten_Balangan/
│           ├── Pajak_Hiburan.txt (✅ Already tested - 6,712 words!)
│           └── Pajak_Hiburan_metadata.json
```

## 📈 Performance Expectations

- **Speed:** ~10-50 PDFs per minute
- **Quality:** Excellent for regular PDFs with embedded text
- **Incremental:** Skips already-processed files automatically

## 🔍 Optional: Enable OCR for Scanned PDFs

If some PDFs are scanned images (no embedded text), you can enable OCR:

### Install OCR dependencies:
```bash
pip install pytesseract pdf2image Pillow
```

### Then use with `--ocr` flag:
```bash
python pdf_text_extractor.py --input docs/bpk --ocr --workers 4
```

**Note:** OCR is much slower (~1-5 PDFs/minute) and requires Tesseract + Poppler installed on your system.

## 📝 Recommended Workflow

### Step 1: Quick extraction (no OCR)
Start with basic extraction to process all PDFs with embedded text:
```bash
python pdf_text_extractor.py --input docs/bpk --output extracted_texts/bpk --workers 8
```

### Step 2: Check results
Look at the summary to see how many succeeded/failed:
```
EXTRACTION COMPLETE
======================================================================
Total PDFs processed: 1000
✅ Successfully extracted: 950
⏭️  Skipped (already done): 0
❌ Failed: 50
🔍 OCR used: 0
```

### Step 3: (Optional) Re-process failures with OCR
If some PDFs failed, they might be scanned. Install OCR tools and retry:
```bash
python pdf_text_extractor.py --input docs/bpk --ocr --workers 2
```

## 💡 Pro Tips

1. **Start Small** - Test on a subfolder first:
   ```bash
   python pdf_text_extractor.py --input docs/bpk/2024 --output test_extraction
   ```

2. **Monitor Progress** - The progress bar shows real-time stats:
   ```
   Extracting text: 45%|████▌     | Success: 450, Failed: 5, Skipped: 0
   ```

3. **Check Metadata** - Review `_metadata.json` files to see extraction quality:
   ```json
   {
     "method": "pdfplumber",
     "char_count": 41097,
     "word_count": 6712,
     "success": true
   }
   ```

4. **Adjust Workers** - Use more workers for faster processing:
   - Good CPU: 8-12 workers
   - Average CPU: 4-6 workers
   - Low CPU or OCR: 2-4 workers

## 🎯 Next Steps

After extraction, you can:

1. **Search through texts** using grep:
   ```bash
   grep -r "keyword" extracted_texts/
   ```

2. **Import to database** for full-text search
3. **Analyze text** with NLP tools
4. **Build search index** with Elasticsearch/Whoosh

## 📚 Full Documentation

See `PDF_EXTRACTION_GUIDE.md` for complete documentation including:
- Detailed installation instructions
- All command-line options
- Troubleshooting guide
- Integration examples
