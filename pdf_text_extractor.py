#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF Text Extractor
Extracts text from PDF files, handling both regular and OCR-scanned PDFs
Supports batch processing of downloaded regulation PDFs
"""

import sys
import os
from pathlib import Path
from typing import Optional, Dict, List
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import threading

# Set UTF-8 encoding for Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False
    print("⚠️  PyPDF2 not installed. Install with: pip install PyPDF2")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("⚠️  pdfplumber not installed. Install with: pip install pdfplumber")

try:
    from pdf2image import convert_from_path
    import pytesseract
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("⚠️  OCR not available. Install with: pip install pdf2image pytesseract pillow")
    print("    Also requires poppler and tesseract installed on system")


class PDFTextExtractor:
    """Extract text from PDF files using multiple methods"""

    def __init__(self, output_dir: str = "extracted_texts", use_ocr: bool = True,
                 max_workers: int = 4):
        """
        Initialize PDF text extractor

        Args:
            output_dir: Directory to save extracted text files
            use_ocr: Whether to use OCR for scanned PDFs
            max_workers: Number of concurrent workers for batch processing
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.use_ocr = use_ocr and OCR_AVAILABLE
        self.max_workers = max_workers

        # Statistics
        self.stats_lock = threading.Lock()
        self.stats = {
            'total': 0,
            'success': 0,
            'failed': 0,
            'skipped': 0,
            'ocr_used': 0,
            'errors': []
        }

    def extract_with_pypdf2(self, pdf_path: Path) -> Optional[str]:
        """Extract text using PyPDF2"""
        if not PYPDF2_AVAILABLE:
            return None

        try:
            with open(pdf_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = []

                for page_num, page in enumerate(reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text.append(f"\n--- Page {page_num + 1} ---\n")
                            text.append(page_text)
                    except Exception as e:
                        print(f"⚠️  Error extracting page {page_num + 1}: {e}")
                        continue

                extracted_text = "\n".join(text).strip()
                return extracted_text if extracted_text else None

        except Exception as e:
            print(f"❌ PyPDF2 error for {pdf_path.name}: {e}")
            return None

    def extract_with_pdfplumber(self, pdf_path: Path) -> Optional[str]:
        """Extract text using pdfplumber (better for complex layouts)"""
        if not PDFPLUMBER_AVAILABLE:
            return None

        try:
            with pdfplumber.open(pdf_path) as pdf:
                text = []

                for page_num, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text and page_text.strip():
                            text.append(f"\n--- Page {page_num + 1} ---\n")
                            text.append(page_text)
                    except Exception as e:
                        print(f"⚠️  Error extracting page {page_num + 1}: {e}")
                        continue

                extracted_text = "\n".join(text).strip()
                return extracted_text if extracted_text else None

        except Exception as e:
            print(f"❌ pdfplumber error for {pdf_path.name}: {e}")
            return None

    def extract_with_ocr(self, pdf_path: Path, max_pages: int = 50) -> Optional[str]:
        """Extract text using OCR (for scanned PDFs)"""
        if not self.use_ocr or not OCR_AVAILABLE:
            return None

        try:
            print(f"🔍 Using OCR for {pdf_path.name}...")

            # Convert PDF to images
            images = convert_from_path(pdf_path, dpi=300, first_page=1,
                                      last_page=min(max_pages, 100))

            text = []
            for page_num, image in enumerate(images):
                try:
                    # Extract text using Tesseract OCR
                    page_text = pytesseract.image_to_string(image, lang='ind+eng')
                    if page_text and page_text.strip():
                        text.append(f"\n--- Page {page_num + 1} (OCR) ---\n")
                        text.append(page_text)
                except Exception as e:
                    print(f"⚠️  OCR error on page {page_num + 1}: {e}")
                    continue

            extracted_text = "\n".join(text).strip()

            with self.stats_lock:
                self.stats['ocr_used'] += 1

            return extracted_text if extracted_text else None

        except Exception as e:
            print(f"❌ OCR error for {pdf_path.name}: {e}")
            return None

    def extract_text(self, pdf_path: Path, force_ocr: bool = False) -> Dict:
        """
        Extract text from PDF using multiple methods

        Args:
            pdf_path: Path to PDF file
            force_ocr: Force OCR even if text extraction works

        Returns:
            Dict with extracted text and metadata
        """
        result = {
            'file': str(pdf_path),
            'filename': pdf_path.name,
            'text': None,
            'method': None,
            'success': False,
            'error': None,
            'extracted_at': datetime.now().isoformat(),
            'char_count': 0,
            'word_count': 0
        }

        try:
            # Try pdfplumber first (best quality)
            if not force_ocr and PDFPLUMBER_AVAILABLE:
                text = self.extract_with_pdfplumber(pdf_path)
                if text and len(text) > 100:  # Minimum threshold
                    result['text'] = text
                    result['method'] = 'pdfplumber'
                    result['success'] = True

            # Try PyPDF2 as fallback
            if not result['success'] and not force_ocr and PYPDF2_AVAILABLE:
                text = self.extract_with_pypdf2(pdf_path)
                if text and len(text) > 100:
                    result['text'] = text
                    result['method'] = 'pypdf2'
                    result['success'] = True

            # Use OCR if text extraction failed or forced
            if not result['success'] or force_ocr:
                if self.use_ocr:
                    text = self.extract_with_ocr(pdf_path)
                    if text:
                        result['text'] = text
                        result['method'] = 'ocr'
                        result['success'] = True
                else:
                    result['error'] = "No text found and OCR not available"

            # Calculate statistics
            if result['text']:
                result['char_count'] = len(result['text'])
                result['word_count'] = len(result['text'].split())

        except Exception as e:
            result['error'] = str(e)
            result['success'] = False

        return result

    def save_extracted_text(self, pdf_path: Path, text: str, metadata: Dict) -> Path:
        """Save extracted text to file with metadata"""
        # Create output path maintaining directory structure
        rel_path = pdf_path.relative_to(pdf_path.parts[0]) if len(pdf_path.parts) > 1 else pdf_path

        # Create subdirectories in output
        output_subdir = self.output_dir / rel_path.parent
        output_subdir.mkdir(parents=True, exist_ok=True)

        # Text file path
        text_file = output_subdir / f"{pdf_path.stem}.txt"

        # Write text file
        with open(text_file, 'w', encoding='utf-8') as f:
            f.write(f"# Extracted from: {pdf_path.name}\n")
            f.write(f"# Method: {metadata.get('method', 'unknown')}\n")
            f.write(f"# Extracted at: {metadata.get('extracted_at', 'unknown')}\n")
            f.write(f"# Characters: {metadata.get('char_count', 0)}\n")
            f.write(f"# Words: {metadata.get('word_count', 0)}\n")
            f.write("\n" + "="*80 + "\n\n")
            f.write(text)

        # Save metadata JSON
        json_file = output_subdir / f"{pdf_path.stem}_metadata.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        return text_file

    def process_single_pdf(self, pdf_path: Path, force_ocr: bool = False,
                          save_output: bool = True) -> Dict:
        """Process a single PDF file"""
        with self.stats_lock:
            self.stats['total'] += 1

        # Check if already processed
        output_file = self.output_dir / pdf_path.parent.name / f"{pdf_path.stem}.txt"
        if output_file.exists() and not force_ocr:
            with self.stats_lock:
                self.stats['skipped'] += 1
            return {
                'file': str(pdf_path),
                'status': 'skipped',
                'message': 'Already processed'
            }

        # Extract text
        result = self.extract_text(pdf_path, force_ocr=force_ocr)

        # Save if successful
        if result['success'] and save_output:
            try:
                output_path = self.save_extracted_text(pdf_path, result['text'], result)
                result['output_file'] = str(output_path)
                with self.stats_lock:
                    self.stats['success'] += 1
            except Exception as e:
                result['save_error'] = str(e)
                with self.stats_lock:
                    self.stats['failed'] += 1
        elif not result['success']:
            with self.stats_lock:
                self.stats['failed'] += 1
                self.stats['errors'].append({
                    'file': str(pdf_path),
                    'error': result.get('error', 'Unknown error')
                })

        return result

    def process_directory(self, pdf_dir: str, recursive: bool = True,
                         force_ocr: bool = False) -> Dict:
        """
        Process all PDFs in a directory

        Args:
            pdf_dir: Directory containing PDF files
            recursive: Process subdirectories recursively
            force_ocr: Force OCR for all PDFs

        Returns:
            Summary statistics
        """
        pdf_dir = Path(pdf_dir)

        # Find all PDF files
        if recursive:
            pdf_files = list(pdf_dir.rglob("*.pdf"))
        else:
            pdf_files = list(pdf_dir.glob("*.pdf"))

        print(f"\n{'='*70}")
        print(f"PDF TEXT EXTRACTION")
        print(f"{'='*70}")
        print(f"Source directory: {pdf_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"PDF files found: {len(pdf_files)}")
        print(f"Workers: {self.max_workers}")
        print(f"OCR enabled: {self.use_ocr}")
        print(f"Force OCR: {force_ocr}")
        print(f"{'='*70}\n")

        if not pdf_files:
            print("❌ No PDF files found!")
            return self.stats

        # Process PDFs with thread pool
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(self.process_single_pdf, pdf, force_ocr): pdf
                      for pdf in pdf_files}

            with tqdm(total=len(pdf_files), desc="Extracting text") as pbar:
                for future in as_completed(futures):
                    pdf_path = futures[future]
                    try:
                        result = future.result()

                        # Update progress bar
                        pbar.update(1)
                        pbar.set_postfix({
                            'Success': self.stats['success'],
                            'Failed': self.stats['failed'],
                            'Skipped': self.stats['skipped'],
                            'OCR': self.stats['ocr_used']
                        })

                    except Exception as e:
                        print(f"\n❌ Error processing {pdf_path.name}: {e}")
                        with self.stats_lock:
                            self.stats['failed'] += 1
                        pbar.update(1)

        # Print summary
        self.print_summary()

        return self.stats

    def print_summary(self):
        """Print extraction summary"""
        print(f"\n{'='*70}")
        print(f"EXTRACTION COMPLETE")
        print(f"{'='*70}")
        print(f"Total PDFs processed: {self.stats['total']}")
        print(f"✅ Successfully extracted: {self.stats['success']}")
        print(f"⏭️  Skipped (already done): {self.stats['skipped']}")
        print(f"❌ Failed: {self.stats['failed']}")
        print(f"🔍 OCR used: {self.stats['ocr_used']}")
        print(f"{'='*70}")

        if self.stats['errors']:
            print(f"\n⚠️  Errors ({len(self.stats['errors'])}):")
            for err in self.stats['errors'][:10]:  # Show first 10
                print(f"  - {Path(err['file']).name}: {err['error']}")
            if len(self.stats['errors']) > 10:
                print(f"  ... and {len(self.stats['errors']) - 10} more errors")

        print()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(
        description='Extract text from PDF files (supports OCR for scanned PDFs)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract from all PDFs in docs/bpk directory
  python pdf_text_extractor.py --input docs/bpk --output extracted_texts

  # Extract with OCR enabled
  python pdf_text_extractor.py --input docs/bpk --ocr

  # Force OCR for all PDFs (even if text extraction works)
  python pdf_text_extractor.py --input docs/bpk --force-ocr

  # Extract from specific PDF file
  python pdf_text_extractor.py --file docs/bpk/2024/Bandung/regulation.pdf

  # Use more workers for faster processing
  python pdf_text_extractor.py --input docs --workers 8
        """
    )

    parser.add_argument('--input', '-i', help='Input directory containing PDFs')
    parser.add_argument('--file', '-f', help='Single PDF file to process')
    parser.add_argument('--output', '-o', default='extracted_texts',
                       help='Output directory for extracted text (default: extracted_texts)')
    parser.add_argument('--workers', '-w', type=int, default=4,
                       help='Number of worker threads (default: 4)')
    parser.add_argument('--ocr', action='store_true',
                       help='Enable OCR for scanned PDFs')
    parser.add_argument('--force-ocr', action='store_true',
                       help='Force OCR for all PDFs (slower but more accurate)')
    parser.add_argument('--no-recursive', action='store_true',
                       help='Do not process subdirectories')

    args = parser.parse_args()

    if not args.input and not args.file:
        parser.print_help()
        print("\n❌ Error: Either --input or --file must be specified")
        sys.exit(1)

    # Check dependencies
    if not PYPDF2_AVAILABLE and not PDFPLUMBER_AVAILABLE:
        print("❌ No PDF extraction library available!")
        print("Install at least one: pip install PyPDF2 pdfplumber")
        sys.exit(1)

    # Create extractor
    extractor = PDFTextExtractor(
        output_dir=args.output,
        use_ocr=args.ocr or args.force_ocr,
        max_workers=args.workers
    )

    # Process files
    if args.file:
        # Single file
        pdf_path = Path(args.file)
        if not pdf_path.exists():
            print(f"❌ File not found: {args.file}")
            sys.exit(1)

        print(f"Processing: {pdf_path.name}")
        result = extractor.process_single_pdf(pdf_path, force_ocr=args.force_ocr)

        if result['success']:
            print(f"✅ Success! Output: {result.get('output_file')}")
            print(f"   Method: {result.get('method')}")
            print(f"   Words: {result.get('word_count')}")
        else:
            print(f"❌ Failed: {result.get('error')}")

    else:
        # Directory
        extractor.process_directory(
            args.input,
            recursive=not args.no_recursive,
            force_ocr=args.force_ocr
        )


if __name__ == "__main__":
    main()
