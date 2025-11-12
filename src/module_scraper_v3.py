#!/usr/bin/env python3
"""
Master-Modul-System mit Deduplizierung und Change Detection
Version 3.0 - Final
"""

import json
import re
import time
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# Konfiguration
BASE_URL = "https://www.modulbaukasten.ch"
OUTPUT_DIR = Path("/Users/sascha/Documents/git/saw_notizen-inbox")
PROGRESS_FILE = OUTPUT_DIR / ".scraper_progress_v3.json"
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 2
REQUEST_DELAY = 1


def calculate_hash(pub_datum):
    """Berechne Hash für Change Detection."""
    if not pub_datum:
        return None
    return hashlib.sha256(pub_datum.encode()).hexdigest()[:16]


def load_progress():
    """Lade gespeicherten Fortschritt."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': [], 'modules': {}}


def save_progress(progress):
    """Speichere Fortschritt."""
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f, indent=2)


def scrape_with_retry(url, max_retries=MAX_RETRIES):
    """Scrape URL mit Retry-Logik."""
    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(2000)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = RETRY_DELAY * (2 ** attempt)
                print(f" Retry {attempt+1}/{max_retries}...", end="", flush=True)
                time.sleep(wait_time)
            else:
                raise e


def scrape_module_list():
    """Scrape und dedupliziere Modulliste."""
    print("Lade Modulliste...")
    html = scrape_with_retry(BASE_URL)
    soup = BeautifulSoup(html, 'lxml')

    # Sammle ALLE Module (inkl. Duplikate)
    all_modules = []
    for item in soup.find_all('app-module-grid-item'):
        link = item.find('a')
        if link:
            href = link.get('href', '')
            match = re.match(r'/module/(\d+)/(\d+)/', href)
            if match:
                text = item.get_text().strip()
                titel_match = re.match(r'(\d{3,4})V(\d+)(.*)', text)
                if titel_match:
                    all_modules.append({
                        'nummer': titel_match.group(1),
                        'version': titel_match.group(2),
                        'titel': titel_match.group(3).strip(),
                        'detail_url': f"{BASE_URL}{href}"
                    })

    # Deduplizierung: Gruppiere nach nummer+version
    unique_modules = {}
    for mod in all_modules:
        key = f"{mod['nummer']}-{mod['version']}"
        if key not in unique_modules:
            unique_modules[key] = mod

    print(f"  Total: {len(all_modules)} Einträge")
    print(f"  Duplikate: {len(all_modules) - len(unique_modules)}")
    print(f"  Einzigartig: {len(unique_modules)}")

    return list(unique_modules.values())


def scrape_module_detail(url):
    """Scrape Detailseite eines Moduls."""
    html = scrape_with_retry(url)
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

    # 2. HANDLUNGSZIELE
    handlungsziele = []
    for panel in soup.find_all('mat-expansion-panel'):
        header = panel.find('mat-expansion-panel-header')
        if header:
            header_text = header.get_text().strip()
            match = re.match(r'^(\d+)\.\s*(.*)', header_text)
            if match:
                handlungsziele.append({
                    'nummer': match.group(1),
                    'beschreibung': match.group(2).strip()
                })

    details['handlungsziele'] = handlungsziele

    # 3. BERUFE
    berufe = []
    for span in soup.find_all('span', class_='ng-star-inserted'):
        text = span.get_text().strip()
        if ('efz' in text.lower() or 'eba' in text.lower()) and 10 < len(text) < 150:
            if text not in berufe:
                berufe.append(text)

    details['berufe'] = berufe
    details['letzter_check'] = datetime.now().isoformat()

    return details


def group_by_master(modules):
    """Gruppiere Module nach Master-ID (Nummer)."""
    masters = defaultdict(list)

    for mod in modules:
        master_key = mod['nummer']
        masters[master_key].append(mod)

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
            if 'detail_url' in ver:
                del ver['detail_url']

        # Neueste Version für Master-Titel
        neueste = versionen[-1]

        master_modules.append({
            'master_id': f"M{nummer}",
            'nummer': nummer,
            'titel_master': neueste.get('titel', ''),
            'anzahl_versionen': len(versionen),
            'versionen': versionen
        })

    output = {
        'meta': {
            'quelle': BASE_URL,
            'erstellt': datetime.now().isoformat(),
            'anzahl_master_module': len(master_modules),
            'anzahl_versionen_total': sum(m['anzahl_versionen'] for m in master_modules),
            'anzahl_berufe': len(berufe_liste),
            'system': 'Master-Modul mit Deduplizierung und Change Detection'
        },
        'berufe': berufe_liste,
        'module': master_modules
    }

    output_file = OUTPUT_DIR / 'it-module-master.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_file


def main():
    """Hauptprogramm."""
    print("="*60)
    print("Master-Modul-System v3.0")
    print("="*60)

    # 1. Modulliste laden und deduplizieren
    print("\n[1/4] Lade und dedupliziere Modulliste...")
    unique_modules = scrape_module_list()

    # 2. Details scrapen
    print(f"\n[2/4] Scrape Details für {len(unique_modules)} einzigartige Module:")
    all_berufe = []
    completed = 0
    failed = 0

    for i, module in enumerate(unique_modules):
        print(f"  [{i+1}/{len(unique_modules)}] Modul {module['nummer']} V{module['version']}...", end=" ", flush=True)

        try:
            details = scrape_module_detail(module['detail_url'])
            module.update(details)
            all_berufe.extend(details.get('berufe', []))
            completed += 1
            print("✓")

            # Batch-Save
            if (i + 1) % BATCH_SIZE == 0:
                print(f"  💾 Fortschritt: {completed} Module")

        except Exception as e:
            print(f"✗ ({str(e)[:40]})")
            failed += 1

        time.sleep(REQUEST_DELAY)

    # 3. Gruppiere nach Master
    print(f"\n[3/4] Gruppiere nach Master-Modulen...")
    masters = group_by_master(unique_modules)
    print(f"  Master-Module: {len(masters)}")

    # 4. Erstelle finales JSON
    print(f"\n[4/4] Erstelle finales JSON...")
    berufe_liste = create_beruf_mapping(all_berufe)
    output_file = save_final_json(masters, berufe_liste)

    # Cleanup
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    print(f"\n✅ Erfolgreich abgeschlossen!")
    print(f"   Datei: {output_file}")
    print(f"   Master-Module: {len(masters)}")
    print(f"   Versionen total: {sum(len(v) for v in masters.values())}")
    print(f"   Erfolgreich: {completed}")
    print(f"   Fehler: {failed}")
    print(f"   Berufe: {len(berufe_liste)}")
    print(f"   Größe: {output_file.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
