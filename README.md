# Werkstatt-Terminassistent

## 1. Was das ist

Ein Assistent, der eingehende Werkstatt-Mails eines Autohauses liest, die
relevanten Angaben strukturiert herauszieht und einen Terminvorschlag samt
Antwortentwurf erzeugt. Eigenprojekt, Demo mit erfundenen Testdaten,
entstanden für eine Bewerbung.

## 2. Demo im Browser ohne Installation

`https://dangtu1190-tech.github.io/werkstatt-terminassistent/`

Das ist der statische Modus: vorberechnete Ergebnisse aus `docs/data/`,
keine Modellaufrufe. Alle 15 Testmails lassen sich anklicken und zeigen den
kompletten Ablauf inklusive Pseudonymisierung, Extraktion und Terminvorschlag,
so wie sie beim letzten Echtlauf entstanden sind. Für eine neue Mail
„live" gegen ein Modell rechnen zu lassen, geht nur lokal (Abschnitt 5).

## 3. Das Kernstück: Pseudonymisierung vor dem Modellaufruf

Bevor eine Mail an das Modell geht, ersetzt eine deterministische
Regex-Erkennung personenbezogene Angaben durch Platzhalter. Das Modell sieht
nie den Original-Text. Es ist bewusst Pseudonymisierung und keine
Anonymisierung: die Zuordnungstabelle bleibt lokal und macht den Schritt
umkehrbar, an das Modell gehen ausschließlich die Platzhalter. (Das Modul
heißt aus der Entstehungsgeschichte heraus weiterhin `anonymisierung.py`.)

| Typ | Beispiel | Platzhalter |
|---|---|---|
| E-Mail | `p.kraemer@example.net` | `[EMAIL_1]` |
| Kennzeichen | `AB-PK 404` | `[KENNZEICHEN_1]` |
| Telefon | `0160 98 76 54 32` | `[TELEFON_1]` |
| Adresse | `Rosenweg 3` | `[ADRESSE_1]` |
| Ort | `63571 Gelnhausen` | `[ORT_1]` |
| Name | `Sabine Krämer` | `[NAME_1]` |

Dieselbe Angabe bekommt immer denselben Platzhalter, auch bei
unterschiedlicher Schreibweise (Groß-/Kleinschreibung, Namensteile). Die
Antwort des Modells enthält deshalb dieselben Platzhalter; erst danach
werden sie anhand der Zuordnungstabelle wieder auf die Originalwerte
zurückgesetzt, rekursiv über das ganze JSON-Ergebnis.

