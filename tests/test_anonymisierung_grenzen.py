"""Grenzfälle der Pseudonymisierung: Zeilenumbrüche, Firmen mit Rechtsform,
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


def test_firma_frisst_keine_folgeworte():
    text, tab = anonymisiere("Die Kolb Zahnradfabrik GmbH meldet: Halle 3 steht. Bitte Rückruf.")
    assert text == "Die [FIRMA_1] meldet: Halle 3 steht. Bitte Rückruf."


def test_firma_in_signatur_und_email_domain():
    text, tab = anonymisiere("Gruß\nAndrea Wittmann\nElektro Wittmann GmbH\na.wittmann@elektro-wittmann.example\n06051 881720",
                             absender_name="Andrea Wittmann", absender_firma="Elektro Wittmann GmbH")
    assert "Wittmann" not in text and "elektro-wittmann" not in text
    typen = [t["typ"] for t in tab]
    assert "FIRMA" in typen and "NAME" in typen and "EMAIL" in typen and "TELEFON" in typen


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
    """Dokumentierte Grenze: der Nachname wird zum vollen Namen zurückgesetzt.

    "Elektro Wittmann GmbH" (das frühere Beispiel hier) ist seit der
    Firmenerkennung selbst ein FIRMA-Treffer (siehe
    test_firma_in_signatur_und_email_domain) — dieser Test prueft die reine
    Namensteil-Ersetzung deshalb an einem Satz ohne Rechtsform."""
    text, tab = anonymisiere("Anruf von Wittmann wegen der Anlage.", absender_name="Andrea Wittmann")
    assert text == "Anruf von [NAME_1] wegen der Anlage."
    assert zuruecksetzen(text, tab) == "Anruf von Andrea Wittmann wegen der Anlage."


def test_ascii_grussformel_findet_die_signatur():
    text, tab = anonymisiere("Danke.\n\nViele Gruesse\nMax Muster")
    assert [t["original"] for t in tab if t["typ"] == "NAME"] == ["Max Muster"]
    assert text == "Danke.\n\nViele Gruesse\n[NAME_1]"


def test_ascii_grussformel_lange_variante():
    text, tab = anonymisiere("Bitte um Termin.\n\nMit freundlichen Gruessen\nJens Ohlmann")
    assert [t["original"] for t in tab if t["typ"] == "NAME"] == ["Jens Ohlmann"]
