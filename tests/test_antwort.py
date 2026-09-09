from app.antwort import baue_antwort

EX = {
    "kunde": {"anrede": "Frau", "name": "Sabine Krämer"},
    "fahrzeug": {"marke": "Toyota", "modell": "Corolla", "baujahr": None, "kilometerstand": None},
    "kennzeichen": "MKK-AB 1234",
    "anliegen": [{"kategorie": "wartung", "beschreibung": "Inspektion"},
                 {"kategorie": "hu_au", "beschreibung": "HU/AU fällig"}],
    "dringlichkeit": "mittel",
    "wunschzeitraum": {"von": "2026-09-21", "bis": "2026-09-25", "tageszeit": "vormittag"},
    "zustaendigkeit": "werkstatt",
    "unklarheiten": [],
}


def test_entwurf_mit_termin():
    t = baue_antwort(EX, {"datum": "2026-09-21", "halbtag": "vormittag", "hinweis": ""}, "Inspektion")
    assert t.startswith("Sehr geehrte Frau Krämer,")
    assert '„Inspektion"' in t
    assert "Inspektion" in t and "HU/AU fällig" in t
    assert "Montag, 21.09.2026" in t and "Vormittag" in t
    assert "MKK-AB 1234" in t
    assert "[" not in t
    assert t.rstrip().endswith("Ihr Serviceteam")


def test_entwurf_hinweis_und_unklarheit():
    ex = dict(EX, unklarheiten=["Kennzeichen fehlt"], kennzeichen=None)
    t = baue_antwort(ex, {"datum": "2026-09-18", "halbtag": "nachmittag",
                          "hinweis": "Im Wunschzeitraum ist nichts frei, Vorschlag liegt außerhalb."}, "x")
    assert "nichts frei" in t
    assert "Kennzeichen fehlt" in t


def test_entwurf_verkauf_weiterleitung():
    ex = dict(EX, zustaendigkeit="verkauf", anliegen=[{"kategorie": "verkauf", "beschreibung": "Probefahrt"}])
    t = baue_antwort(ex, None, "Probefahrt")
    assert "Verkauf" in t and "weitergeleitet" in t
    assert "Verkauf: Probefahrt" in t
    assert "Termin" not in t.split("weitergeleitet")[0]


def test_entwurf_ohne_namen_und_ohne_termin():
    ex = dict(EX, kunde={"anrede": None, "name": None})
    t = baue_antwort(ex, None, "x")
    assert t.startswith("Guten Tag,")
    assert "melden uns" in t


def test_entwurf_ohne_betreff():
    t = baue_antwort(EX, None, "")
    assert "vielen Dank für Ihre Anfrage." in t and '„' not in t
