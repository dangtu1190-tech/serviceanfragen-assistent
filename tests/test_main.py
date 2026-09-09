import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import speicher
from app.llm_client import FakeClient
from app.main import erzeuge_app

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
    assert r["status"] == "offen" and r["extraktion"]["kunde"]["name"] == "Katrin Vollmer"
    assert client.get("/api/mails").json()[0]["status"] == "offen"
    r = client.post("/api/mails/m01/status", json={"status": "freigegeben", "antwort_entwurf": "Geändert"}).json()
    assert r["status"] == "freigegeben" and r["antwort_entwurf"] == "Geändert"
    kal = json.loads((speicher.DATEN / "kalender.json").read_text(encoding="utf-8"))
    tag = [t for t in kal["tage"] if t["datum"] == "2026-09-21"][0]
    assert tag["halbtage"]["vormittag"]["belegt"] == 1
    assert client.post("/api/mails/m01/status", json={"status": "kaputt"}).status_code == 422


def test_neue_mail_anlegen(client):
    r = client.post("/api/mails", json={"absender_name": "Test Person", "absender_email": "t@example.org",
                                        "betreff": "Test", "text": "Hallo, Test Person hier."}).json()
    assert r["id"] == "m16"
    assert len(client.get("/api/mails").json()) == 16
    e = client.post("/api/mails/m16/verarbeiten").json()
    assert "Test Person" not in e["pseudonym_text"]


def test_freigabe_zyklus_belegt_nur_einmal(client):
    client.post("/api/mails/m01/verarbeiten")
    for status in ("freigegeben", "abgelehnt", "freigegeben", "offen"):
        assert client.post("/api/mails/m01/status", json={"status": status}).status_code == 200
    kal = json.loads((speicher.DATEN / "kalender.json").read_text(encoding="utf-8"))
    tag = [t for t in kal["tage"] if t["datum"] == "2026-09-21"][0]
    assert tag["halbtage"]["vormittag"]["belegt"] == 0
    client.post("/api/mails/m01/status", json={"status": "freigegeben"})
    kal = json.loads((speicher.DATEN / "kalender.json").read_text(encoding="utf-8"))
    assert [t for t in kal["tage"] if t["datum"] == "2026-09-21"][0]["halbtage"]["vormittag"]["belegt"] == 1
