#!/usr/bin/env python3
"""
Parallel Master-Modul-Scraper mit 5 Workers
Schnellere Ausführung durch Threading
"""

import json
import re
import time
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import threading


# Konfiguration
BASE_URL = "https://www.modulbaukasten.ch"
OUTPUT_DIR = Path("/Users/sascha/Documents/git/saw_notizen-inbox")
NUM_WORKERS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2

# Thread-safe Counter
progress_lock = threading.Lock()
progress_counter = {'completed': 0, 'failed': 0}


def calculate_hash(pub_datum):
    """Berechne Hash für Change Detection."""
    if not pub_datum:
        return None
    return hashlib.sha256(pub_datum.encode()).hexdigest()[:16]


def scrape_with_retry(url, max_retries=MAX_RETRIES):
    """Scrape URL mit Retry-Logik."""
    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.goto(url, wait_until="networkidle", timeout=30000)
                page.wait_for_timeout(1500)
                html = page.content()
                browser.close()
                return html
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                raise e


def scrape_module_list():
    """Scrape und dedupliziere Modulliste."""
    print("Lade Modulliste...")
    html = scrape_with_retry(BASE_URL)
    soup = BeautifulSoup(html, 'lxml')

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

    # Deduplizierung
    unique_modules = {}
    for mod in all_modules:
        key = f"{mod['nummer']}-{mod['version']}"
        if key not in unique_modules:
            unique_modules[key] = mod

    modules_list = list(unique_modules.values())
    print(f"  Einzigartig: {len(modules_list)} Module")
    return modules_list


def scrape_module_detail(module, index, total):
    """Scrape Detailseite eines Moduls (für Threading)."""
    try:
        html = scrape_with_retry(module['detail_url'])
        soup = BeautifulSoup(html, 'lxml')

        # 1. PUBLIKATIONSDATUM
        publish_div = soup.find(class_='publish')
        if publish_div:
            text = publish_div.get_text()
            match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
            if match:
                date_str = match.group(1)
                day, month, year = date_str.split('.')
                pub_datum = f"{year}-{month}-{day}"
                module['publikationsdatum'] = pub_datum
                module['content_hash'] = calculate_hash(pub_datum)

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
        module['handlungsziele'] = handlungsziele

        # 3. BERUFE
        berufe = []
        for span in soup.find_all('span', class_='ng-star-inserted'):
            text = span.get_text().strip()
            if ('efz' in text.lower() or 'eba' in text.lower()) and 10 < len(text) < 150:
                if text not in berufe:
                    berufe.append(text)
        module['berufe'] = berufe
        module['letzter_check'] = datetime.now().isoformat()

        with progress_lock:
            progress_counter['completed'] += 1
            print(f"  [{progress_counter['completed']}/{total}] Modul {module['nummer']} V{module['version']}... ✓")

        return module, None

    except Exception as e:
        with progress_lock:
            progress_counter['failed'] += 1
            print(f"  [{progress_counter['completed'] + progress_counter['failed']}/{total}] Modul {module['nummer']} V{module['version']}... ✗")
        return module, str(e)


def group_by_master(modules):
    """Gruppiere Module nach Master-ID."""
    masters = defaultdict(list)
    for mod in modules:
        masters[mod['nummer']].append(mod)

    for master_key in masters:
        masters[master_key].sort(key=lambda x: int(x['version']))

    return dict(masters)


def create_beruf_mapping(all_berufe):
    """Erstelle Berufs-Liste mit IDs."""
    unique_berufe = sorted(list(set(all_berufe)))
    return [{'id': i + 1, 'name': beruf} for i, beruf in enumerate(unique_berufe)]


def save_final_json(masters, berufe_liste):
    """Speichere finales JSON."""
    beruf_to_id = {beruf['name']: beruf['id'] for beruf in berufe_liste}

    master_modules = []
    for nummer in sorted(masters.keys(), key=int):
        versionen = masters[nummer]

        for ver in versionen:
            if 'berufe' in ver:
                ver['berufe_ids'] = [beruf_to_id.get(b) for b in ver['berufe'] if b in beruf_to_id]
                del ver['berufe']
            if 'detail_url' in ver:
                del ver['detail_url']

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
            'system': 'Master-Modul mit Parallel-Scraping (5 Workers)'
        },
        'berufe': berufe_liste,
        'module': master_modules
    }

    output_file = OUTPUT_DIR / 'it-module-master.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_file


def main():
    """Hauptprogramm mit Parallel-Scraping."""
    start_time = time.time()

    print("="*60)
    print(f"Parallel Master-Modul-Scraper ({NUM_WORKERS} Workers)")
    print("="*60)

    # 1. Modulliste laden
    print("\n[1/4] Lade Modulliste...")
    modules = scrape_module_list()
    total = len(modules)

    # 2. Parallel scrapen
    print(f"\n[2/4] Scrape {total} Module parallel ({NUM_WORKERS} Workers):\n")

    all_berufe = []

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {
            executor.submit(scrape_module_detail, mod, i+1, total): mod
            for i, mod in enumerate(modules)
        }

        for future in as_completed(futures):
            result_module, error = future.result()
            if error is None and 'berufe' in result_module:
                all_berufe.extend(result_module['berufe'])

    # 3. Gruppiere nach Master
    print(f"\n[3/4] Gruppiere nach Master-Modulen...")
    masters = group_by_master(modules)
    print(f"  Master-Module: {len(masters)}")

    # 4. Erstelle finales JSON
    print(f"\n[4/4] Erstelle finales JSON...")
    berufe_liste = create_beruf_mapping(all_berufe)
    output_file = save_final_json(masters, berufe_liste)

    elapsed = time.time() - start_time

    print(f"\n✅ Erfolgreich abgeschlossen!")
    print(f"   Datei: {output_file}")
    print(f"   Master-Module: {len(masters)}")
    print(f"   Versionen: {sum(len(v) for v in masters.values())}")
    print(f"   Erfolgreich: {progress_counter['completed']}")
    print(f"   Fehler: {progress_counter['failed']}")
    print(f"   Berufe: {len(berufe_liste)}")
    print(f"   Größe: {output_file.stat().st_size // 1024} KB")
    print(f"   Zeit: {elapsed:.1f} Sekunden")


if __name__ == "__main__":
    main()
