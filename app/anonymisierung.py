"""Pseudonymisierung vor dem Modellaufruf: Platzhalter setzen und zurücksetzen.

Reiner Rechenkern, deterministisch, ohne Modell. Reihenfolge der Muster:
E-Mail, Kennzeichen, Telefon, Adresse, PLZ+Ort, Namen. Bereits gesetzte
Platzhalter werden nie erneut angefasst (Text wird an ihnen zerlegt).
Bekannte Grenzen: Namen im Fließtext ohne Anrede/Absender/Signatur bleiben.
Ein allein stehender Nachname, den sich zwei bekannte Personen teilen, bleibt
ebenfalls stehen — er lässt sich nicht zuordnen (siehe `_mehrdeutige_teile`).
Das Modul heißt aus historischen Gründen weiter `anonymisierung`.
"""
import re

PLATZHALTER_MUSTER = re.compile(r"\[(EMAIL|KENNZEICHEN|TELEFON|ADRESSE|ORT|NAME)_(\d+)\]")

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Drei Zweige, weil die Mindestzahl der Ziffern vom Trenner abhängt: mit
# Bindestrich reicht eine Ziffer ("B-A 1"), mit Leerzeichen braucht es zwei,
# sonst träfe das Muster Fahrzeugmodelle wie "BMW X5". Klein nur mit
# Bindestrich (sonst träfe "und am 21").
_KENNZEICHEN = re.compile(
    r"\b(?:[A-ZÄÖÜ]{1,3}-[A-ZÄÖÜ]{1,2}[- ]?\d{1,4}[EH]?"      # Bindestrich: eine Ziffer reicht
    r"|[A-ZÄÖÜ]{1,3} [A-ZÄÖÜ]{1,2}[- ]?\d{2,4}[EH]?"           # Leerzeichen: mindestens zwei (sonst "BMW X5")
    r"|[a-zäöü]{1,3}-[a-zäöü]{1,2}[- ]?\d{1,4}[EH]?)\b"
)
# Trennzeichen bewusst ohne \n: eine Nummer am Zeilenende darf die Folgezeile
# (PLZ+Ort, Datum) nicht mitfressen.
_TELEFON = re.compile(r"(?<![\d.])(?:\+49|0)[ \t\-/()]*\d(?:[\d \t\-/()]{4,}\d)")
# "Musterstraße 12a", "Am Alten Weg 3", "Am Bahndamm 7": Vorworte mit Großbuchstaben,
# Kern darf leer sein, damit "Weg"/"Platz" als eigenes Wort trifft
# Vorworte nur aus einer Whitelist typischer Straßenvorworte, Kern darf Bindestriche enthalten,
# Ende ohne optionales Leerzeichen (sonst wird das Folgeleerzeichen mitgefressen)
_ADRESSE = re.compile(
    r"\b(?:(?:Am|An|Im|In|Auf|Zum|Zur|Zu|Bei|Hinter|Unter|Vor|Alte[nr]?|Neue[nr]?|Obere[nr]?|"
    r"Untere[nr]?|Große[nr]?|Grosse[nr]?|Kleine[nr]?|Lange[nr]?|Hohe[nr]?|Breite[nr]?)[- ])*"
    r"[A-ZÄÖÜ]?[\wäöüß\-]*"
    r"(?:[Ss]traße|[Ss]trasse|[Ss]tr\.|[Ww]eg|[Pp]latz|[Aa]llee|[Gg]asse|[Rr]ing|[Dd]amm|[Uu]fer)"
    r"\s+\d+[a-z]?\b"
)
# Bewusst OHNE Zusatz nach dem Ortsnamen ("am Main", "ob der Tauber"): ein
# Muster dafür fraß den Folgetext, weil am/an/bei/im gewöhnliche Präpositionen
# sind. "63739 Aschaffenburg bei Herrn Mueller" wurde bis "Herrn" verschluckt,
# danach fand _ANREDE die Anrede nicht mehr und der Nachname blieb offen.
# "Frankfurt am Main" wird deshalb zu "[ORT_1] am Main" — Rest, kein Leck.
_ORT = re.compile(r"\b\d{5}\s+[A-ZÄÖÜ][a-zäöüß]+(?:[- ][A-ZÄÖÜ][a-zäöüß]+)*")
_ANREDE = re.compile(r"\b(?:Herrn?|Frau|Hr\.|Fr\.)\s+([A-ZÄÖÜ][\wäöüß\-]+(?:\s+[A-ZÄÖÜ][\wäöüß\-]+)?)")
_HALLO = re.compile(r"^\s*(?:Hallo|Hi|Servus|Moin|Guten Tag)\s+([A-ZÄÖÜ][\wäöüß\-]+)\s*[,!]?\s*$", re.MULTILINE)
_GRUSS = re.compile(
    r"^\s*(?:Viele|Liebe|Beste|Schöne|Schoene|Herzliche|Freundliche)?\s*"
    r"(?:Mit freundlichen Grüßen|Mit freundlichen Gruessen|Mit freundlichem Gruß|"
    r"Grüße|Grüsse|Gruesse|Gruß|Gruss|LG|MfG|VG|"
    r"Servus|Ciao|Danke und Gruß|Danke und Gruss|Best regards|Kind regards|Regards)"
    r"[\s,!.]*$",
    re.IGNORECASE,
)
_NAMENSZEILE = re.compile(r"^[A-ZÄÖÜ][\wäöüß\-.]*(?:\s+[A-ZÄÖÜ][\wäöüß\-.]*){0,2}$")
_KEIN_NAME = {"team", "werkstatt", "zusammen", "autohaus", "service", "gmbh", "ag", "kg", "ohg", "alle", "leute"}


