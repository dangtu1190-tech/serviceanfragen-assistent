from datetime import date
from app.kalender import erzeuge_kalender, finde_termin, belege

HEUTE = date(2026, 9, 14)


def _kal():
    kal = erzeuge_kalender(HEUTE, wochen=3)
    for tag in kal["tage"]:
        if tag["datum"] in ("2026-09-16", "2026-09-17"):
            for h in tag["halbtage"].values():
                h["belegt"] = h["kapazitaet"]
        if tag["datum"] == "2026-09-15":
            tag["halbtage"]["vormittag"]["belegt"] = tag["halbtage"]["vormittag"]["kapazitaet"]
    return kal


def _ex(**kw):
    basis = {"zustaendigkeit": "werkstatt", "dringlichkeit": "mittel",
             "wunschzeitraum": {"von": None, "bis": None, "tageszeit": "egal"}}
    basis.update(kw)
    return basis


def test_nur_werktage():
    kal = erzeuge_kalender(HEUTE, wochen=1)
    assert [t["datum"] for t in kal["tage"]] == ["2026-09-14", "2026-09-15", "2026-09-16", "2026-09-17", "2026-09-18"]
    assert kal["basisdatum"] == "2026-09-14"


def test_ohne_wunsch_ab_naechstem_werktag():
    t = finde_termin(_kal(), _ex(), HEUTE)
    assert t == {"datum": "2026-09-15", "halbtag": "nachmittag", "hinweis": ""}


def test_wunschzeitraum_und_tageszeit():
    t = finde_termin(_kal(), _ex(wunschzeitraum={"von": "2026-09-21", "bis": "2026-09-25", "tageszeit": "vormittag"}), HEUTE)
    assert t["datum"] == "2026-09-21" and t["halbtag"] == "vormittag" and t["hinweis"] == ""


def test_wunschzeitraum_ausgebucht_naechster_danach():
    t = finde_termin(_kal(), _ex(wunschzeitraum={"von": "2026-09-16", "bis": "2026-09-17", "tageszeit": "egal"}), HEUTE)
    assert t["datum"] == "2026-09-18"
    assert "außerhalb" in t["hinweis"]


def test_sicherheitsrelevant_zieht_vor():
    t = finde_termin(_kal(), _ex(dringlichkeit="sicherheitsrelevant",
                                 wunschzeitraum={"von": "2026-09-28", "bis": "2026-09-30", "tageszeit": "egal"}), HEUTE)
    assert t["datum"] == "2026-09-14"
    assert "vorgezogen" in t["hinweis"]


def test_verkauf_kein_termin():
    assert finde_termin(_kal(), _ex(zustaendigkeit="verkauf"), HEUTE) is None


def test_belegen():
    kal = _kal()
    assert belege(kal, "2026-09-18", "vormittag") is True
    assert kal["tage"][4]["halbtage"]["vormittag"]["belegt"] == 1
    assert belege(kal, "2026-09-16", "vormittag") is False
    assert belege(kal, "2099-01-01", "vormittag") is False


def test_bis_vor_von_wird_offener_zeitraum():
    t = finde_termin(_kal(), _ex(wunschzeitraum={"von": "2026-09-25", "bis": "2026-09-14", "tageszeit": "egal"}), HEUTE)
    assert t["datum"] == "2026-09-25" and t["hinweis"] == ""
