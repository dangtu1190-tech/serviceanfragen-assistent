"""Läuft nur mit gesetztem Schlüssel. Ein Aufruf, eine Mail."""
import os
from datetime import date

import pytest

from app.kalender import lade_kalender
from app.llm_client import LLMClient, lade_konfig
from app.pipeline import verarbeite
from app.speicher import lade_mails

pytestmark = pytest.mark.skipif(not os.getenv("LLM_API_KEY"), reason="LLM_API_KEY nicht gesetzt")


def test_echtlauf_eine_mail():
    client = LLMClient(lade_konfig())
    mail = [m for m in lade_mails() if m["id"] == "m05"][0]
    erg = verarbeite(mail, client, lade_kalender("data/kalender.json"), date(2026, 9, 14))
    assert erg["status"] == "offen", erg["extraktion_fehler"]
    assert len(erg["extraktion"]["anliegen"]) >= 3
    assert erg["extraktion"]["kennzeichen"] == "MKK-JB 3300"
    assert erg["extraktion"]["fahrzeug"]["kilometerstand"] == 118000