Ehrliche Grenzen: Namen, die im Fließtext ohne Anrede, Absenderfeld oder
Signatur auftauchen, werden nicht erkannt. Signaturen, die durchgehend klein
geschrieben sind, ebenfalls nicht — die Namenszeile wird über den
Großbuchstaben am Wortanfang gefunden. Teilen sich zwei erkannte Personen
einen Nachnamen, bleibt ein allein stehender Nachname stehen; er ist nicht
zuordenbar, und ein geratener Platzhalter setzte die falsche Person wieder
ein. Umgekehrt gilt: ist nur eine Person mit diesem Nachnamen bekannt, wird
auch der allein stehende Nachname ersetzt und beim Zurücksetzen zum vollen
Namen aufgefüllt — aus „Elektro Wittmann GmbH" wird so „Elektro Andrea
Wittmann GmbH". Orte ohne vorangestellte PLZ bleiben stehen, und Ortsnamen
mit Zusatz wie „am Main" bleiben teilweise sichtbar: maskiert wird
„60313 Frankfurt", das „am Main" bleibt stehen. Ein Muster, das den Zusatz
mitnimmt, verschluckt sonst gewöhnlichen Fließtext („bei Herrn Mueller") und
verdeckt damit eine Anrede, hinter der ein Name steht. Straßen mit
unüblichen Vorworten fallen durch das Muster. Zeichenfolgen, die wie ein
Kennzeichen aussehen (z. B. „Raum A-B 4"), werden ebenfalls maskiert; diese
Über-Maskierung ist gewollt, weil ein übersehenes Kennzeichen schwerer wiegt
als ein maskierter Raumname. Fahrzeugmodelle bleiben absichtlich sichtbar —
ohne sie ist keine sinnvolle Terminplanung möglich, und sie sind für sich
genommen nicht personenbezogen.

## 4. Pipeline

```
Mail
  │
  ▼
1. Pseudonymisierung – personenbezogene Angaben durch Platzhalter ersetzen
  │
  ▼
2. Extraktion        – Modellaufruf liefert strukturiertes JSON (Kunde,
  │                     Fahrzeug, Anliegen, Dringlichkeit, Wunschzeitraum)
  ▼
3. Terminsuche        – freien Halbtag im Kapazitätskalender finden
  │
  ▼
4. Antwortentwurf     – deutscher Text aus einer festen Vorlage, nicht vom
                         Modell
```

Das Modell liefert ausschließlich das JSON aus Schritt 2; der Antworttext
in Schritt 4 kommt aus einer Vorlage im Code, damit er vorhersagbar bleibt.

## 5. Lokal starten

```
copy .env.example .env
```

In der `.env` den Schlüssel eintragen (`LLM_API_KEY`), dann:

- Windows: `run.bat`
- Linux/Mac: `sh run.sh`

Danach im Browser `http://localhost:8040` öffnen. Ohne `.env` starten die
Skripte den Server trotzdem, mit einem Hinweis: die 15 vorberechneten
Ergebnisse aus `data/` lassen sich ansehen, ein neuer Modellaufruf scheitert
am fehlenden Schlüssel und endet sichtbar als `pruefung_noetig`.

Alle Testmails auf einmal verarbeiten (ohne Server):

```
python -m app.cli --neu
```

## 6. Modellzugriff

Der Client ist OpenAI-kompatibel und über vier Umgebungsvariablen
konfiguriert:

| Variable | Langdock (verwendet) | Ollama (lokal) |
|---|---|---|
| `LLM_PROVIDER` | `langdock` | `ollama` |
| `LLM_BASE_URL` | `https://api.langdock.com/openai/eu/v1` | `http://localhost:11434/v1` |
| `LLM_MODEL` | `gpt-5.1` | z. B. `qwen2.5:7b` |
| `LLM_API_KEY` | Langdock-Schlüssel | beliebiger Wert |

Alle ausgelieferten Ergebnisse in `data/ergebnisse.json` und `docs/data/`
stammen aus echten Läufen gegen Langdock mit `gpt-5.1`, im Schnitt rund
3,5 Sekunden pro Mail. Der Ollama-Pfad ist gebaut, aber von mir noch nicht
gegen eine laufende Ollama-Instanz geprüft.

## 7. Testdaten

15 erfundene Mails in `data/mails.json`, die typische Störfälle abdecken:
Dialekt (m03), Anfrage ohne Kennzeichen (m04, Winterreifen), drei Anliegen
in einer Mail (m05, Crafter mit Ölwechsel/HU/Klima), Verkaufsanfrage statt
Werkstatt (m06, Probefahrt), sicherheitsrelevanter Fall (m13,
Motorwarnleuchte rot), ausgebuchter Wunschzeitraum (m07,
Mittwoch/Donnerstag), englische Mail (m10), sehr kurze Mail (m08) und
Firmensignatur mit Adresse (m09, Elektro Wittmann GmbH).

## 8. Tests

```
python -m pytest -q
```

61 Tests laufen ohne Netzzugriff und ohne Schlüssel (Fake-Client). Ein
Test, der wirklich gegen ein Modell fragt, wird nur ausgeführt, wenn
`LLM_API_KEY` gesetzt ist — sonst übersprungen (skip), nie fehlgeschlagen.

## 9. GitHub Pages einschalten

Repository-Einstellungen → **Settings → Pages** → Source
„Deploy from a branch", Branch `main`, Ordner `/docs`. Nach jedem

```
python -m app.cli --pages
```

die aktualisierten Dateien unter `docs/data/` committen, damit der
statische Modus (Abschnitt 2) den aktuellen Stand zeigt.

## 10. Bewusst nicht enthalten

Mailanbindung (Posteingang, IMAP/Graph), Login/Benutzerverwaltung,
Deployment-Automatisierung, eine echte Datenbank. Die Demo arbeitet mit
JSON-Dateien und manuell eingespielten Testmails.

## 11. Wie ich das im Autohaus umsetzen würde

Klar als Ausblick markiert, keine bestehende Implementierung:

**DMS-Anbindung** — Kunden- und Fahrzeugdaten direkt aus dem
Dealer-Management-System ziehen, Kennzeichen als Schlüssel, statt Angaben
aus der Mail zu erraten.

**Freigabeworkflow** — der Entwurf entsteht in der gewohnten Oberfläche des
Teams, ein Klick sendet die Antwort, ein Protokoll hält fest, wer wann
freigegeben hat.

**Auslastungssteuerung** — Kapazität je Arbeitsplatz und Qualifikation statt
eines einzelnen Kalenders, damit ein Reifenwechsel nicht denselben Slot wie
eine Motorreparatur belegt.

**Sicherheitsrelevante Mängel vorziehen** — bleibt Grundprinzip: Anliegen
mit Sicherheitsbezug bekommen Vorrang vor der Wunschzeit des Kunden.
