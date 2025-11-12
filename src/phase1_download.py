#!/usr/bin/env python3
"""
Phase 1: HTML-Download für alle Module
Speichert rohe HTML-Dateien für spätere lokale Verarbeitung
"""

import json
import re
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import threading


# Konfiguration
BASE_URL = "https://www.modulbaukasten.ch"
OUTPUT_DIR = Path("/Users/sascha/Documents/git/saw_tool_webscraper/data/raw_html")
NUM_WORKERS = 5
MAX_RETRIES = 3
RETRY_DELAY = 2

# Thread-safe Counter
progress_lock = threading.Lock()
progress_counter = {'completed': 0, 'failed': 0}


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


def download_module_html(module, index, total):
    """Download HTML eines Moduls (für Threading)."""
    try:
        html = scrape_with_retry(module['detail_url'])

        # Speichere HTML
        filename = f"modul-{module['nummer']}-v{module['version']}.html"
        filepath = OUTPUT_DIR / filename

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(html)

        with progress_lock:
            progress_counter['completed'] += 1
            print(f"  [{progress_counter['completed']}/{total}] {filename}... ✓")

        return module, None

    except Exception as e:
        with progress_lock:
            progress_counter['failed'] += 1
            print(f"  [{progress_counter['completed'] + progress_counter['failed']}/{total}] Modul {module['nummer']} V{module['version']}... ✗")
        return module, str(e)


def save_module_index(modules):
    """Speichere Modul-Index für Phase 2."""
    index_file = OUTPUT_DIR / 'module_index.json'

    module_index = []
    for mod in modules:
        module_index.append({
            'nummer': mod['nummer'],
            'version': mod['version'],
            'titel': mod['titel'],
            'html_file': f"modul-{mod['nummer']}-v{mod['version']}.html"
        })

    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(module_index, f, indent=2, ensure_ascii=False)

    return index_file


def main():
    """Hauptprogramm - Phase 1: HTML Download."""
    start_time = time.time()

    print("="*60)
    print(f"Phase 1: HTML-Download ({NUM_WORKERS} Workers)")
    print("="*60)

    # Erstelle Output-Verzeichnis
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Modulliste laden
    print("\n[1/3] Lade Modulliste...")
    modules = scrape_module_list()
    total = len(modules)

    # 2. Parallel HTML herunterladen
    print(f"\n[2/3] Downloade {total} HTML-Seiten ({NUM_WORKERS} Workers):\n")

    failed_modules = []

    with ThreadPoolExecutor(max_workers=NUM_WORKERS) as executor:
        futures = {
            executor.submit(download_module_html, mod, i+1, total): mod
            for i, mod in enumerate(modules)
        }

        for future in as_completed(futures):
            result_module, error = future.result()
            if error:
                failed_modules.append({
                    'module': result_module,
                    'error': error
                })

    # 3. Speichere Index
    print(f"\n[3/3] Erstelle Modul-Index...")
    index_file = save_module_index(modules)

    elapsed = time.time() - start_time

    print(f"\n✅ Phase 1 abgeschlossen!")
    print(f"   Verzeichnis: {OUTPUT_DIR}")
    print(f"   HTML-Dateien: {progress_counter['completed']}")
    print(f"   Fehler: {progress_counter['failed']}")
    print(f"   Index: {index_file}")
    print(f"   Zeit: {elapsed:.1f} Sekunden")

    if failed_modules:
        print(f"\n⚠️  {len(failed_modules)} Module konnten nicht geladen werden:")
        for fm in failed_modules[:5]:
            print(f"     - Modul {fm['module']['nummer']} V{fm['module']['version']}")


if __name__ == "__main__":
    main()
