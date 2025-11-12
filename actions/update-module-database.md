# Update IT-Module Datenbank

**Zweck**: Aktualisiert die IT-Module Datenbank von modulbaukasten.ch und erkennt Änderungen

## Beschreibung

Diese Action führt ein vollständiges Update der IT-Module Datenbank durch:
- Download aller aktuellen HTML-Seiten
- Lokales Parsing mit korrekter Datenextraktion
- Change Detection via content_hash
- Validierung der Datenqualität
- Erstellung eines Update-Reports

## Parameter

Keine Parameter erforderlich - läuft vollautomatisch.

## Verwendung

```bash
# In Claude Code Session im Repo saw_tool_webscraper:
/Users/sascha/Documents/git/saw_tool_webscraper/actions/update-module-database.md
```

Oder:

```
Führe die Action actions/update-module-database.md aus
```

## Prompt für Claude Code

---

Aktualisiere die IT-Module Datenbank von modulbaukasten.ch.

### Voraussetzungen

1. **Aktuelles Working Directory**: `/Users/sascha/Documents/git/saw_tool_webscraper`
2. **Python-Umgebung**: Python 3 mit beautifulsoup4, lxml, playwright
3. **Vorherige Datenbank**: `/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank/it-module-master.json`

### Ablauf (3 Phasen)

#### Phase 1: HTML-Download (Parallel)

Führe `src/phase1_download.py` aus:
- Lädt alle Modul-HTML-Seiten von https://www.modulbaukasten.ch/
- 5 parallele Workers für schnelles Download
- Speichert in `data/raw_html/`
- Erstellt `data/raw_html/module_index.json`

```bash
python3 src/phase1_download.py
```

**Erwartete Ausgabe:**
- Anzahl heruntergeladene Module
- Fehleranzahl (sollte 0 sein)
- Zeit in Sekunden

#### Phase 2: Lokales Parsing

Führe `src/phase2_parse.py` aus:
- Parsed alle HTML-Dateien lokal
- Extrahiert:
  - Publikationsdatum + content_hash
  - Handlungsziele mit Beschreibungen
  - Handlungsnotwendige Kenntnisse
  - Berufe (korrekt via mat-chip)
- Speichert neue JSON in `/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank/it-module-master.json`

```bash
python3 src/phase2_parse.py
```

**Erwartete Ausgabe:**
- Anzahl geparste Module
- Fehleranzahl
- Anzahl Berufe, Handlungsziele, Kenntnisse

#### Phase 3: Validierung

Führe `src/phase3_validate.py` aus:
- Prüft Vollständigkeit
- Erstellt Validierungsbericht
- Speichert in `data/validation_report.txt`

```bash
python3 src/phase3_validate.py
```

**Erwartete Ausgabe:**
- Datenqualität in Prozent
- Anzahl Module ohne Berufe/Kenntnisse
- Statistiken

#### Phase 4: Change Detection

Erstelle einen Update-Report mit Änderungen seit letztem Update:

**Script:** `src/create_update_report.py`

