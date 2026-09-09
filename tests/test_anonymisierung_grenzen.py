"""Grenzfälle der Pseudonymisierung: Zeilenumbrüche, kurze Kennzeichen,
Ortszusätze, mehrdeutige Nachnamen, ASCII-Grußformeln."""
from app.anonymisierung import anonymisiere, zuruecksetzen


def test_telefon_frisst_die_folgezeile_nicht():
    text, tab = anonymisiere("Tel. 06021 123456\n63739 Aschaffenburg")
    assert text == "Tel. [TELEFON_1]\n[ORT_1]"
    assert {t["typ"] for t in tab} == {"TELEFON", "ORT"}
    assert zuruecksetzen(text, tab) == "Tel. 06021 123456\n63739 Aschaffenburg"


def test_telefon_frisst_das_datum_der_folgezeile_nicht():
    text, tab = anonymisiere("Rueckruf 0170 1234567\n15.09. passt mir")
    assert "15.09." in text
    assert [t["original"] for t in tab if t["typ"] == "TELEFON"] == ["0170 1234567"]


def test_zwei_nummern_in_zwei_zeilen_sind_zwei_eintraege():
    text, tab = anonymisiere("Telefon 06051 881720\n0171 6554321")
    originale = [t["original"] for t in tab if t["typ"] == "TELEFON"]
    assert originale == ["06051 881720", "0171 6554321"]
    assert text == "Telefon [TELEFON_1]\n[TELEFON_2]"


def test_einstellige_kennzeichen_mit_bindestrich():
    text, tab = anonymisiere("AB-C 1, B-A 1, M-X 2")
    originale = [t["original"] for t in tab if t["typ"] == "KENNZEICHEN"]
    assert originale == ["AB-C 1", "B-A 1", "M-X 2"]
    assert text == "[KENNZEICHEN_1], [KENNZEICHEN_2], [KENNZEICHEN_3]"


def test_kurze_modellnamen_bleiben_trotz_einstelliger_kennzeichen():
    text, tab = anonymisiere("BMW X5, VW T6.1, VW ID.4, Audi A4")
    assert [t for t in tab if t["typ"] == "KENNZEICHEN"] == []
    assert text == "BMW X5, VW T6.1, VW ID.4, Audi A4"


def test_ort_zusatz_frisst_keine_folgeworte():
    text, tab = anonymisiere("63739 Aschaffenburg bei Herrn Mueller vorbeikommen. 60313 Frankfurt am Main.")
    assert "Mueller" not in text
    assert [t["original"] for t in tab if t["typ"] == "ORT"] == ["63739 Aschaffenburg", "60313 Frankfurt"]


def test_gemeinsamer_nachname_bleibt_allein_stehen():
    text, tab = anonymisiere(
        "meine Frau Sabine Krämer und ich, Peter Krämer, kommen. Krämer allein reicht nicht.",
        absender_name="Peter Krämer",
    )
    namen = [t for t in tab if t["typ"] == "NAME"]
    assert len(namen) == 2
    assert {t["original"] for t in namen} == {"Sabine Krämer", "Peter Krämer"}
    assert "Sabine Krämer" not in text and "Peter Krämer" not in text
    # Dokumentierte Grenze: der allein stehende Nachname ist nicht zuordenbar
    assert "Krämer allein reicht nicht." in text


def test_eindeutiger_nachname_wird_weiter_ersetzt():
    """Dokumentierte Grenze: der Nachname wird zum vollen Namen zurückgesetzt."""
    text, tab = anonymisiere("Elektro Wittmann GmbH", absender_name="Andrea Wittmann")
    assert text == "Elektro [NAME_1] GmbH"
    assert zuruecksetzen(text, tab) == "Elektro Andrea Wittmann GmbH"


def test_ascii_grussformel_findet_die_signatur():
    text, tab = anonymisiere("Danke.\n\nViele Gruesse\nMax Muster")
    assert [t["original"] for t in tab if t["typ"] == "NAME"] == ["Max Muster"]
    assert text == "Danke.\n\nViele Gruesse\n[NAME_1]"


def test_ascii_grussformel_lange_variante():
    text, tab = anonymisiere("Bitte um Termin.\n\nMit freundlichen Gruessen\nJens Ohlmann")
    assert [t["original"] for t in tab if t["typ"] == "NAME"] == ["Jens Ohlmann"]
