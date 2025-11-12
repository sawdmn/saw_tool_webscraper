#!/usr/bin/env python3
"""
Optimierter Modul-Scraper für modulbaukasten.ch
Features: Retry-Logik, Batch-Save, Resume-Funktion
"""

import json
import re
import time
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


# Konfiguration
BASE_URL = "https://www.modulbaukasten.ch"
OUTPUT_DIR = Path("/Users/sascha/Documents/git/saw_notizen-inbox")
PROGRESS_FILE = OUTPUT_DIR / ".scraper_progress.json"
BATCH_SIZE = 50
MAX_RETRIES = 3
RETRY_DELAY = 2  # Sekunden
REQUEST_DELAY = 1  # Sekunde zwischen Requests


def load_progress():
    """Lade gespeicherten Fortschritt."""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r') as f:
            return json.load(f)
    return {'completed': [], 'failed': [], 'modules': []}


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
                wait_time = RETRY_DELAY * (2 ** attempt)  # Exponential backoff
                print(f"\n    Retry {attempt+1}/{max_retries} nach {wait_time}s...", end="", flush=True)
                time.sleep(wait_time)
            else:
                raise e


def scrape_module_list():
    """Scrape die Liste aller Module."""
    print("Lade Modulliste...")
    html = scrape_with_retry(BASE_URL)
    soup = BeautifulSoup(html, 'lxml')

    modules = []
    for item in soup.find_all('app-module-grid-item'):
        link = item.find('a')
        if link:
            href = link.get('href', '')
            match = re.match(r'/module/(\d+)/(\d+)/', href)
            if match:
                text = item.get_text().strip()
                titel_match = re.match(r'(\d{3,4})V(\d+)(.*)', text)
                if titel_match:
                    modules.append({
                        'nummer': titel_match.group(1),
                        'version': titel_match.group(2),
                        'titel': titel_match.group(3).strip(),
                        'detail_url': f"{BASE_URL}{href}"
                    })

    return modules


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
            details['publikationsdatum'] = f"{year}-{month}-{day}"

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


def create_beruf_mapping(all_berufe):
    """Erstelle Berufs-Liste mit IDs."""
    unique_berufe = sorted(list(set(all_berufe)))
    return [{'id': i + 1, 'name': beruf} for i, beruf in enumerate(unique_berufe)]


def save_final_json(modules, berufe_liste):
    """Speichere finales JSON."""
    beruf_to_id = {beruf['name']: beruf['id'] for beruf in berufe_liste}

    # Ersetze Berufsnamen durch IDs
    for module in modules:
        if 'berufe' in module:
            module['berufe_ids'] = [beruf_to_id.get(b) for b in module['berufe'] if b in beruf_to_id]
            del module['berufe']
        if 'detail_url' in module:
            del module['detail_url']

    output = {
        'meta': {
            'quelle': BASE_URL,
            'erstellt': datetime.now().isoformat(),
            'anzahl_module': len(modules),
            'anzahl_berufe': len(berufe_liste)
        },
        'berufe': berufe_liste,
        'module': modules
    }

    output_file = OUTPUT_DIR / 'it-module-vollstaendig.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    return output_file


def main():
    """Hauptprogramm mit Resume-Funktion."""
    print("="*60)
    print("Modulbaukasten.ch - Optimierter Scraper v2")
    print("="*60)

    # Lade oder erstelle Fortschritt
    progress = load_progress()

    # 1. Modulliste laden (falls noch nicht vorhanden)
    if not progress.get('modules'):
        print("\n[1/3] Lade Modulliste...")
        modules = scrape_module_list()
        progress['modules'] = modules
        save_progress(progress)
        print(f"  ✓ {len(modules)} Module gefunden")
    else:
        modules = progress['modules']
        print(f"\n[1/3] Nutze gespeicherte Modulliste ({len(modules)} Module)")

    # 2. Details scrapen
    completed_ids = set(progress.get('completed', []))
    failed_ids = set(progress.get('failed', []))

    print(f"\n[2/3] Scrape Modul-Details:")
    print(f"  Bereits fertig: {len(completed_ids)}")
    print(f"  Fehler: {len(failed_ids)}")
    print(f"  Verbleibend: {len(modules) - len(completed_ids)}")
    print()

    all_berufe = []
    batch_counter = 0

    for i, module in enumerate(modules):
        module_id = f"{module['nummer']}-{module['version']}"

        # Skip bereits verarbeitete Module
        if module_id in completed_ids:
            continue

        print(f"  [{i+1}/{len(modules)}] Modul {module['nummer']}...", end=" ", flush=True)

        try:
            details = scrape_module_detail(module['detail_url'])
            module.update(details)
            all_berufe.extend(details.get('berufe', []))

            progress['completed'].append(module_id)
            if module_id in failed_ids:
                progress['failed'].remove(module_id)

            print("✓")
            batch_counter += 1

            # Batch-Save alle 50 Module
            if batch_counter >= BATCH_SIZE:
                save_progress(progress)
                print(f"  💾 Fortschritt gespeichert ({len(progress['completed'])} Module)")
                batch_counter = 0

        except Exception as e:
            print(f"✗ ({str(e)[:50]}...)")
            progress['failed'].append(module_id)

        time.sleep(REQUEST_DELAY)

    # Final save
    save_progress(progress)

    # 3. Erstelle Berufs-Mapping und finales JSON
    print(f"\n[3/3] Erstelle finales JSON...")
    berufe_liste = create_beruf_mapping(all_berufe)
    output_file = save_final_json(modules, berufe_liste)

    # Cleanup
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()

    print(f"\n✅ Erfolgreich abgeschlossen!")
    print(f"   Datei: {output_file}")
    print(f"   Module: {len(modules)}")
    print(f"   Erfolgreich: {len(progress['completed'])}")
    print(f"   Fehler: {len(progress['failed'])}")
    print(f"   Berufe: {len(berufe_liste)}")
    print(f"   Größe: {output_file.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
