#!/usr/bin/env python3
"""
Phase 2: Lokales HTML-Parsing mit korrekter Datenextraktion
- Handlungsziele MIT handlungsnotwendigen Kenntnissen
- Berufe aus mat-chip
- Publikationsdatum
"""

import json
import re
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from bs4 import BeautifulSoup


# Konfiguration
RAW_HTML_DIR = Path("/Users/sascha/Documents/git/saw_tool_webscraper/data/raw_html")
OUTPUT_DIR = Path("/Users/sascha/Documents/git/wiss_data_it-module/data")


def calculate_hash(pub_datum):
    """Berechne Hash für Change Detection."""
    if not pub_datum:
        return None
    return hashlib.sha256(pub_datum.encode()).hexdigest()[:16]


def parse_module_html(html_file):
    """Parse HTML-Datei und extrahiere alle Daten."""
    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'lxml')
    details = {}

    # 1. PUBLIKATIONSDATUM
    publish_div = soup.find(class_='publish')
    if publish_div:
        text = publish_div.get_text()
        match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
        if match:
            date_str = match.group(1)
            day, month, year = date_str.split('.')
            pub_datum = f"{year}-{month}-{day}"
            details['publikationsdatum'] = pub_datum
            details['content_hash'] = calculate_hash(pub_datum)

    # 2. HANDLUNGSZIELE MIT HANDLUNGSNOTWENDIGEN KENNTNISSEN
    handlungsziele = []
    for panel in soup.find_all('mat-expansion-panel'):
        # Header = Handlungsziel
        header = panel.find('mat-expansion-panel-header')
        if header:
            header_text = header.get_text().strip()
            match = re.match(r'^(\d+)\.\s*(.*)', header_text)
            if match:
                handlungsziel = {
                    'nummer': match.group(1),
                    'beschreibung': match.group(2).strip()
                }

                # Content = Handlungsnotwendige Kenntnisse
                content_div = panel.find(class_='mat-expansion-panel-content')
                if content_div:
                    content_text = content_div.get_text().strip()

                    # Extrahiere Kenntnisse (Format: "1. Kennt...", "2. Kennt...", etc.)
                    kenntnisse = re.findall(
                        r'\d+\.\s*Kennt[^\.]+(?:\([^\)]+\))?\.(?:\s*\([^\)]+\))?',
                        content_text
                    )
                    if kenntnisse:
                        handlungsziel['handlungsnotwendige_kenntnisse'] = [
                            k.strip() for k in kenntnisse
                        ]

                handlungsziele.append(handlungsziel)

    details['handlungsziele'] = handlungsziele

    # 3. BERUFE (korrekt aus mat-chip)
    berufe = []
    for chip in soup.find_all('mat-chip'):
        text = chip.get_text().strip()
        if text and text not in berufe:
            berufe.append(text)

    details['berufe'] = berufe
    details['letzter_check'] = datetime.now().isoformat()

    return details


def group_by_master(modules):
    """Gruppiere Module nach Master-ID."""
    masters = defaultdict(list)
    for mod in modules:
        masters[mod['nummer']].append(mod)

    # Sortiere Versionen innerhalb jedes Masters
    for master_key in masters:
        masters[master_key].sort(key=lambda x: int(x['version']))

    return dict(masters)


def create_beruf_mapping(all_berufe):
    """Erstelle Berufs-Liste mit IDs."""
    unique_berufe = sorted(list(set(all_berufe)))
    return [{'id': i + 1, 'name': beruf} for i, beruf in enumerate(unique_berufe)]


