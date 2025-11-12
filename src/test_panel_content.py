#!/usr/bin/env python3
"""Detaillierte Analyse des mat-expansion-panel Contents"""

from pathlib import Path
from bs4 import BeautifulSoup
import re

# Lade Beispiel-HTML
html_file = Path("/Users/sascha/Documents/git/saw_tool_webscraper/data/raw_html/modul-326-v3.html")

with open(html_file, 'r', encoding='utf-8') as f:
    html = f.read()

soup = BeautifulSoup(html, 'lxml')

print("="*60)
print("DETAILLIERTE PANEL-CONTENT ANALYSE")
print("="*60)

panels = soup.find_all('mat-expansion-panel')

for i, panel in enumerate(panels, 1):
    print(f"\n{'='*60}")
    print(f"PANEL {i}")
    print(f"{'='*60}")

    # Header
    header = panel.find('mat-expansion-panel-header')
    if header:
        header_text = header.get_text().strip()
        print(f"\nHeader:")
        print(f"  {header_text}")

        # Extrahiere Nummer und Beschreibung
        match = re.match(r'^(\d+)\.\s*(.*)', header_text)
        if match:
            print(f"\n  → Nummer: {match.group(1)}")
            print(f"  → Beschreibung: {match.group(2)}")

    # Content
    content_div = panel.find(class_='mat-expansion-panel-content')
    if content_div:
        content_text = content_div.get_text().strip()

        print(f"\nContent:")
        print(f"  Länge: {len(content_text)} Zeichen")

        # Suche nach "Handlungsnotwendige Kenntnisse:"
        if "Handlungsnotwendige Kenntnisse:" in content_text:
            print("\n  ✓ Enthält 'Handlungsnotwendige Kenntnisse:'")

            # Extrahiere die Kenntnisse (Nummern 1., 2., 3., etc.)
            kenntnisse = re.findall(r'\d+\.\s*Kennt[^\.]+\.', content_text)
            print(f"  → {len(kenntnisse)} Kenntnisse gefunden")

            for j, kenntnis in enumerate(kenntnisse, 1):
                print(f"\n  Kenntnis {j}:")
                print(f"    {kenntnis}")
        else:
            print(f"\n  Content Text:")
            print(f"    {content_text[:300]}")
    else:
        print("\n  ✗ Kein Content gefunden")

    if i >= 2:  # Nur erste 2 Panels im Detail
        print(f"\n[... {len(panels) - 2} weitere Panels ...]")
        break
