#!/usr/bin/env python3
"""
Phase 3: Validierung der extrahierten Daten
Prüft Vollständigkeit und Qualität der Daten
"""

import json
from pathlib import Path
from collections import defaultdict


# Konfiguration
JSON_FILE = Path("/Users/sascha/Documents/git/saw_notizen-inbox/it-module-master.json")
VALIDATION_REPORT = Path("/Users/sascha/Documents/git/saw_tool_webscraper/data/validation_report.txt")


def load_json():
    """Lade JSON-Datei."""
    with open(JSON_FILE, 'r') as f:
        return json.load(f)


def validate_data(data):
    """Validiere Daten und erstelle Bericht."""
    report = []
    report.append("="*60)
    report.append("VALIDIERUNGSBERICHT")
    report.append("="*60)
    report.append("")

    # 1. META-DATEN
    report.append("1. META-DATEN:")
    report.append("-" * 40)
    meta = data['meta']
    for key, value in meta.items():
        report.append(f"  {key}: {value}")
    report.append("")

    # 2. BERUFE-ANALYSE
    report.append("2. BERUFE:")
    report.append("-" * 40)
    berufe = data['berufe']
    report.append(f"  Anzahl Berufe: {len(berufe)}")
    report.append("")
    report.append("  Liste der Berufe:")
    for beruf in berufe:
        report.append(f"    {beruf['id']}. {beruf['name']}")
    report.append("")

    # 3. MODULE-ANALYSE
    report.append("3. MODULE-ANALYSE:")
    report.append("-" * 40)

    modules_ohne_berufe = []
    modules_ohne_handlungsziele = []
    modules_ohne_kenntnisse = []
    modules_ohne_publikationsdatum = []

    handlungsziele_stats = defaultdict(int)
    kenntnisse_stats = defaultdict(int)

    for master in data['module']:
        for version in master['versionen']:
            modul_key = f"{master['nummer']}-V{version['version']}"

            # Berufe
            if not version.get('berufe_ids') or len(version['berufe_ids']) == 0:
                modules_ohne_berufe.append(modul_key)

            # Publikationsdatum
            if not version.get('publikationsdatum'):
                modules_ohne_publikationsdatum.append(modul_key)

            # Handlungsziele
            handlungsziele = version.get('handlungsziele', [])
            if not handlungsziele:
                modules_ohne_handlungsziele.append(modul_key)
            else:
                handlungsziele_stats[len(handlungsziele)] += 1

                # Kenntnisse
                hat_kenntnisse = False
                for hz in handlungsziele:
                    kenntnisse = hz.get('handlungsnotwendige_kenntnisse', [])
                    if kenntnisse:
                        hat_kenntnisse = True
                        kenntnisse_stats[len(kenntnisse)] += 1

                if not hat_kenntnisse:
                    modules_ohne_kenntnisse.append(modul_key)

    # Ausgabe
    report.append(f"  Module ohne Berufe: {len(modules_ohne_berufe)}")
    if modules_ohne_berufe:
        report.append(f"    Beispiele: {', '.join(modules_ohne_berufe[:10])}")

    report.append(f"  Module ohne Handlungsziele: {len(modules_ohne_handlungsziele)}")
    if modules_ohne_handlungsziele:
        report.append(f"    Beispiele: {', '.join(modules_ohne_handlungsziele[:10])}")

    report.append(f"  Module ohne Kenntnisse: {len(modules_ohne_kenntnisse)}")
    if modules_ohne_kenntnisse:
        report.append(f"    Beispiele: {', '.join(modules_ohne_kenntnisse[:10])}")

    report.append(f"  Module ohne Publikationsdatum: {len(modules_ohne_publikationsdatum)}")
    if modules_ohne_publikationsdatum:
        report.append(f"    Beispiele: {', '.join(modules_ohne_publikationsdatum[:10])}")

    report.append("")

    # 4. HANDLUNGSZIELE-VERTEILUNG
    report.append("4. HANDLUNGSZIELE-VERTEILUNG:")
    report.append("-" * 40)
    report.append("  Anzahl HZ | Anzahl Module")
    for count in sorted(handlungsziele_stats.keys()):
        report.append(f"  {count:9d} | {handlungsziele_stats[count]:13d}")
    report.append("")

    # 5. KENNTNISSE-VERTEILUNG
    report.append("5. KENNTNISSE-VERTEILUNG (pro Handlungsziel):")
    report.append("-" * 40)
    report.append("  Anzahl Kenntnisse | Anzahl Handlungsziele")
    for count in sorted(kenntnisse_stats.keys()):
        report.append(f"  {count:17d} | {kenntnisse_stats[count]:21d}")
    report.append("")

    # 6. BEISPIEL-MODULE
    report.append("6. BEISPIEL-MODULE (mit vollständigen Daten):")
    report.append("-" * 40)

    # Finde 3 Module mit vollständigen Daten
    vollstaendige_module = []
    for master in data['module']:
        for version in master['versionen']:
            if (version.get('berufe_ids') and
                version.get('handlungsziele') and
                version.get('publikationsdatum')):

                # Prüfe ob mindestens ein Handlungsziel Kenntnisse hat
                hat_kenntnisse = any(
                    hz.get('handlungsnotwendige_kenntnisse')
                    for hz in version['handlungsziele']
                )

                if hat_kenntnisse:
                    vollstaendige_module.append({
                        'master': master,
                        'version': version
                    })

                if len(vollstaendige_module) >= 3:
                    break
        if len(vollstaendige_module) >= 3:
            break

    for i, item in enumerate(vollstaendige_module, 1):
        master = item['master']
        version = item['version']
        report.append(f"\n  Beispiel {i}: Modul {master['nummer']} V{version['version']}")
        report.append(f"    Titel: {master['titel_master'][:60]}")
        report.append(f"    Publikationsdatum: {version.get('publikationsdatum')}")
        report.append(f"    Berufe: {len(version.get('berufe_ids', []))}")
        report.append(f"    Handlungsziele: {len(version.get('handlungsziele', []))}")

        total_kenntnisse = sum(
            len(hz.get('handlungsnotwendige_kenntnisse', []))
            for hz in version.get('handlungsziele', [])
        )
        report.append(f"    Kenntnisse gesamt: {total_kenntnisse}")

    report.append("")

    # 7. QUALITÄTSBEWERTUNG
    report.append("7. QUALITÄTSBEWERTUNG:")
    report.append("-" * 40)

    total_versionen = meta['anzahl_versionen_total']
    complete_versionen = total_versionen - len(modules_ohne_berufe) - len(modules_ohne_handlungsziele) - len(modules_ohne_kenntnisse)
    completeness = (complete_versionen / total_versionen) * 100 if total_versionen > 0 else 0

    report.append(f"  Vollständigkeit: {completeness:.1f}%")
    report.append(f"    ({complete_versionen} von {total_versionen} Module mit allen Daten)")
    report.append("")

    if len(modules_ohne_berufe) > 0:
        report.append(f"  ⚠️  {len(modules_ohne_berufe)} Module ohne Berufe")
    if len(modules_ohne_handlungsziele) > 0:
        report.append(f"  ⚠️  {len(modules_ohne_handlungsziele)} Module ohne Handlungsziele")
    if len(modules_ohne_kenntnisse) > 0:
        report.append(f"  ⚠️  {len(modules_ohne_kenntnisse)} Module ohne Kenntnisse")

    if completeness >= 90:
        report.append("\n  ✅ SEHR GUT - Datenqualität über 90%")
    elif completeness >= 70:
        report.append("\n  ✓ GUT - Datenqualität über 70%")
    else:
        report.append("\n  ⚠️  VERBESSERUNGSWÜRDIG - Datenqualität unter 70%")

    report.append("")
    report.append("="*60)

    return "\n".join(report)


def main():
    """Hauptprogramm - Phase 3: Validierung."""
    print("="*60)
    print("Phase 3: Daten-Validierung")
    print("="*60)

    print("\n[1/2] Lade JSON-Datei...")
    data = load_json()
    print(f"  {data['meta']['anzahl_versionen_total']} Versionen geladen")

    print("\n[2/2] Validiere Daten...")
    report = validate_data(data)

    # Speichere Bericht
    VALIDATION_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with open(VALIDATION_REPORT, 'w', encoding='utf-8') as f:
        f.write(report)

    # Zeige Bericht
    print("\n" + report)

    print(f"\n✅ Validierung abgeschlossen!")
    print(f"   Bericht: {VALIDATION_REPORT}")


if __name__ == "__main__":
    main()
