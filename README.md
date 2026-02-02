# Briefkasten

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
[![GitHub Release](https://img.shields.io/github/release/DEIN_USERNAME/briefkasten.svg)](https://github.com/DEIN_USERNAME/briefkasten/releases)

Home Assistant Integration für smarte Briefkästen mit Klappen- und Tür-Sensor.

## Features

- **Post** (binary_sensor): Zeigt an, ob Post im Briefkasten liegt
- **Letzter Einwurf** (timestamp): Zeitpunkt der letzten Zustellung
- **Letzte Leerung** (timestamp): Zeitpunkt der letzten Entnahme
- **Einwurf Zähler** (optional): Zählt die Anzahl der Einwürfe
- **Post liegt seit** (optional): Zeigt wie lange Post im Briefkasten liegt (Stunden/Tage)
- **Entprellung** für den Klappen-Sensor (konfigurierbar)
- **Push-Benachrichtigung** bei neuer Post (optional, nur einmal pro Zustellung)
- **Reset Service**: `briefkasten.reset_counter`

## Installation

### HACS (empfohlen)

1. Öffne HACS in Home Assistant
2. Klicke auf "Integrationen"
3. Klicke auf die drei Punkte oben rechts → "Benutzerdefinierte Repositories"
4. Füge `https://github.com/DEIN_USERNAME/briefkasten` hinzu (Kategorie: Integration)
5. Suche nach "Briefkasten" und installiere es
6. Starte Home Assistant neu

### Manuell

Kopiere den `custom_components/briefkasten/` Ordner in dein Home Assistant `config/custom_components/` Verzeichnis und starte Home Assistant neu.

## Konfiguration

1. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**
2. Suche nach "Briefkasten"
3. Wähle deine Klappen- und Tür-Sensoren aus
4. Optional: Klicke auf **Konfigurieren** um weitere Optionen anzupassen

## Voraussetzungen

Du benötigst zwei Binary Sensoren:
- **Klappen-Sensor**: Erkennt das Öffnen der Einwurfklappe (Posteingang)
- **Tür-Sensor**: Erkennt das Öffnen der Entnahme-Tür (Leerung)
