#!/usr/bin/env python3
"""Génère build/Planning-samedi-26-juin-2027-A3.pdf depuis build/planning-samedi-print.html (Chromium/Playwright)."""
from pathlib import Path
from playwright.sync_api import sync_playwright

BUILD = Path(__file__).resolve().parent.parent / 'build'
with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page()
    pg.goto((BUILD / 'planning-samedi-print.html').as_uri()); pg.wait_for_timeout(600)
    pg.pdf(path=str(BUILD / 'Planning-samedi-26-juin-2027-A3.pdf'), format='A3', landscape=True,
           print_background=True, prefer_css_page_size=True)
    b.close()
print('PDF ->', BUILD / 'Planning-samedi-26-juin-2027-A3.pdf')