def _ersetze(text: str, muster: re.Pattern, typ: str, tabelle: list, zuordnung: dict,
             fest: str | None = None) -> str:
    """Wendet `muster` nur auf Textstücke zwischen bestehenden Platzhaltern an.

    `fest`: ein bereits vergebener Platzhalter, der für jeden Treffer gesetzt
    wird (Namen: Groß-/Kleinschreibung darf keinen neuen Eintrag erzeugen).
    """
    stuecke = PLATZHALTER_MUSTER.split(text)
    # split mit Gruppen liefert [text, typ, nr, text, typ, nr, ...]
    ergebnis = []
    for i in range(0, len(stuecke), 3):
        stueck = stuecke[i]

        def _neu(m):
            if fest:
                return fest
            original = m.group(0)
            if typ == "TELEFON" and sum(c.isdigit() for c in original) < 7:
                return original
            return _platzhalter(typ, original, tabelle, zuordnung)

        ergebnis.append(muster.sub(_neu, stueck))
        if i + 2 < len(stuecke):
            ergebnis.append(f"[{stuecke[i + 1]}_{stuecke[i + 2]}]")
    return "".join(ergebnis)


def _platzhalter(typ: str, original: str, tabelle: list, zuordnung: dict) -> str:
    schluessel = (typ, original.strip())
    if schluessel not in zuordnung:
        nr = sum(1 for t in tabelle if t["typ"] == typ) + 1
        zuordnung[schluessel] = f"[{typ}_{nr}]"
        tabelle.append({"typ": typ, "platzhalter": zuordnung[schluessel], "original": original.strip()})
    return zuordnung[schluessel]


def _namenskandidaten(text: str, absender_name: str | None) -> list[str]:
    kandidaten = []
    if absender_name and absender_name.strip():
        kandidaten.append(absender_name.strip())
    kandidaten += _ANREDE.findall(text)
    kandidaten += [n for n in _HALLO.findall(text) if n.lower() not in _KEIN_NAME]
    zeilen = text.splitlines()
    for i, zeile in enumerate(zeilen):
        if _GRUSS.match(zeile):
            for folge in zeilen[i + 1:]:
                if folge.strip():
                    folge = folge.strip()
                    woerter = folge.lower().replace(",", " ").split()
                    if _NAMENSZEILE.match(folge) and not any(w in _KEIN_NAME for w in woerter) \
                            and not PLATZHALTER_MUSTER.search(folge):
                        kandidaten.append(folge)
                    break
    gesehen, eindeutig = set(), []
    for k in kandidaten:
        if k.lower() not in gesehen:
            gesehen.add(k.lower())
            eindeutig.append(k)
    return eindeutig


