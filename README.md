# SENEC Connect

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

Home Assistant Custom Integration für SENEC Batteriespeichersysteme über die SENEC.Connect API.

## Funktionen

- Batterie-Überwachung (Ladezustand, Leistung, Spannung, Strom)
- Netz-Monitoring (Netzbezug/-einspeisung, Hausverbrauch, PV-Produktion)
- BESS-Typenschild-Daten (Hersteller, Modell, Kapazität, Ladeleistungsgrenzen)
- Wallbox-Status (EV-Verbindung, Ladestatus, Ladeleistung)
- Unterstützung für mehrere SENEC-Geräte pro Installation
- Konfigurierbares Polling-Intervall (mindestens 60 Sekunden)

## Installation

### HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Klicke auf die drei Punkte oben rechts und wähle **Benutzerdefinierte Repositories**
3. Füge die Repository-URL hinzu und wähle als Kategorie **Integration**
4. Klicke auf **Hinzufügen**
5. Suche nach "SENEC Connect" in HACS und klicke auf **Herunterladen**
6. Starte Home Assistant neu
7. Gehe zu **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
8. Suche nach "SENEC Connect" und folge dem Einrichtungsassistenten

### Manuelle Installation

1. Lade die neueste Version aus dem [Releases](../../releases)-Bereich herunter
2. Kopiere den Ordner `custom_components/senec_connect/` in dein Home Assistant `config/custom_components/`-Verzeichnis
3. Starte Home Assistant neu
4. Gehe zu **Einstellungen** → **Geräte & Dienste** → **Integration hinzufügen**
5. Suche nach "SENEC Connect" und folge dem Einrichtungsassistenten

## Konfiguration

Die Integration wird vollständig über die Home Assistant UI konfiguriert:

1. **API Key** — Dein SENEC.Connect API Subscription Key
2. **Polling-Intervall** — Aktualisierungsintervall in Sekunden (Standard: 60, Minimum: 60)
3. **Geräteauswahl** — Wähle die SENEC-Geräte aus, die überwacht werden sollen

## Voraussetzungen

- Home Assistant 2024.1.0 oder neuer
- Ein gültiger SENEC.Connect API Key (Ocp-Apim-Subscription-Key)

## Versionierung

Dieses Projekt verwendet [Semantic Versioning](https://semver.org/). HACS erkennt neue Versionen automatisch über Git-Tags und zeigt Update-Benachrichtigungen an.

## Lizenz

MIT
