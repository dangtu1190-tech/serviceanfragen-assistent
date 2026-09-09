import json
import re
from datetime import date

from app.kalender import lade_kalender
from app.llm_client import FakeClient
from app.pipeline import verarbeite
from app.speicher import lade_mails

HEUTE = date(2026, 9, 14)
ANTWORT = {
    "kunde": {"anrede": "Frau", "name": "[NAME_1]"},
    "fahrzeug": {"marke": "Toyota", "modell": "Corolla", "baujahr": None, "kilometerstand": None},
    "kennzeichen": "[KENNZEICHEN_1]",
    "anliegen": [{"kategorie": "wartung", "beschreibung": "Inspektion"}],
    "dringlichkeit": "mittel",
    "wunschzeitraum": {"von": "2026-09-21", "bis": "2026-09-22", "tageszeit": "vormittag"},
    "zustaendigkeit": "werkstatt",
    "unklarheiten": [],
}


def test_alle_mails_laden():
    mails = lade_mails()
    assert len(mails) == 15
    assert {m["id"] for m in mails} == {f"m{i:02d}" for i in range(1, 16)}


def test_modell_sieht_keine_originale():
    mails = lade_mails()
    kal = lade_kalender("data/kalender.json")
    for mail in mails:
        fake = FakeClient(ANTWORT)
        erg = verarbeite(mail, fake, kal, HEUTE)
        gesendet = fake.aufrufe[0]
        assert gesendet == erg["pseudonym_text"]
        assert mail["absender_email"] not in gesendet
        for eintrag in erg["platzhalter"]:
            assert eintrag["original"] not in gesendet, (mail["id"], eintrag)
        nachname = mail["absender_name"].split()[-1]
        assert nachname not in gesendet, mail["id"]


def test_ergebnis_felder_und_rueckersetzung():
    mail = lade_mails()[0]
    erg = verarbeite(mail, FakeClient(ANTWORT), lade_kalender("data/kalender.json"), HEUTE)
    assert erg["mail_id"] == "m01"
    assert erg["status"] == "offen"
    assert erg["extraktion"]["kunde"]["name"] == "Katrin Vollmer"
    assert erg["extraktion"]["kennzeichen"] == "MKK-KV 2187"
    assert erg["termin"] == {"datum": "2026-09-21", "halbtag": "vormittag", "hinweis": ""}
    assert "Katrin Vollmer" not in erg["pseudonym_text"]
    assert "[" not in erg["antwort_entwurf"]
    assert erg["anbieter"] == "fake" and erg["dauer_ms"] >= 0 and erg["zeitpunkt"]
    json.dumps(erg)  # muss serialisierbar sein


def test_ungueltige_modellantwort_wird_pruefung_noetig():
    mail = lade_mails()[0]
    erg = verarbeite(mail, FakeClient("kein json"), lade_kalender("data/kalender.json"), HEUTE)
    assert erg["status"] == "pruefung_noetig"
    assert erg["extraktion"] is None and "JSON" in erg["extraktion_fehler"]
    assert erg["termin"] is None
    assert "Katrin Vollmer" not in erg["pseudonym_text"]


def _woerter(wert: str) -> set[str]:
    """Alle durch Leerraum getrennten Teile ab drei Zeichen."""
    return {t for t in wert.split() if len(t) >= 3}


def test_kein_original_erreicht_das_modell():
    """Schaerfer als test_modell_sieht_keine_originale: auch Namensteile und
    Bestandteile jedes Platzhalter-Originals duerfen nicht im Prompt stehen."""
    kal = lade_kalender("data/kalender.json")
    for mail in lade_mails():
        fake = FakeClient(ANTWORT)
        erg = verarbeite(mail, fake, kal, HEUTE)
        gesendet = fake.aufrufe[0]
        verboten = {mail["absender_email"]} | _woerter(mail["absender_name"])
        for eintrag in erg["platzhalter"]:
            verboten.add(eintrag["original"])
            verboten |= _woerter(eintrag["original"])
        for wert in verboten:
            if not wert:
                continue
            muster = re.compile(r"(?<!\w)" + re.escape(wert) + r"(?!\w)", re.IGNORECASE)
            assert not muster.search(gesendet), (mail["id"], wert)
