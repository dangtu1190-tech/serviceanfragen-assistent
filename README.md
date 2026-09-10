# Serviceanfragen-Assistent

## 1. Was das ist

Ein Assistent, der eingehende Servicemails eines Sonderanlagenbauers (Vakuumöfen
für Metallurgie und Wärmebehandlung) liest, die relevanten Angaben strukturiert
herauszieht und den Einsatz eines Servicetechnikers vorschlägt, samt
Antwortentwurf zur Freigabe. Abgedeckt sind Wartung, Störung, Ersatzteil,
Reklamation und Angebot. Eigenprojekt, Demo mit erfundenen Testdaten,
entstanden für Bewerbungen.

## 2. Demo im Browser ohne Installation

`https://dangtu1190-tech.github.io/serviceanfragen-assistent/`

Das ist der statische Modus: vorberechnete Ergebnisse aus `docs/data/`,
keine Modellaufrufe. Alle 15 Testmails lassen sich anklicken und zeigen den
kompletten Ablauf inklusive Pseudonymisierung, Extraktion und
Einsatzvorschlag, so wie sie beim letzten Echtlauf entstanden sind. Für eine
neue Mail „live" gegen ein Modell rechnen zu lassen, geht nur lokal
(Abschnitt 5).

## 3. Das Kernstück: Pseudonymisierung vor dem Modellaufruf

Bevor eine Mail an das Modell geht, ersetzt eine deterministische
Regex-Erkennung personenbezogene Angaben durch Platzhalter. Das Modell sieht
nie den Original-Text. Es ist bewusst Pseudonymisierung und keine
Anonymisierung: die Zuordnungstabelle bleibt lokal und macht den Schritt
umkehrbar, an das Modell gehen ausschließlich die Platzhalter. (Das Modul
heißt aus der Entstehungsgeschichte heraus weiterhin `anonymisierung.py`.)

| Typ | Beispiel | Platzhalter |
|---|---|---|
| E-Mail | `f.lindemann@hartmann-wb.example` | `[EMAIL_1]` |
| Firma | `Hartmann Wärmebehandlung GmbH` | `[FIRMA_1]` |
| Telefon | `06661 / 90 12 34` | `[TELEFON_1]` |
| Adresse | `Am Gewerbepark 12` | `[ADRESSE_1]` |
| Ort | `36381 Schlüchtern` | `[ORT_1]` |
| Name | `Frank Lindemann` | `[NAME_1]` |

Dieselbe Angabe bekommt immer denselben Platzhalter, auch bei
unterschiedlicher Schreibweise (Groß-/Kleinschreibung, Namensteile). Die
Antwort des Modells enthält deshalb dieselben Platzhalter. Erst danach
werden sie anhand der Zuordnungstabelle wieder auf die Originalwerte
zurückgesetzt, rekursiv über das ganze JSON-Ergebnis.

### Warum diese Felder und keine anderen

Anlagen- und Seriennummern, Fehlercodes und Anlagentypen werden bewusst nicht
ersetzt. Sie sind keine personenbezogenen Daten, und das Modell braucht sie
wörtlich, um die Anfrage der richtigen Anlage zuzuordnen. Firmennamen werden
dagegen ersetzt, aber nicht aus Datenschutzgründen: sie berühren
Geschäftsgeheimnisse, denn wer welche Anlage betreibt und welche Störungen
sie hat, ist selbst schützenswert. Die Auswahl der zu ersetzenden Felder ist
damit eine Entscheidung je Anwendungsfall, keine Pauschalregel, die sich
unbesehen auf andere Domänen übertragen ließe.

Ehrliche Grenzen: Namen, die im Fließtext ohne Anrede, Absenderfeld oder
Signatur auftauchen, werden nicht erkannt. Signaturen, die durchgehend klein
geschrieben sind, ebenfalls nicht — die Namenszeile wird über den
Großbuchstaben am Wortanfang gefunden. Teilen sich zwei erkannte Personen
einen Nachnamen, bleibt ein allein stehender Nachname stehen. Er ist nicht
zuordenbar, und ein geratener Platzhalter setzte die falsche Person wieder
ein. Umgekehrt gilt: ist nur eine Person mit diesem Nachnamen bekannt, wird
auch der allein stehende Nachname ersetzt und beim Zurücksetzen zum vollen
Namen aufgefüllt. Orte ohne vorangestellte PLZ bleiben stehen, und
Ortsnamen mit Zusatz wie „am Main" bleiben teilweise sichtbar: maskiert wird
„60437 Frankfurt", das „am Main" bleibt stehen. Ein Muster, das den Zusatz
mitnimmt, verschluckt sonst gewöhnlichen Fließtext und verdeckt damit eine
Anrede, hinter der ein Name steht. Firmennamen ohne Rechtsform im Namen
(also ohne GmbH, AG, KG und ähnliche Endungen) werden nur erkannt, wenn sie
als Absenderfirma aus den Mail-Metadaten bekannt sind. Taucht ein solcher
Name nur im Fließtext auf, etwa in einer Weiterleitung, bleibt er stehen.

## 4. Pipeline, Technikerkalender, Ersatzteilhinweise

