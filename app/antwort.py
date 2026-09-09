"""Antwortentwurf aus einer deutschen Vorlage. Kein Modell: der Text bleibt vorhersagbar."""
from datetime import date

WOCHENTAGE = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
KATEGORIE_TEXT = {
    "wartung": "Wartung", "reparatur": "Reparatur", "reifen": "Reifen", "hu_au": "HU/AU",
    "karosserie": "Karosserie", "verkauf": "Verkauf", "sonstiges": "Sonstiges",
}


def _anrede(kunde: dict) -> str:
    name = (kunde or {}).get("name")
    anrede = (kunde or {}).get("anrede")
    if not name:
        return "Guten Tag,"
    nachname = name.split()[-1]
    if anrede == "Frau":
        return f"Sehr geehrte Frau {nachname},"
    if anrede == "Herr":
        return f"Sehr geehrter Herr {nachname},"
    return f"Guten Tag {name},"


def _datum_text(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{WOCHENTAGE[d.weekday()]}, {d.strftime('%d.%m.%Y')}"


def _fahrzeug_text(ex: dict) -> str:
    f = ex.get("fahrzeug") or {}
    teile = [f.get("marke"), f.get("modell")]
    text = " ".join(t for t in teile if t)
    if ex.get("kennzeichen"):
        text = f"{text} ({ex['kennzeichen']})" if text else ex["kennzeichen"]
    return text or "Ihr Fahrzeug"


def baue_antwort(ex: dict, termin: dict | None, betreff: str) -> str:
    zeilen = [_anrede(ex.get("kunde")), "", "vielen Dank für Ihre Anfrage."]
    if ex.get("zustaendigkeit") == "verkauf":
        zeilen += ["", "Ihr Anliegen betrifft unseren Verkauf. Ich habe Ihre Nachricht an die "
                   "Kolleginnen und Kollegen dort weitergeleitet; sie melden sich in Kürze bei Ihnen."]
    else:
        anliegen = ex.get("anliegen") or []
        if anliegen:
            zeilen += ["", f"Für {_fahrzeug_text(ex)} haben wir folgende Punkte notiert:"]
            zeilen += [f"- {KATEGORIE_TEXT.get(a['kategorie'], a['kategorie'])}: {a['beschreibung']}" for a in anliegen]
        if termin:
            halbtag = "Vormittag" if termin["halbtag"] == "vormittag" else "Nachmittag"
            zeilen += ["", f"Wir schlagen Ihnen einen Termin am {_datum_text(termin['datum'])} am {halbtag} vor."]
            if termin.get("hinweis"):
                zeilen.append(termin["hinweis"])
            zeilen.append("Bitte bestätigen Sie den Termin kurz per Antwort auf diese E-Mail.")
        else:
            zeilen += ["", "Wir melden uns mit einem Terminvorschlag, sobald die offenen Punkte geklärt sind."]
    unklar = ex.get("unklarheiten") or []
    if unklar:
        zeilen += ["", "Damit wir den Termin passend planen können, benötigen wir noch:"]
        zeilen += [f"- {u}" for u in unklar]
    zeilen += ["", "Mit freundlichen Grüßen", "Ihr Serviceteam"]
    return "\n".join(zeilen)
