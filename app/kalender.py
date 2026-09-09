"""Kapazitätskalender: Werktage mit zwei Halbtagen, freien Halbtag finden, belegen.

Regeln (Spec): Verkauf -> kein Termin. Sicherheitsrelevant -> nächster freier
Halbtag ab heute, Hinweis "vorgezogen". Sonst erster freier Halbtag im
Wunschzeitraum passend zur Tageszeit; nichts frei -> erster freier Halbtag
nach dem Zeitraum mit Hinweis. Ohne Wunsch: ab heute + 1 Werktag.
Der Vorschlag reserviert nichts; erst `belege()` erhöht `belegt`.
"""
import json
from datetime import date, timedelta
from pathlib import Path

HALBTAGE = ("vormittag", "nachmittag")
KAPAZITAET = 4


def erzeuge_kalender(basisdatum: date, wochen: int = 3) -> dict:
    tage = []
    tag = basisdatum
    while tag < basisdatum + timedelta(weeks=wochen):
        if tag.weekday() < 5:
            tage.append({"datum": tag.isoformat(),
                         "halbtage": {h: {"kapazitaet": KAPAZITAET, "belegt": 0} for h in HALBTAGE}})
        tag += timedelta(days=1)
    return {"basisdatum": basisdatum.isoformat(), "tage": tage}


def lade_kalender(pfad) -> dict:
    return json.loads(Path(pfad).read_text(encoding="utf-8"))


def speichere_kalender(kalender: dict, pfad) -> None:
    Path(pfad).write_text(json.dumps(kalender, ensure_ascii=False, indent=2), encoding="utf-8")


def _frei(tag: dict, halbtag: str) -> bool:
    h = tag["halbtage"][halbtag]
    return h["belegt"] < h["kapazitaet"]


def _erster_freier(kalender: dict, von: date, bis: date | None, tageszeit: str) -> tuple[str, str] | None:
    halbtage = HALBTAGE if tageszeit not in HALBTAGE else (tageszeit,)
    for tag in kalender["tage"]:
        d = date.fromisoformat(tag["datum"])
        if d < von or (bis and d > bis):
            continue
        for h in halbtage:
            if _frei(tag, h):
                return tag["datum"], h
    return None


def _datum(wert) -> date | None:
    try:
        return date.fromisoformat(wert) if wert else None
    except ValueError:
        return None


def finde_termin(kalender: dict, extraktion: dict, heute: date) -> dict | None:
    if extraktion.get("zustaendigkeit") == "verkauf":
        return None
    wunsch = extraktion.get("wunschzeitraum") or {}
    tageszeit = wunsch.get("tageszeit") or "egal"

    if extraktion.get("dringlichkeit") == "sicherheitsrelevant":
        treffer = _erster_freier(kalender, heute, None, "egal")
        return {"datum": treffer[0], "halbtag": treffer[1],
                "hinweis": "Sicherheitsrelevant, Termin vorgezogen."} if treffer else None

    von, bis = _datum(wunsch.get("von")), _datum(wunsch.get("bis"))
    if von is None:
        von = heute + timedelta(days=1)
        while von.weekday() >= 5:
            von += timedelta(days=1)
    if von < heute:
        von = heute
    if bis is not None and bis < von:
        bis = None
    treffer = _erster_freier(kalender, von, bis, tageszeit)
    if treffer:
        return {"datum": treffer[0], "halbtag": treffer[1], "hinweis": ""}
    ab = (bis or von) + timedelta(days=1)
    treffer = _erster_freier(kalender, ab, None, tageszeit)
    if treffer:
        return {"datum": treffer[0], "halbtag": treffer[1],
                "hinweis": "Im Wunschzeitraum ist nichts frei, Vorschlag liegt außerhalb."}
    return None


def belege(kalender: dict, datum: str, halbtag: str) -> bool:
    for tag in kalender["tage"]:
        if tag["datum"] == datum and halbtag in tag["halbtage"]:
            if not _frei(tag, halbtag):
                return False
            tag["halbtage"][halbtag]["belegt"] += 1
            return True
    return False
