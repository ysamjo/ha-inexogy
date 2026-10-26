# inexogy / Discovergy Smart Meter für Home Assistant

[![HACS Custom](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://hacs.xyz)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.6%2B-blue.svg)](https://www.home-assistant.io)
[![Lizenz](https://img.shields.io/badge/Lizenz-MIT-green.svg)](LICENSE)

Liest einen Stromzähler von **inexogy** (ehemals Discovergy) über die
Cloud-API des Portals und legt daraus Sensoren in Home Assistant an. Kein
Zusatzgerät, kein Modbus, kein lokaler Zugriff — nur die Zugangsdaten des
Portal-Kontos.

## Sensoren

Pro Zähler entstehen vier Entitäten. Das Gerät heißt `inexogy Zähler`, daraus
ergeben sich die Entity-IDs (Beispiel):

| Entity-ID | Bedeutung | Einheit |
|---|---|---|
| `sensor.inexogy_zahler_bezug` | aktuelle Bezugsleistung | W |
| `sensor.inexogy_zahler_einspeisung` | aktuelle Einspeiseleistung | W |
| `sensor.inexogy_zahler_zahlerstand_bezug` | Zählerstand Bezug | kWh |
| `sensor.inexogy_zahler_zahlerstand_einspeisung` | Zählerstand Einspeisung | kWh |

Die Leistungssensoren sind `measurement`, die Zählerstände `total_increasing`
und damit direkt für das Energie-Dashboard geeignet.

> Die Entity-IDs stehen nach dem ersten Einrichten fest. Wer andere Namen
> will, muss die Entitäten vor dem ersten Start umbenennen oder die
> Integrations-Einträge neu anlegen — nachträglich umbenennen ändert die ID
> nicht mehr.

## Installation

### Über HACS

1. HACS → **Integrationen** → ⋮ → **Benutzerdefinierte Repositories**
2. Repository `https://github.com/ysamjo/ha-inexogy` hinzufügen,
   Kategorie **Integration**
3. Die Integration suchen, installieren und Home Assistant neu starten
4. **Einstellungen → Geräte & Dienste → Integration hinzufügen** →
   „inexogy / Discovergy Smart Meter"

### Manuell

`custom_components/inexogy/` in den Ordner `custom_components/` der
HA-Konfiguration kopieren, Home Assistant neu starten, dann wie oben
einrichten.

## Einrichtung

Es werden nur zwei Angaben verlangt:

- **E-Mail** und **Passwort** des Kontos bei [my.inexogy.com](https://my.inexogy.com)
  (bzw. des Discovergy-Portals, falls der Zugang noch von dort stammt).

Die Zugangsdaten werden gegen die API geprüft, bevor der Eintrag entsteht.
Schlägt die Anmeldung fehl, erscheint eine passende Meldung im Dialog.

## Verhalten

- **Abfrageintervall: 30 Sekunden.** Der Zähler liefert nicht öfter neue
  Werte; häufiger zu fragen bringt nichts und belastet nur die Cloud-API.
- **Ein Zähler pro Konto.** Hat das Konto mehrere Zähler, wird der erste
  verwendet. Mehrere Zähler lassen sich derzeit nicht einrichten — dafür
  müsste die Auswahl in den Config-Flow.
- **Intervallzähler.** Manche Zähler liefern in der letzten Ablesung nur
  Nullen, weil sie nur alle 15 Minuten einen Wert schreiben. Die Integration
  fällt dann auf den letzten 3-Minuten-Wert der vergangenen zwei Stunden
  zurück, statt 0 W in die Statistik zu schreiben. Findet sie auch dort
  nichts, bleibt der Sensor auf dem letzten bekannten Wert.
- **Negative Leistung** wird als Einspeisung interpretiert: Manche Zähler
  melden die Einspeisung nicht als eigenes Feld, sondern als negativen Bezug.

## Voraussetzungen

- Home Assistant **2024.6** oder neuer
- Ein Konto bei inexogy/Discovergy mit mindestens einem Zähler
- Internetzugang des HA-Hosts (die Werte kommen aus der Cloud)

## Bekannte Einschränkungen

- Es gibt **keine lokale** Abfrage. Fällt das Portal aus, liefert die
  Integration keine neuen Werte, bis es wieder erreichbar ist.
- Der Zählerstand wird so übernommen, wie das Portal ihn liefert — eine
  Nachkommastelle mehr als im Portal ist nicht verfügbar.

## Warum eine eigene Integration

Die vorhandenen HACS-Integrationen für Discovergy sind nicht mehr brauchbar:
`schlac/hacs-integration-discovergy` ist archiviert (letzter Stand 2023),
`dachickenuser/ha-discovergy-inexogy` hat einen widersprüchlichen Domain-Namen
im Manifest, blockierende HTTP-Aufrufe und keinen Config-Flow. Diese hier ist
neu geschrieben, nutzt `pydiscovergy` und lässt sich über die Oberfläche
einrichten.

## Lizenz

MIT — siehe [LICENSE](LICENSE).
