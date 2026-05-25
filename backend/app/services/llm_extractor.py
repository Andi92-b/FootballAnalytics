"""
Extracts structured match events from German-language match texts using the Claude API.
Uses prompt caching on the system prompt to reduce token cost (~80% on repeated calls).
"""
import json
import os
import re

import anthropic

from backend import db

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY environment variable not set")
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


_SYSTEM_PROMPT = """\
Du bist ein Fußball-Taktik-Analyst. Du erhältst deutsche Spielberichte und Live-Ticker-Texte
eines FC-Bayern-München-Spiels und extrahierst daraus strukturierte taktische Ereignisse.

Antworte ausschließlich mit einem JSON-Objekt der folgenden Form (kein Markdown, kein Text darum):

{
  "events": [
    {
      "minute": <integer oder null>,
      "type": "<goal|big_chance|chance_created|chance_conceded|pressing_success|pressing_failure|tactical_change|substitution>",
      "direction": "<offensive|defensive>",
      "situation": "<counterattack|buildup_play|set_piece_attack|set_piece_defense|individual_error|high_press|low_block_break|transition|penalty>",
      "trigger": "<ball_loss_midfield|ball_loss_defensive|corner|free_kick|second_ball|individual_mistake|through_ball|cross|penalty_foul|null>",
      "defensive_cover": "<1v1|2v1|2v2|3v2|outnumbered|adequate|unclear|null>",
      "players_involved": ["<Spielername>", ...],
      "outcome": "<goal|saved|missed|blocked|chance|no_chance>",
      "description": "<kurzes deutsches Zitat oder Paraphrase aus dem Quelltext, max. 150 Zeichen>",
      "confidence": "<high|medium|low>"
    }
  ]
}

Regeln:
- Extrahiere nur klar erkennbare taktische Ereignisse, keine Spielerstatistiken oder allgemeinen Kommentare.
- direction="offensive" wenn Bayern angreift; direction="defensive" wenn Bayern verteidigt.
- Schreibe players_involved als JSON-Array von Spielernamen (nur Nachname wenn eindeutig).
- Wenn ein Feld nicht bestimmt werden kann, setze null (kein leerer String).
- Extrahiere zwischen 5 und 30 Ereignisse pro Spiel. Priorisiere Tore, große Chancen und taktische Schlüsselmomente.
- Confidence "high" = explizit im Text beschrieben; "medium" = sinngemäß erkennbar; "low" = spekulativ.
"""

MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096


def extract_match_events(match_id: str, texts: list[dict]) -> list[dict]:
    """
    Call Claude API to extract tactical events from match texts.

    texts: list of {source: str, content: str} dicts from text_sources table.
    Returns list of event dicts. On success, inserts into match_events and marks match analysed.
    """
    if not texts:
        return []

    combined = "\n\n".join(
        f"=== Quelle: {t['source']} ===\n{t['content']}" for t in texts if t.get("content")
    )
    if not combined.strip():
        return []

    client = _get_client()

    response = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=[
            {
                "type": "text",
                "text": _SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ],
        messages=[
            {
                "role": "user",
                "content": (
                    f"Hier sind die Texte für Spiel-ID: {match_id}\n\n{combined}"
                ),
            }
        ],
    )

    raw = response.content[0].text.strip()

    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = re.sub(r"^```[a-z]*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    data = json.loads(raw)
    events = data.get("events", [])

    enriched: list[dict] = []
    for ev in events:
        enriched.append(
            {
                "match_id": match_id,
                "minute": ev.get("minute"),
                "type": ev.get("type"),
                "direction": ev.get("direction"),
                "situation": ev.get("situation"),
                "trigger": ev.get("trigger"),
                "defensive_cover": ev.get("defensive_cover"),
                "players_involved": json.dumps(ev.get("players_involved") or [], ensure_ascii=False),
                "outcome": ev.get("outcome"),
                "description": ev.get("description"),
                "confidence": ev.get("confidence"),
            }
        )

    if enriched:
        db.insert_match_events(enriched)
        db.mark_match_analysed(match_id)

    return enriched
