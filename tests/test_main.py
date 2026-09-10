import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import speicher
from app.llm_client import FakeClient
from app.main import erzeuge_app

ANTWORT = {
    "kunde": {"firma": "[FIRMA_1]"},
    "ansprechpartner": {"anrede": "Herr", "name": "[NAME_1]"},
    "anlage": {"typ": "Vakuumhärteofen", "nummer": None, "baujahr": 2019},
    "anliegen": [{"kategorie": "wartung", "beschreibung": "Jahreswartung"}],
    "dringlichkeit": "mittel",
    "wunschzeitraum": {"von": "2026-09-21", "bis": "2026-09-25", "tageszeit": "egal"},
    "zustaendigkeit": "service",
    "unklarheiten": ["Anlagennummer fehlt"],
}


@pytest.fixture
def client(tmp_path, monkeypatch):
    daten = tmp_path / "data"
    daten.mkdir()
    shutil.copyfile("data/mails.json", daten / "mails.json")
    shutil.copyfile("data/kalender.json", daten / "kalender.json")
    monkeypatch.setattr(speicher, "DATEN", daten)
    app = erzeuge_app(client_factory=lambda: FakeClient(ANTWORT))
    return TestClient(app)


def test_startseite_und_status(client):
    assert client.get("/").status_code == 200
    s = client.get("/api/status").json()
    assert s["anbieter"] == "fake" and s["heute"] == "2026-09-14"


def test_mails_liste_und_detail(client):
    liste = client.get("/api/mails").json()
    assert len(liste) == 15 and liste[0]["status"] == "unverarbeitet"
    d = client.get("/api/mails/m01").json()
    assert d["mail"]["id"] == "m01" and d["ergebnis"] is None
    assert client.get("/api/mails/gibtsnicht").status_code == 404


def test_verarbeiten_und_freigeben(client):
    r = client.post("/api/mails/m01/verarbeiten").json()
    assert r["status"] == "offen" and r["extraktion"]["ansprechpartner"]["name"] == "Frank Lindemann"
    assert client.get("/api/mails").json()[0]["status"] == "offen"
    r = client.post("/api/mails/m01/status", json={"status": "freigegeben", "antwort_entwurf": "Geändert"}).json()
    assert r["status"] == "freigegeben" and r["antwort_entwurf"] == "Geändert"
    kal = json.loads((speicher.DATEN / "kalender.json").read_text(encoding="utf-8"))
    tag = [t for t in kal["tage"] if t["datum"] == "2026-09-21"][0]
    assert "T2" in tag["belegt"]
    assert client.post("/api/mails/m01/status", json={"status": "kaputt"}).status_code == 422


def test_neue_mail_anlegen(client):
    r = client.post("/api/mails", json={"absender_name": "Test Person", "absender_firma": "Testfirma GmbH",
                                        "absender_email": "t@example.org",
                                        "betreff": "Test", "text": "Hallo, Test Person hier."}).json()
    assert r["id"] == "m16"
    assert len(client.get("/api/mails").json()) == 16
    e = client.post("/api/mails/m16/verarbeiten").json()
    assert "Test Person" not in e["pseudonym_text"]
    assert "Testfirma" not in e["pseudonym_text"]


def test_freigabe_zyklus_belegt_nur_einmal(client):
    client.post("/api/mails/m01/verarbeiten")
    for status in ("freigegeben", "abgelehnt", "freigegeben", "offen"):
        assert client.post("/api/mails/m01/status", json={"status": status}).status_code == 200
    kal = json.loads((speicher.DATEN / "kalender.json").read_text(encoding="utf-8"))
    tag = [t for t in kal["tage"] if t["datum"] == "2026-09-21"][0]
    assert "T2" not in tag["belegt"]
    client.post("/api/mails/m01/status", json={"status": "freigegeben"})
    kal = json.loads((speicher.DATEN / "kalender.json").read_text(encoding="utf-8"))
    tag = [t for t in kal["tage"] if t["datum"] == "2026-09-21"][0]
    assert "T2" in tag["belegt"]


def test_neu_verarbeiten_gibt_freigegebenen_termin_zurueck(client):
    """Ohne Freigabe des alten Termins bliebe der Techniker für immer belegt."""
    def belegt() -> bool:
        kal = json.loads((speicher.DATEN / "kalender.json").read_text(encoding="utf-8"))
        tag = [t for t in kal["tage"] if t["datum"] == "2026-09-21"][0]
        return "T2" in tag["belegt"]

    client.post("/api/mails/m01/verarbeiten")
    client.post("/api/mails/m01/status", json={"status": "freigegeben"})
    assert belegt()
    r = client.post("/api/mails/m01/verarbeiten").json()
    assert r["status"] == "offen"
    assert not belegt()
    client.post("/api/mails/m01/status", json={"status": "freigegeben"})
    assert belegt()


def test_freigabe_bei_belegtem_techniker_wird_abgelehnt(client):
    """Der Vorschlag reserviert nichts: bis zur Freigabe kann der Techniker anderweitig verplant werden."""
    pfad = speicher.DATEN / "kalender.json"
    termin = client.post("/api/mails/m01/verarbeiten").json()["termin"]

    kal = json.loads(pfad.read_text(encoding="utf-8"))
    tag = [t for t in kal["tage"] if t["datum"] == termin["datum"]][0]
    tag["belegt"] += ["T2", "T4"]
    pfad.write_text(json.dumps(kal, ensure_ascii=False, indent=2), encoding="utf-8")

    r = client.post("/api/mails/m01/status", json={"status": "freigegeben"})
    assert r.status_code == 409
    assert r.json()["detail"] == "Techniker ist an dem Tag inzwischen belegt, Termin kann nicht freigegeben werden"
    assert client.get("/api/mails/m01").json()["ergebnis"]["status"] == "offen"
    kal = json.loads(pfad.read_text(encoding="utf-8"))
    tag = [t for t in kal["tage"] if t["datum"] == termin["datum"]][0]
    assert tag["belegt"].count("T2") == 1