def save_final_json(masters, berufe_liste):
    """Speichere finales JSON mit Master-Modul-Struktur."""
    beruf_to_id = {beruf['name']: beruf['id'] for beruf in berufe_liste}

    # Erstelle Master-Module
    master_modules = []
    for nummer in sorted(masters.keys(), key=int):
        versionen = masters[nummer]

        # Ersetze Berufsnamen durch IDs in allen Versionen
        for ver in versionen:
            if 'berufe' in ver:
                ver['berufe_ids'] = [beruf_to_id.get(b) for b in ver['berufe'] if b in beruf_to_id]
                del ver['berufe']

        # Neueste Version für Master-Titel
        neueste = versionen[-1]

        master_modules.append({
            'master_id': f"M{nummer}",
            'nummer': nummer,
            'titel_master': neueste.get('titel', ''),
            'anzahl_versionen': len(versionen),
            'versionen': versionen
        })

    # Statistiken für handlungsnotwendige Kenntnisse
    total_handlungsziele = 0
    total_kenntnisse = 0
    versionen_mit_kenntnissen = 0

    for master in master_modules:
        for version in master['versionen']:
            if 'handlungsziele' in version:
                total_handlungsziele += len(version['handlungsziele'])
                for hz in version['handlungsziele']:
                    if 'handlungsnotwendige_kenntnisse' in hz:
                        total_kenntnisse += len(hz['handlungsnotwendige_kenntnisse'])
                        versionen_mit_kenntnissen += 1

    output = {
        'meta': {
            'quelle': 'https://www.modulbaukasten.ch',
            'erstellt': datetime.now().isoformat(),
            'anzahl_master_module': len(master_modules),
            'anzahl_versionen_total': sum(m['anzahl_versionen'] for m in master_modules),
            'anzahl_berufe': len(berufe_liste),
            'anzahl_handlungsziele_total': total_handlungsziele,
            'anzahl_kenntnisse_total': total_kenntnisse,
            'versionen_mit_kenntnissen': versionen_mit_kenntnissen,
            'system': 'Phase 2: Lokales Parsing mit vollständiger Datenextraktion'
        },
        'berufe': berufe_liste,
        'module': master_modules
    }

    output_file = OUTPUT_DIR / 'it-module-master.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_file


def main():
    """Hauptprogramm - Phase 2: Lokales Parsing."""
    print("="*60)
    print("Phase 2: Lokales HTML-Parsing")
    print("="*60)

    # 1. Lade Modul-Index
    print("\n[1/3] Lade Modul-Index...")
    index_file = RAW_HTML_DIR / 'module_index.json'

    with open(index_file, 'r') as f:
        module_index = json.load(f)

    print(f"  {len(module_index)} Module im Index")

    # 2. Parse alle HTML-Dateien
    print(f"\n[2/3] Parse {len(module_index)} HTML-Dateien:\n")

    all_modules = []
    all_berufe = []
    completed = 0
    failed = 0

    for i, mod_info in enumerate(module_index, 1):
        html_file = RAW_HTML_DIR / mod_info['html_file']

        print(f"  [{i}/{len(module_index)}] {mod_info['html_file']}...", end=" ", flush=True)

        try:
            details = parse_module_html(html_file)

            module = {
                'nummer': mod_info['nummer'],
                'version': mod_info['version'],
                'titel': mod_info['titel'],
                **details
            }

            all_modules.append(module)
            all_berufe.extend(details.get('berufe', []))
            completed += 1
            print("✓")

        except Exception as e:
            print(f"✗ ({str(e)[:40]})")
            failed += 1

    # 3. Gruppiere nach Master und erstelle JSON
    print(f"\n[3/3] Erstelle Master-Modul-JSON...")
    masters = group_by_master(all_modules)
    berufe_liste = create_beruf_mapping(all_berufe)
    output_file = save_final_json(masters, berufe_liste)

    # Berechne Statistiken
    file_size = output_file.stat().st_size

    print(f"\n✅ Phase 2 abgeschlossen!")
    print(f"   Datei: {output_file}")
    print(f"   Master-Module: {len(masters)}")
    print(f"   Versionen total: {sum(len(v) for v in masters.values())}")
    print(f"   Erfolgreich: {completed}")
    print(f"   Fehler: {failed}")
    print(f"   Berufe: {len(berufe_liste)}")
    print(f"   Größe: {file_size // 1024} KB")

    # Zeige Beispiel-Handlungsziel mit Kenntnissen
    if all_modules:
        print(f"\n📋 Beispiel: Modul {all_modules[0]['nummer']} V{all_modules[0]['version']}")
        if all_modules[0].get('handlungsziele'):
            hz = all_modules[0]['handlungsziele'][0]
            print(f"   Handlungsziel {hz.get('nummer')}: {hz.get('beschreibung')[:60]}...")
            if hz.get('handlungsnotwendige_kenntnisse'):
                print(f"   → {len(hz['handlungsnotwendige_kenntnisse'])} Kenntnisse")
                print(f"      1. {hz['handlungsnotwendige_kenntnisse'][0][:70]}...")


if __name__ == "__main__":
    main()
