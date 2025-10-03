#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Update BPK state file to reflect latest scraped page
"""

import json
from datetime import datetime
from pathlib import Path

def update_bpk_state(last_page=3450):
    """Update BPK state file with pages 1 to last_page"""

    state_file = Path('E:/scrapper/scraping_state_bpk.json')

    # Generate list of pages from 1 to last_page
    scraped_pages = list(range(1, last_page + 1))

    state = {
        'scraped_pages': scraped_pages,
        'failed_pages': {},
        'total_items': len(scraped_pages) * 10,  # Approximate 10 items per page
        'timestamp': datetime.now().isoformat()
    }

    # Save state file
    with open(state_file, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2)

    print(f"✅ Updated BPK state file: {state_file}")
    print(f"   📊 Pages: 1 - {last_page} ({len(scraped_pages)} pages)")
    print(f"   📈 Estimated items: {state['total_items']}")
    print(f"   ⏰ Timestamp: {state['timestamp']}")
    print(f"\n🚀 Next scraping will resume from page {last_page + 1}")

if __name__ == "__main__":
    update_bpk_state(3450)