```python
#!/usr/bin/env python3
"""
Erstellt Update-Report mit Änderungen seit letztem Update
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Pfade
CURRENT_DB = Path("/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank/it-module-master.json")
BACKUP_DIR = Path("/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank/backups")
REPORT_DIR = Path("/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank")

def find_latest_backup():
    """Finde neuestes Backup."""
    if not BACKUP_DIR.exists():
        return None

    backups = sorted(BACKUP_DIR.glob("it-module-master-*.json"), reverse=True)
    return backups[0] if backups else None

def compare_databases(old_db, new_db):
    """Vergleiche zwei Datenbanken und finde Änderungen."""
    changes = {
        'neue_module': [],
        'geaenderte_module': [],
        'geloeschte_module': [],
        'neue_berufe': [],
        'statistik_alt': {},
        'statistik_neu': {}
    }

    # Erstelle Hash-Maps
    old_modules = {}
    for master in old_db['module']:
        for version in master['versionen']:
            key = f"{master['nummer']}-V{version['version']}"
            old_modules[key] = {
                'master': master,
                'version': version
            }

    new_modules = {}
    for master in new_db['module']:
        for version in master['versionen']:
            key = f"{master['nummer']}-V{version['version']}"
            new_modules[key] = {
                'master': master,
                'version': version
            }

    # Finde neue Module
    for key in new_modules:
        if key not in old_modules:
            changes['neue_module'].append(key)

    # Finde gelöschte Module
    for key in old_modules:
        if key not in new_modules:
            changes['geloeschte_module'].append(key)

    # Finde geänderte Module (via content_hash)
    for key in new_modules:
        if key in old_modules:
            old_hash = old_modules[key]['version'].get('content_hash')
            new_hash = new_modules[key]['version'].get('content_hash')

            if old_hash != new_hash:
                changes['geaenderte_module'].append({
                    'modul': key,
                    'alt_datum': old_modules[key]['version'].get('publikationsdatum'),
                    'neu_datum': new_modules[key]['version'].get('publikationsdatum'),
                    'titel': new_modules[key]['master']['titel_master']
                })

    # Berufe-Vergleich
    old_berufe = {b['name'] for b in old_db['berufe']}
    new_berufe = {b['name'] for b in new_db['berufe']}
    changes['neue_berufe'] = sorted(new_berufe - old_berufe)

    # Statistiken
    changes['statistik_alt'] = {
        'master_module': old_db['meta']['anzahl_master_module'],
        'versionen': old_db['meta']['anzahl_versionen_total'],
        'berufe': old_db['meta']['anzahl_berufe'],
        'handlungsziele': old_db['meta'].get('anzahl_handlungsziele_total', 0),
        'kenntnisse': old_db['meta'].get('anzahl_kenntnisse_total', 0)
    }

    changes['statistik_neu'] = {
        'master_module': new_db['meta']['anzahl_master_module'],
        'versionen': new_db['meta']['anzahl_versionen_total'],
        'berufe': new_db['meta']['anzahl_berufe'],
        'handlungsziele': new_db['meta'].get('anzahl_handlungsziele_total', 0),
        'kenntnisse': new_db['meta'].get('anzahl_kenntnisse_total', 0)
    }

    return changes

def create_report(changes, old_date, new_date):
    """Erstelle Markdown-Report."""
    report = []

    report.append("# IT-Module Datenbank Update-Report")
    report.append("")
    report.append(f"**Update-Datum:** {new_date}")
    report.append(f"**Vorherige Version:** {old_date}")
    report.append("")
    report.append("---")
    report.append("")

    # Zusammenfassung
    report.append("## Zusammenfassung")
    report.append("")

    total_changes = len(changes['neue_module']) + len(changes['geaenderte_module']) + len(changes['geloeschte_module'])

    if total_changes == 0:
        report.append("✅ **Keine Änderungen** - Datenbank ist aktuell")
    else:
        report.append(f"📊 **{total_changes} Änderungen** erkannt:")
        report.append("")
        report.append(f"- 🆕 Neue Module: {len(changes['neue_module'])}")
        report.append(f"- ♻️ Geänderte Module: {len(changes['geaenderte_module'])}")
        report.append(f"- 🗑️ Gelöschte Module: {len(changes['geloeschte_module'])}")
        report.append(f"- 👔 Neue Berufe: {len(changes['neue_berufe'])}")

    report.append("")
    report.append("---")
    report.append("")

    # Statistik-Vergleich
    report.append("## Statistik-Vergleich")
    report.append("")
    report.append("| Metrik | Vorher | Nachher | Differenz |")
    report.append("|--------|--------|---------|-----------|")

    for key in ['master_module', 'versionen', 'berufe', 'handlungsziele', 'kenntnisse']:
        alt = changes['statistik_alt'][key]
        neu = changes['statistik_neu'][key]
        diff = neu - alt
        diff_str = f"+{diff}" if diff > 0 else str(diff)

        key_name = key.replace('_', ' ').title()
        report.append(f"| {key_name} | {alt} | {neu} | {diff_str} |")

    report.append("")

    # Neue Module
    if changes['neue_module']:
        report.append("## Neue Module")
        report.append("")
        for modul in sorted(changes['neue_module']):
            report.append(f"- `{modul}`")
        report.append("")

    # Geänderte Module
    if changes['geaenderte_module']:
        report.append("## Geänderte Module (neues Publikationsdatum)")
        report.append("")
        report.append("| Modul | Titel | Alt | Neu |")
        report.append("|-------|-------|-----|-----|")

        for change in sorted(changes['geaenderte_module'], key=lambda x: x['modul']):
            modul = change['modul']
            titel = change['titel'][:40]
            alt = change['alt_datum'] or 'N/A'
            neu = change['neu_datum'] or 'N/A'
            report.append(f"| `{modul}` | {titel} | {alt} | {neu} |")

        report.append("")

    # Gelöschte Module
    if changes['geloeschte_module']:
        report.append("## Gelöschte Module")
        report.append("")
        for modul in sorted(changes['geloeschte_module']):
            report.append(f"- `{modul}`")
        report.append("")

    # Neue Berufe
    if changes['neue_berufe']:
        report.append("## Neue Berufe")
        report.append("")
        for beruf in changes['neue_berufe']:
            report.append(f"- {beruf}")
        report.append("")

    return "\n".join(report)

def main():
    """Hauptprogramm."""
    print("="*60)
    print("Update-Report Generator")
    print("="*60)

    # Lade aktuelle Datenbank
    print("\n[1/4] Lade aktuelle Datenbank...")
    with open(CURRENT_DB, 'r') as f:
        new_db = json.load(f)

    new_date = new_db['meta']['erstellt'][:10]
    print(f"  Erstellt: {new_date}")

    # Finde Backup
    print("\n[2/4] Suche vorherige Version...")
    backup_file = find_latest_backup()

    if not backup_file:
        print("  ⚠️ Kein Backup gefunden - erstelle Initialversion")

        # Erstelle Backup
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_file = BACKUP_DIR / f"it-module-master-{new_date}.json"
        with open(backup_file, 'w') as f:
            json.dump(new_db, f, indent=2, ensure_ascii=False)

        print(f"  ✓ Backup erstellt: {backup_file.name}")
        print("\n✅ Erste Datenbank-Version gespeichert!")
        return

    print(f"  Gefunden: {backup_file.name}")

    # Lade Backup
    with open(backup_file, 'r') as f:
        old_db = json.load(f)

    old_date = old_db['meta']['erstellt'][:10]
    print(f"  Erstellt: {old_date}")

    # Vergleiche
    print("\n[3/4] Analysiere Änderungen...")
    changes = compare_databases(old_db, new_db)

    total_changes = len(changes['neue_module']) + len(changes['geaenderte_module']) + len(changes['geloeschte_module'])
    print(f"  Änderungen: {total_changes}")

    # Erstelle Report
    print("\n[4/4] Erstelle Report...")
    report = create_report(changes, old_date, new_date)

    # Speichere Report
    report_file = REPORT_DIR / f"UPDATE-REPORT-{new_date}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)

    print(f"  ✓ Report: {report_file.name}")

    # Erstelle neues Backup
    new_backup = BACKUP_DIR / f"it-module-master-{new_date}.json"
    if not new_backup.exists():
        with open(new_backup, 'w') as f:
            json.dump(new_db, f, indent=2, ensure_ascii=False)
        print(f"  ✓ Backup: {new_backup.name}")

    # Zeige Report
    print("\n" + "="*60)
    print("UPDATE-REPORT")
    print("="*60)
    print(report)

    print("\n✅ Update-Report abgeschlossen!")

if __name__ == "__main__":
    main()
```

