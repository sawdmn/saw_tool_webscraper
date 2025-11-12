#!/usr/bin/env python3
"""Test HTML-Struktur einer Modul-Seite analysieren"""

from pathlib import Path
from bs4 import BeautifulSoup

# Lade Beispiel-HTML
html_file = Path("/Users/sascha/Documents/git/saw_tool_webscraper/data/raw_html/modul-326-v3.html")

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'lxml')

print("="*60)
print("HTML-Struktur Analyse: Modul 326 V3")
print("="*60)

# 1. PUBLIKATIONSDATUM
print("\n1. PUBLIKATIONSDATUM:")
print("-" * 40)
publish_div = soup.find(class_='publish')
if publish_div:
    print(f"Gefunden: {publish_div.get_text()[:100]}")
else:
    print("NICHT GEFUNDEN")

# 2. HANDLUNGSZIELE / EXPANSION PANELS
print("\n2. HANDLUNGSZIELE (mat-expansion-panel):")
print("-" * 40)
panels = soup.find_all('mat-expansion-panel')
print(f"Anzahl Panels: {len(panels)}")

if panels:
    # Erstes Panel analysieren
    first_panel = panels[0]

    # Header
    header = first_panel.find('mat-expansion-panel-header')
    if header:
        print(f"\nPanel 1 - Header:")
        print(f"  {header.get_text().strip()[:150]}")

    # Content
    content = first_panel.find(class_='mat-expansion-panel-content')
    if content:
        print(f"\nPanel 1 - Content:")
        content_text = content.get_text().strip()
        print(f"  Länge: {len(content_text)} Zeichen")
        print(f"  Preview: {content_text[:200]}")
    else:
        print("\nPanel 1 - Content: NICHT GEFUNDEN")

# 3. BERUFE (mat-chip)
print("\n3. BERUFE (mat-chip):")
print("-" * 40)
chips = soup.find_all('mat-chip')
print(f"Anzahl mat-chip Elemente: {len(chips)}")

if chips:
    print("\nErste 5 mat-chip Inhalte:")
    for i, chip in enumerate(chips[:5], 1):
        text = chip.get_text().strip()
        print(f"  {i}. {text[:100]}")

# 4. ALTERNATIVE: span.ng-star-inserted (was wir fälschlicherweise verwendet haben)
print("\n4. ALTERNATIVE: span.ng-star-inserted:")
print("-" * 40)
spans = soup.find_all('span', class_='ng-star-inserted')
print(f"Anzahl span.ng-star-inserted: {len(spans)}")

if spans:
    # Filter nur die mit EFZ/EBA
    beruf_spans = []
    for span in spans:
        text = span.get_text().strip()
        if ('efz' in text.lower() or 'eba' in text.lower()) and 10 < len(text) < 150:
            beruf_spans.append(text)

    print(f"Davon mit EFZ/EBA: {len(beruf_spans)}")
    print("\nErste 5 EFZ/EBA spans:")
    for i, text in enumerate(beruf_spans[:5], 1):
        print(f"  {i}. {text[:100]}")
