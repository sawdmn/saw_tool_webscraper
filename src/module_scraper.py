#!/usr/bin/env python3
"""
Erweiterter Modul-Scraper für modulbaukasten.ch
Extrahiert: Publikationsdatum, Handlungsziele, Berufe
"""

import json
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


def scrape_module_list(base_url="https://www.modulbaukasten.ch/"):
    """Scrape die Liste aller Module von der Hauptseite."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print(f"Loading module list from {base_url}")
        page.goto(base_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)

        html = page.content()
        browser.close()

        soup = BeautifulSoup(html, 'lxml')
        modules = []

        for item in soup.find_all('app-module-grid-item'):
            link = item.find('a')
            if link:
                href = link.get('href', '')
                # Extract nummer and version from href: /module/107/1/de-DE
                match = re.match(r'/module/(\d+)/(\d+)/', href)
                if match:
                    text = item.get_text().strip()
                    titel_match = re.match(r'(\d{3,4})V(\d+)(.*)', text)
                    if titel_match:
                        modules.append({
                            'nummer': titel_match.group(1),
                            'version': titel_match.group(2),
                            'titel': titel_match.group(3).strip(),
                            'detail_url': f"https://www.modulbaukasten.ch{href}"
                        })

        print(f"Found {len(modules)} modules")
        return modules


def scrape_module_detail(url):
    """Scrape Detailseite eines Moduls."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            html = page.content()
            soup = BeautifulSoup(html, 'lxml')

            details = {}

            # 1. PUBLIKATIONSDATUM
            publish_div = soup.find(class_='publish')
            if publish_div:
                text = publish_div.get_text()
                match = re.search(r'(\d{2}\.\d{2}\.\d{4})', text)
                if match:
                    # Konvertiere zu ISO-Format YYYY-MM-DD
                    date_str = match.group(1)
                    day, month, year = date_str.split('.')
                    details['publikationsdatum'] = f"{year}-{month}-{day}"

            # 2. HANDLUNGSZIELE
            handlungsziele = []
            for panel in soup.find_all('mat-expansion-panel'):
                header = panel.find('mat-expansion-panel-header')
                if header:
                    header_text = header.get_text().strip()
                    # Extrahiere Nummer und Text: "1. Beschreibung..."
                    match = re.match(r'^(\d+)\.\s*(.*)', header_text)
                    if match:
                        handlungsziele.append({
                            'nummer': match.group(1),
                            'beschreibung': match.group(2).strip()
                        })

            details['handlungsziele'] = handlungsziele

            # 3. BERUFE
            # Suche nach span-Elementen mit EFZ/EBA
            berufe = []
            for span in soup.find_all('span', class_='ng-star-inserted'):
                text = span.get_text().strip()
                if 'efz' in text.lower() or 'eba' in text.lower():
                    # Nur wenn es wie ein Berufsname aussieht
                    if len(text) > 10 and len(text) < 150:
                        if text not in berufe:  # Duplikate vermeiden
                            berufe.append(text)

            details['berufe'] = berufe

            return details

        except Exception as e:
            print(f"Error scraping {url}: {e}")
            return None
        finally:
            browser.close()


def create_beruf_mapping(all_berufe):
    """Erstelle Berufs-Liste mit IDs."""
    unique_berufe = sorted(list(set(all_berufe)))
    return [
        {'id': i + 1, 'name': beruf}
        for i, beruf in enumerate(unique_berufe)
    ]


def main():
    """Hauptprogramm."""
    print("="*60)
    print("Modulbaukasten.ch - Vollständiger Scraper")
    print("="*60)

    # 1. Lade Modulliste
    print("\n[1/3] Lade Modulliste...")
    modules = scrape_module_list()

    # 2. Scrape Details für jedes Modul
    print(f"\n[2/3] Scrape Details für {len(modules)} Module...")
    all_berufe = []

    for i, module in enumerate(modules):
        print(f"  [{i+1}/{len(modules)}] Modul {module['nummer']}...", end=" ", flush=True)

        details = scrape_module_detail(module['detail_url'])
        if details:
            module.update(details)
            all_berufe.extend(details.get('berufe', []))
            print("✓")
        else:
            print("✗")

        # Kleine Pause um Server nicht zu überlasten
        time.sleep(0.5)

    # 3. Erstelle Berufs-Mapping
    print("\n[3/3] Erstelle Berufs-Mapping...")
    berufe_liste = create_beruf_mapping(all_berufe)
    beruf_to_id = {beruf['name']: beruf['id'] for beruf in berufe_liste}

    # Ersetze Berufsnamen durch IDs in Modulen
    for module in modules:
        if 'berufe' in module:
            module['berufe_ids'] = [beruf_to_id[b] for b in module['berufe']]
            del module['berufe']  # Entferne redundante Namen

        # Entferne detail_url (nicht mehr benötigt)
        if 'detail_url' in module:
            del module['detail_url']

        # Füge Check-Timestamp hinzu
        module['letzter_check'] = datetime.now().isoformat()

    # 4. Erstelle finales JSON
    output = {
        'meta': {
            'quelle': 'https://www.modulbaukasten.ch/',
            'erstellt': datetime.now().isoformat(),
            'anzahl_module': len(modules),
            'anzahl_berufe': len(berufe_liste)
        },
        'berufe': berufe_liste,
        'module': modules
    }

    # 5. Speichern
    output_file = '/Users/sascha/Documents/git/saw_notizen-inbox/it-module-vollstaendig.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Erfolgreich gespeichert: {output_file}")
    print(f"   Module: {len(modules)}")
    print(f"   Berufe: {len(berufe_liste)}")
    print(f"   Größe: {len(json.dumps(output)) // 1024} KB")


if __name__ == "__main__":
    main()