Speichere dieses Script als `src/create_update_report.py` und führe es aus:

```bash
python3 src/create_update_report.py
```

### Zusammenfassung der Ausgaben

Nach Ausführung aller 4 Phasen solltest du folgende Dateien haben:

1. **HTML-Daten**: `data/raw_html/*.html` (395 Dateien)
2. **Module-Index**: `data/raw_html/module_index.json`
3. **Haupt-Datenbank**: `/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank/it-module-master.json`
4. **Validierung**: `data/validation_report.txt`
5. **Update-Report**: `/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank/UPDATE-REPORT-[DATUM].md`
6. **Backup**: `/Users/sascha/Documents/git/saw_notizen-inbox/it-module-datenbank/backups/it-module-master-[DATUM].json`

### Finale Schritte

Zeige dem User eine Zusammenfassung:
- Anzahl neue Module
- Anzahl geänderte Module
- Datenqualität (%)
- Link zum Update-Report

---

## Erwartetes Ergebnis

- ✅ Aktualisierte Datenbank in `it-module-datenbank/it-module-master.json`
- ✅ Update-Report als Markdown in `it-module-datenbank/UPDATE-REPORT-[DATUM].md`
- ✅ Backup der vorherigen Version in `it-module-datenbank/backups/`
- ✅ Validierungsbericht in `data/validation_report.txt`
- ✅ Alle HTML-Dateien in `data/raw_html/`

## Wartung

Diese Action sollte regelmäßig ausgeführt werden:
- **Monatlich**: Um neue Module zu erfassen
- **Nach Ankündigungen**: Wenn neue Modulversionen veröffentlicht werden
- **Bei Bedarf**: Wenn Inkonsistenzen vermutet werden

## Troubleshooting

**Problem**: Phase 1 schlägt fehl (Network Errors)
- **Lösung**: Retry mit `python3 src/phase1_download.py`

**Problem**: Zu viele neue Module (>50)
- **Lösung**: Prüfe ob Website-Struktur geändert hat

**Problem**: Datenqualität < 70%
- **Lösung**: Prüfe HTML-Parser in `src/phase2_parse.py`
