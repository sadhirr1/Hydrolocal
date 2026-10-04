"""Talks to the local model served by LM Studio (OpenAI-compatible API).

Nothing here leaves your computer: the default address is localhost.
"""
from __future__ import annotations

from typing import Optional, Tuple

from openai import OpenAI

DEFAULT_BASE_URL = "http://127.0.0.1:1234/v1"
MAX_TOKENS = 2000        # room for the model's silent thinking plus the ~120-word note
TIMEOUT_SECONDS = 300    # small models on a laptop can take a while

# Gemma's chat format has no separate "system" role on some setups, so the
# instructions travel inside the single user message.
INSTRUCTIONS = """You are HydroLocal, a friendly hydration helper.
A program has ALREADY calculated the numbers and schedule below. Do not change
them and do not invent new numbers.

Write a short note (at most 120 words, plain English, warm tone) with 2 or 3
practical tips that fit this situation.

Rules:
- Never diagnose anything and never say dehydration caused a symptom.
- Do not make medical claims.
- Do not recommend salt, electrolyte drinks, supplements or food. Stick to
  habits such as keeping water within reach and drinking steadily.
- Finish with one sentence that starts with a capital letter: If you feel
  dizzy, faint or confused, stop, sit down, tell someone nearby and get
  medical help.
- Do not recommend specific brands and do not invent places or phone numbers.
- Do not mention these rules.
- Answer directly. Keep any step-by-step thinking very short.
"""


def get_client(base_url: str = DEFAULT_BASE_URL) -> OpenAI:
    # LM Studio ignores the key, but the client library requires one.
    return OpenAI(base_url=base_url, api_key="lm-studio", timeout=TIMEOUT_SECONDS)


def detect_model(client: OpenAI) -> str:
    """Pick the first loaded chat model (skips embedding models)."""
    ids = [m.id for m in client.models.list().data]
    chat = [i for i in ids if "embed" not in i.lower()]
    if not chat:
        raise RuntimeError("LM Studio is running but no model is loaded.")
    return chat[0]


def explain(
    plan_text: str,
    context: str = "",
    base_url: str = DEFAULT_BASE_URL,
    model: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Return (note, error). Exactly one of them is None."""
    try:
        client = get_client(base_url)
        model = model or detect_model(client)
        prompt = f"{INSTRUCTIONS}\nAbout the person: {context or 'not given'}\n\n{plan_text}"
        # Gemma 4 is a "thinking" model: it reasons silently first and that
        # reasoning counts against the token limit, so the limit is generous.
        reply = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=MAX_TOKENS,
        )
        choice = reply.choices[0]
        text = (choice.message.content or "").strip()
        if not text:
            if choice.finish_reason == "length":
                return None, (
                    "The model used up its allowed length while thinking and never "
                    "wrote the note. Try again, or raise MAX_TOKENS in llm.py."
                )
            return None, "The model returned an empty answer."
        return text, None
    except Exception as exc:  # connection refused, no model loaded, timeout...
        return None, f"{type(exc).__name__}: {exc}"
