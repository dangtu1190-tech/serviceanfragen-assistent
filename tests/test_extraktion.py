import json
import os
from datetime import date

import pytest

from app.extraktion import Extraktion, ExtraktionsFehler, baue_prompt, extrahiere, parse_antwort
from app.llm_client import FakeClient, lade_konfig

GUELTIG = {
    "kunde": {"anrede": "Herr", "name": "[NAME_1]"},
    "fahrzeug": {"marke": "Toyota", "modell": "Corolla", "baujahr": 2019, "kilometerstand": 85000},
    "kennzeichen": "[KENNZEICHEN_1]",
    "anliegen": [{"kategorie": "wartung", "beschreibung": "Inspektion"}],
    "dringlichkeit": "mittel",
    "wunschzeitraum": {"von": "2026-09-21", "bis": "2026-09-25", "tageszeit": "vormittag"},
    "zustaendigkeit": "werkstatt",
    "unklarheiten": [],
}


def test_parse_gueltig():
    e = parse_antwort(json.dumps(GUELTIG))
    assert isinstance(e, Extraktion)
    assert e.anliegen[0].kategorie == "wartung"


def test_parse_mit_codeblock():
    e = parse_antwort("```json\n" + json.dumps(GUELTIG) + "\n```")
    assert e.kennzeichen == "[KENNZEICHEN_1]"


def test_parse_ungueltiges_json():
    with pytest.raises(ExtraktionsFehler):
        parse_antwort("das ist kein json")


def test_parse_falsche_kategorie():
    kaputt = dict(GUELTIG, anliegen=[{"kategorie": "motor", "beschreibung": "x"}])
    with pytest.raises(ExtraktionsFehler):
        parse_antwort(json.dumps(kaputt))


def test_parse_toleriert_fehlende_optionale_felder():
    knapp = {"kunde": {"anrede": None, "name": None}, "fahrzeug": {"marke": None, "modell": None},
             "kennzeichen": None, "anliegen": [], "dringlichkeit": "niedrig",
             "wunschzeitraum": {"von": None, "bis": None, "tageszeit": "egal"},
             "zustaendigkeit": "werkstatt", "unklarheiten": ["kein Anliegen erkennbar"]}
    e = parse_antwort(json.dumps(knapp))
    assert e.fahrzeug.baujahr is None


def test_prompt_enthaelt_datum_und_platzhalterregel():
    p = baue_prompt(date(2026, 9, 14))
    assert "2026-09-14" in p and "[NAME_1]" in p and "sicherheitsrelevant" in p


def test_extrahiere_sendet_nur_uebergebenen_text():
    fake = FakeClient(GUELTIG)
    e = extrahiere(fake, "Text mit [NAME_1]", date(2026, 9, 14))
    assert e.kunde.name == "[NAME_1]"
    assert fake.aufrufe == ["Text mit [NAME_1]"]


def test_konfig_defaults_ollama(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "ollama")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    k = lade_konfig(env_datei=None)
    assert k.base_url == "http://localhost:11434/v1"
    assert k.api_key == "ollama"


def test_konfig_defaults_langdock(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "x")
    k = lade_konfig(env_datei=None)
    assert k.provider == "langdock" and "langdock.com" in k.base_url and k.model == "gpt-5.1"
