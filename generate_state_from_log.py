#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Generate scraping state file from activity log
"""

import sys
import os
import json
import re
from pathlib import Path
from datetime import datetime

# Set UTF-8 encoding for Windows console
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())
    os.environ["PYTHONIOENCODING"] = "utf-8"

def parse_activity_log(log_file):
    """Parse activity log and extract completed pages"""
    scraped_pages = set()
    failed_pages = {}
    total_items = 0

    # Pattern to match successful page scrapes (peraturan.go.id format)
    success_pattern1 = re.compile(r'\[Page (\d+)\] Page \d+ successfully scraped with (\d+) items')
    # Pattern to match BPK format
    success_pattern2 = re.compile(r'Page (\d+): Found (\d+) items')
    # Pattern to match failed pages (if any)
    fail_pattern = re.compile(r'\[Page (\d+)\].*failed', re.IGNORECASE)

    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            # Check for successful scrapes (peraturan.go.id format)
            success_match = success_pattern1.search(line)
            if success_match:
                page_num = int(success_match.group(1))
                items_count = int(success_match.group(2))
                scraped_pages.add(page_num)
                total_items += items_count
                continue

            # Check for successful scrapes (BPK format)
            success_match2 = success_pattern2.search(line)
            if success_match2:
                page_num = int(success_match2.group(1))
                items_count = int(success_match2.group(2))
                scraped_pages.add(page_num)
                # Don't add to total_items here to avoid duplicates
                continue

            # Check for failed pages
            fail_match = fail_pattern.search(line)
            if fail_match:
                page_num = int(fail_match.group(1))
                if page_num not in scraped_pages:  # Only add if not already successful
                    failed_pages[str(page_num)] = line.strip()

    # For BPK, count unique pages * average items
    if scraped_pages and total_items == 0:
        # BPK scraper doesn't have the same success message, so count by pages
        total_items = len(scraped_pages) * 10  # Approximate

    return {
        'scraped_pages': sorted(list(scraped_pages)),
        'failed_pages': failed_pages,
        'total_items': total_items,
        'timestamp': datetime.now().isoformat()
    }

def main():
    # Check for both peraturan.go.id and BPK logs
    logs = [
        ('E:/scrapper/logs/scraper_activity.log', 'scraping_state_peraturan_go_id.json'),
        ('E:/scrapper/logs/bpk_activity.log', 'scraping_state_bpk.json')
    ]

    for log_file, state_file in logs:
        log_path = Path(log_file)
        if not log_path.exists():
            print(f"❌ Log file not found: {log_file}")
            continue

        print(f"\n📊 Processing: {log_file}")
        state = parse_activity_log(log_path)

        print(f"   ✓ Found {len(state['scraped_pages'])} completed pages")
        print(f"   ✓ Total items scraped: {state['total_items']}")
        print(f"   ✓ Failed pages: {len(state['failed_pages'])}")

        # Save state file
        output_path = Path('E:/scrapper') / state_file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(state, f, indent=2)

        print(f"   ✅ State saved to: {output_path}")

        # Show page range
        if state['scraped_pages']:
            pages = state['scraped_pages']
            print(f"   📄 Page range: {min(pages)} - {max(pages)}")
            print(f"   🔢 Pages scraped: {', '.join(map(str, pages[:20]))}")
            if len(pages) > 20:
                print(f"      ... and {len(pages) - 20} more pages")

if __name__ == "__main__":
    main()
