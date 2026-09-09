"""Extraktion der Anfrage nach JSON: Schema (Pydantic), Prompt, Antwort parsen.

Das Modell sieht nur den pseudonymisierten Text; Platzhalter wie [NAME_1]
müssen wörtlich übernommen werden. Ungültige Antworten werfen
ExtraktionsFehler, nie einen rohen Absturz.
"""
import json
from datetime import date
from typing import Literal

from pydantic import BaseModel, ValidationError

Kategorie = Literal["wartung", "reparatur", "reifen", "hu_au", "karosserie", "verkauf", "sonstiges"]


class Kunde(BaseModel):
    anrede: str | None = None
    name: str | None = None


class Fahrzeug(BaseModel):
    marke: str | None = None
    modell: str | None = None
    baujahr: int | None = None
    kilometerstand: int | None = None


class Anliegen(BaseModel):
    kategorie: Kategorie
    beschreibung: str


class Wunschzeitraum(BaseModel):
    von: str | None = None
    bis: str | None = None
    tageszeit: Literal["vormittag", "nachmittag", "egal"] = "egal"


class Extraktion(BaseModel):
    kunde: Kunde = Kunde()
    fahrzeug: Fahrzeug = Fahrzeug()
    kennzeichen: str | None = None
    anliegen: list[Anliegen] = []
    dringlichkeit: Literal["niedrig", "mittel", "hoch", "sicherheitsrelevant"] = "mittel"
    wunschzeitraum: Wunschzeitraum = Wunschzeitraum()
    zustaendigkeit: Literal["werkstatt", "verkauf"] = "werkstatt"
    unklarheiten: list[str] = []


class ExtraktionsFehler(Exception):
    pass


SCHEMA_TEXT = """{
  "kunde": {"anrede": "Herr|Frau|null", "name": "Platzhalter wie [NAME_1] oder null"},
  "fahrzeug": {"marke": "string|null", "modell": "string|null", "baujahr": "int|null", "kilometerstand": "int|null"},
  "kennzeichen": "Platzhalter wie [KENNZEICHEN_1] oder null",
  "anliegen": [{"kategorie": "wartung|reparatur|reifen|hu_au|karosserie|verkauf|sonstiges", "beschreibung": "kurz, deutsch"}],
  "dringlichkeit": "niedrig|mittel|hoch|sicherheitsrelevant",
  "wunschzeitraum": {"von": "YYYY-MM-DD|null", "bis": "YYYY-MM-DD|null", "tageszeit": "vormittag|nachmittag|egal"},
  "zustaendigkeit": "werkstatt|verkauf",
  "unklarheiten": ["string"]
}"""


def baue_prompt(heute: date) -> str:
    return (
        "Du bist die Serviceannahme eines Autohauses. Du bekommst eine Kunden-E-Mail, in der "
        "personenbezogene Daten durch Platzhalter ersetzt sind, z. B. [NAME_1], [KENNZEICHEN_1], "
        "[TELEFON_1]. Übernimm Platzhalter wörtlich, erfinde keine Werte dahinter.\n"
        f"Heute ist {heute.isoformat()} ({heute.strftime('%A')}). Relative Angaben wie "
        "'nächste Woche' oder 'Mittwoch' rechnest du auf Kalenderdaten um.\n"
        "Antworte ausschließlich mit einem JSON-Objekt nach diesem Schema:\n" + SCHEMA_TEXT + "\n"
        "Regeln: Jedes eigenständige Anliegen ist ein Listeneintrag. Bremsen, Lenkung, Reifen mit "
        "Druckverlust, Motorwarnleuchte rot oder Rauch sind 'sicherheitsrelevant'. Geht es um Kauf, "
        "Probefahrt, Leasing oder Angebot für ein Fahrzeug, ist zustaendigkeit 'verkauf'. "
        "Fehlt eine Information, die du für den Termin brauchst (Kennzeichen, konkretes Anliegen, "
        "Zeitraum), schreibe sie in unklarheiten. Keine Erklärungen außerhalb des JSON."
    )


def parse_antwort(content: str) -> Extraktion:
    text = content.strip()
    if "```" in text:
        text = text.split("```json")[-1] if "```json" in text else text.split("```")[1]
        text = text.split("```")[0]
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as e:
        raise ExtraktionsFehler(f"Antwort ist kein JSON: {e}") from e
    try:
        return Extraktion.model_validate(daten)
    except ValidationError as e:
        raise ExtraktionsFehler(f"Antwort passt nicht zum Schema: {e.errors()[0]['msg']} bei {e.errors()[0]['loc']}") from e


def extrahiere(client, pseudonym_text: str, heute: date) -> Extraktion:
    return parse_antwort(client.frage_json(baue_prompt(heute), pseudonym_text))