def _teile(name: str) -> list[str]:
    return [t for t in name.split() if len(t) >= 3 and t.lower() not in _KEIN_NAME]


def _mehrdeutige_teile(kandidaten: list[str]) -> set[str]:
    """Namensteile (klein geschrieben), die zu mehr als einem Kandidaten gehören.

    Zwei Personen mit demselben Nachnamen ("Sabine Krämer", "Peter Krämer"):
    ein allein stehendes "Krämer" lässt sich nicht zuordnen. Ein Platzhalter
    dafür wäre geraten und würde beim Zurücksetzen die falsche Person einsetzen.
    Solche Teile werden deshalb nur als Bestandteil des vollen Namens ersetzt.
    """
    herkunft: dict[str, set[str]] = {}
    for name in kandidaten:
        for teil in _teile(name):
            herkunft.setdefault(teil.lower(), set()).add(name.lower())
    return {teil for teil, quellen in herkunft.items() if len(quellen) > 1}


def _ersetze_namen(text: str, kandidaten: list[str], tabelle: list, zuordnung: dict) -> str:
    """Drei Durchgänge: erst alle Namen registrieren (längste zuerst, damit
    'Weber' aus 'Karl Weber' denselben Platzhalter bekommt), dann volle Namen
    ersetzen (Groß-/Kleinschreibung egal), dann eindeutige Namensteile (exakt).
    Mehrdeutige Teile bleiben stehen, siehe `_mehrdeutige_teile`."""
    kandidaten = sorted(kandidaten, key=len, reverse=True)
    mehrdeutig = _mehrdeutige_teile(kandidaten)
    for name in kandidaten:
        platz = _platzhalter("NAME", name, tabelle, zuordnung)
        for teil in _teile(name):
            zuordnung.setdefault(("NAME", teil), platz)
    for name in kandidaten:
        platz = zuordnung[("NAME", name)]
        text = _ersetze(text, re.compile(r"\b" + re.escape(name) + r"\b", re.IGNORECASE),
                        "NAME", tabelle, zuordnung, fest=platz)
    teile = sorted({t for n in kandidaten for t in _teile(n) if t.lower() not in mehrdeutig},
                   key=len, reverse=True)
    for teil in teile:
        text = _ersetze(text, re.compile(r"\b" + re.escape(teil) + r"\b"),
                        "NAME", tabelle, zuordnung, fest=zuordnung[("NAME", teil)])
    return text


def anonymisiere(text: str, absender_name: str | None = None) -> tuple[str, list[dict]]:
    """Liefert (pseudonymisierter Text, Platzhaltertabelle)."""
    tabelle: list[dict] = []
    zuordnung: dict = {}
    text = _ersetze(text, _EMAIL, "EMAIL", tabelle, zuordnung)
    text = _ersetze(text, _KENNZEICHEN, "KENNZEICHEN", tabelle, zuordnung)
    text = _ersetze(text, _TELEFON, "TELEFON", tabelle, zuordnung)
    text = _ersetze(text, _ADRESSE, "ADRESSE", tabelle, zuordnung)
    text = _ersetze(text, _ORT, "ORT", tabelle, zuordnung)
    text = _ersetze_namen(text, _namenskandidaten(text, absender_name), tabelle, zuordnung)
    return text, tabelle


def zuruecksetzen(obj, tabelle: list[dict]):
    """Ersetzt Platzhalter durch Originale; rekursiv über dict und list."""
    if isinstance(obj, str):
        for eintrag in tabelle:
            obj = obj.replace(eintrag["platzhalter"], eintrag["original"])
        return obj
    if isinstance(obj, dict):
        return {k: zuruecksetzen(v, tabelle) for k, v in obj.items()}
    if isinstance(obj, list):
        return [zuruecksetzen(v, tabelle) for v in obj]
    return obj