```
Mail
  │
  ▼
1. Pseudonymisierung – personenbezogene Angaben durch Platzhalter ersetzen
  │
  ▼
2. Extraktion        – Modellaufruf liefert strukturiertes JSON (Kunde,
  │                     Ansprechpartner, Anlage, Anliegen, Dringlichkeit,
  │                     Wunschzeitraum, Zuständigkeit)
  ▼
3. Terminsuche        – freien Servicetechniker mit passender Qualifikation
  │                     im Kapazitätskalender finden
  ▼
4. Antwortentwurf     – deutscher Text aus einer festen Vorlage, nicht vom
                         Modell
```

Das Modell liefert ausschließlich das JSON aus Schritt 2. Der Antworttext
in Schritt 4 kommt aus einer Vorlage im Code, damit er vorhersagbar bleibt.

Der Technikerkalender kennt fünf Servicetechniker mit je ein bis zwei
Qualifikationen (Elektrik, Vakuumtechnik, Steuerung, Mechanik). Die
benötigte Qualifikation wird aus Kategorie und Beschreibung der Anliegen
abgeleitet, zum Beispiel führt ein genannter Fehlercode oder ein Hinweis
auf die Steuerung zur Qualifikation Steuerung. Bei Dringlichkeit
„Stillstand" (Produktion steht oder eine Charge sitzt im Ofen fest) wird
der Einsatz vorgezogen: gesucht wird der erste freie Tag ab heute statt im
Wunschzeitraum, mit dem Hinweis „Produktionsstillstand, Einsatz
vorgezogen." Geht es um eine Neuanlage, einen Kauf oder ein Angebot für
eine neue Anlage, ist die Zuständigkeit Vertrieb, und es wird kein Termin
gesucht. Reine Ersatzteilanliegen ohne weiteren Servicebedarf bekommen
ebenfalls keinen Termin. Der Vorschlag reserviert nichts, erst die Freigabe
belegt den Techniker. Ablehnen oder erneutes Verarbeiten geben ihn wieder
frei.

Für Anliegen der Kategorie Ersatzteil liefert ein kleiner Katalog
Verfügbarkeitshinweise (etwa „ab Lager" oder „Lieferzeit ca. 3 Wochen"),
die im Antwortentwurf mit aufgeführt werden. Ohne Treffer im Katalog steht
dort „Verfügbarkeit wird geprüft".

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

Den statischen Modus selbst ansehen (ohne Server), zum Beispiel um
`docs/index.html` unverändert von der Festplatte zu prüfen:

```
python -m http.server 8041 -d docs
```

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
stammen aus echten Läufen gegen Langdock mit `gpt-5.1`. Der Ollama-Pfad ist
gebaut, aber von mir noch nicht gegen eine laufende Ollama-Instanz geprüft.

## 7. Testdaten

15 erfundene Mails in `data/mails.json`, geschrieben von Instandhaltern,
Werksleitern und Einkäufern erfundener Industriefirmen, die typische
Störfälle abdecken:

- Anfrage ohne Anlagennummer (m01, „der Ofen in Halle 3")
- Produktionsstillstand mit Fehlercode am Bedienfeld (m02)
- alte Anlage mit einer Nummer außerhalb des üblichen Schemas (m03)
- drei Anliegen in einer Mail: Ersatzteil, Wartungstermin, Angebot (m04)
- Vertriebsfall, Anfrage für eine neue Anlage (m05)
- Weiterleitung mit drei Zitatebenen (m06)
- englische Mail (m07)
- vager Fall ohne klare Diagnose („riecht komisch, Charge nicht
  durchgehärtet", m08)
- Anhang-Bezug ohne tatsächlichen Anhang (m09)
- sehr knappe Mail ohne Anrede und Signatur (m10)
- Reklamation nach einem vorangegangenen Serviceeinsatz (m11)
- zwei Anlagen in einem Wartungswunsch, an einem Tag (m12)
- weiterer Stillstandsfall (m13)
- Anfrage außerhalb des Kerngeschäfts, Anlagenumzug (m14)
- Ersatzteil- und Wartungsfrage kombiniert (m15)

Vier Mails sind dringlich (Produktionsstillstand), erkennbar nur aus dem
Text, nicht aus Betreff oder Metadaten.

## 8. Tests

```
python -m pytest -q
```

68 Tests laufen ohne Netzzugriff und ohne Schlüssel (Fake-Client). Ein
Test, der wirklich gegen ein Modell fragt, wird nur ausgeführt, wenn
`LLM_API_KEY` gesetzt ist — sonst übersprungen (skip), nie fehlgeschlagen.

Ergebnisse regenerieren sich mit:

```
python -m app.cli --neu --pages
```

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

## 11. Wie ich das in einem Betrieb umsetzen würde

Das Folgende existiert nicht, es ist mein Vorschlag für den nächsten Schritt. Dasselbe Muster passt auf Serviceanfragen, Ersatzteilanfragen und Reklamationen, unabhängig von der Branche. Kunden-, Fahrzeug- oder Anlagendaten kämen aus dem führenden System statt aus der Mail (im Autohaus das Dealer-Management-System, im Anlagenbau das ERP), Kennzeichen oder Auftragsnummer wären der Schlüssel für den Abgleich. Der Sachbearbeiter sähe den Entwurf in seiner gewohnten Oberfläche, bestätigt und sendet, jede Antwort wird mit Absender und Zeitpunkt protokolliert. Dringlichkeit, Kapazität je Arbeitsplatz und Ersatzteilverfügbarkeit könnten die Priorisierung steuern.
