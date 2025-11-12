#!/usr/bin/env python3
"""
Analyse der 68 Module ohne handlungsnotwendige Kenntnisse
"""

import json
from pathlib import Path
from collections import defaultdict, Counter
from bs4 import BeautifulSoup

# Konfiguration
JSON_FILE = Path("/Users/sascha/Documents/git/saw_notizen-inbox/it-module-master.json")
RAW_HTML_DIR = Path("/Users/sascha/Documents/git/saw_tool_webscraper/data/raw_html")


def load_json():
    """Lade JSON-Datei."""
    with open(JSON_FILE, 'r') as f:
        return json.load(f)


def find_modules_without_kenntnisse(data):
    """Finde alle Module ohne handlungsnotwendige Kenntnisse."""
    modules = []

    for master in data['module']:
        for version in master['versionen']:
            # Prüfe ob mindestens ein Handlungsziel Kenntnisse hat
            handlungsziele = version.get('handlungsziele', [])
            hat_kenntnisse = any(
                hz.get('handlungsnotwendige_kenntnisse')
                for hz in handlungsziele
            )

            if handlungsziele and not hat_kenntnisse:
                modules.append({
                    'nummer': master['nummer'],
                    'version': version['version'],
                    'titel': master['titel_master'],
                    'pub_datum': version.get('publikationsdatum', 'N/A'),
                    'anzahl_hz': len(handlungsziele),
                    'berufe_ids': version.get('berufe_ids', [])
                })

    return modules


def analyze_patterns(modules):
    """Analysiere Muster in den Modulen ohne Kenntnisse."""
    print("\n" + "="*60)
    print("MUSTER-ANALYSE")
    print("="*60)

    # Versionen
    versions = Counter(m['version'] for m in modules)
    print("\nVersions-Verteilung:")
    for version, count in sorted(versions.items()):
        print(f"  V{version}: {count} Module")

    # Publikationsjahre
    years = Counter(m['pub_datum'][:4] if m['pub_datum'] != 'N/A' else 'N/A' for m in modules)
    print("\nPublikationsjahre:")
    for year, count in sorted(years.items()):
        print(f"  {year}: {count} Module")

    # Modul-Nummern (erste Stelle)
    first_digits = Counter(m['nummer'][0] for m in modules)
    print("\nModul-Nummern (erste Ziffer):")
    for digit, count in sorted(first_digits.items()):
        print(f"  {digit}xx: {count} Module")

    # Anzahl Handlungsziele
    hz_counts = Counter(m['anzahl_hz'] for m in modules)
    print("\nAnzahl Handlungsziele:")
    for count, num in sorted(hz_counts.items()):
        print(f"  {count} HZ: {num} Module")


def check_html_example(modules):
    """Prüfe HTML eines Beispiel-Moduls."""
    print("\n" + "="*60)
    print("HTML-CHECK (Beispiel-Modul)")
    print("="*60)

    # Wähle erstes Modul
    example = modules[0]
    html_file = RAW_HTML_DIR / f"modul-{example['nummer']}-v{example['version']}.html"

    print(f"\nModul: {example['nummer']} V{example['version']}")
    print(f"Titel: {example['titel']}")
    print(f"HTML-Datei: {html_file.name}")

    if not html_file.exists():
        print("  ✗ HTML-Datei nicht gefunden!")
        return

    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'lxml')

    # Prüfe mat-expansion-panels
    panels = soup.find_all('mat-expansion-panel')
    print(f"\n  Anzahl mat-expansion-panels: {len(panels)}")

    if panels:
        for i, panel in enumerate(panels[:2], 1):  # Erste 2 Panels
            header = panel.find('mat-expansion-panel-header')
            content_div = panel.find(class_='mat-expansion-panel-content')

            print(f"\n  Panel {i}:")
            if header:
                header_text = header.get_text().strip()
                print(f"    Header: {header_text[:80]}")

            if content_div:
                content_text = content_div.get_text().strip()
                print(f"    Content-Länge: {len(content_text)} Zeichen")

                # Prüfe auf "Handlungsnotwendige Kenntnisse"
                if "Handlungsnotwendige Kenntnisse" in content_text:
                    print(f"    ✓ Enthält 'Handlungsnotwendige Kenntnisse'")
                    print(f"    Content Preview: {content_text[:150]}")
                else:
                    print(f"    ✗ KEIN 'Handlungsnotwendige Kenntnisse' gefunden")
                    print(f"    Content Preview: {content_text[:150]}")
            else:
                print(f"    ✗ Kein Content-Div gefunden")


def create_full_list(modules, data):
    """Erstelle vollständige Liste der Module."""
    print("\n" + "="*60)
    print("VOLLSTÄNDIGE LISTE (68 Module ohne Kenntnisse)")
    print("="*60)

    # Beruf-Mapping
    beruf_map = {b['id']: b['name'] for b in data['berufe']}

    print("\nNr. | Modul   | Titel (gekürzt)                          | Pub.Datum  | HZ | Berufe")
    print("-" * 110)

    for i, m in enumerate(modules, 1):
        berufe_names = [beruf_map.get(b, '?')[:20] for b in m['berufe_ids'][:2]]
        berufe_str = ', '.join(berufe_names) if berufe_names else 'Keine'

        print(f"{i:3d} | {m['nummer']:>3s}-V{m['version']:<2s} | {m['titel'][:40]:<40s} | {m['pub_datum']} | {m['anzahl_hz']:2d} | {berufe_str[:30]}")


def main():
    """Hauptprogramm."""
    print("="*60)
    print("ANALYSE: Module ohne handlungsnotwendige Kenntnisse")
    print("="*60)

    # Lade Daten
    print("\n[1/4] Lade JSON-Daten...")
    data = load_json()

    # Finde Module ohne Kenntnisse
    print("[2/4] Identifiziere Module ohne Kenntnisse...")
    modules = find_modules_without_kenntnisse(data)
    print(f"  Gefunden: {len(modules)} Module")

    # Analysen
    print("\n[3/4] Analysiere Muster...")
    analyze_patterns(modules)

    print("\n[4/4] HTML-Check...")
    check_html_example(modules)

    # Liste
    create_full_list(modules, data)

    print("\n" + "="*60)
    print("FAZIT")
    print("="*60)
    print(f"  {len(modules)} von 395 Modulen haben keine Kenntnisse (17.2%)")
    print("  Diese Module haben Handlungsziele, aber keine 'Handlungsnotwendige Kenntnisse' im Content.")
    print("  → Wahrscheinlich haben diese Module auf der Website wirklich keine Kenntnisse.")


if __name__ == "__main__":
    main()
