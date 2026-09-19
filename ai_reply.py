"""Optional AI polish for draft replies.

The template reply is always correct and is the default. This only rewords it
to sound more natural, and it is guarded: if the rewrite drops a value, adds a
number that was not in the original, or fails for any reason, the original
template is returned unchanged. The AI can change the tone, never the facts.
"""
import re

import ai_extract

PROMPT = """Rewrite the email below so it sounds natural, warm and professional, like a
shipping documentation officer writing to a colleague at a shipping company.

Rules:
- Keep EVERY value exactly as written (company names, ports, container counts,
  weights). Do not round, translate, abbreviate or reorder them.
- Do not add any facts, numbers, dates, promises or apologies that are not in the original.
- Keep it short and keep the list of discrepancies if there is one.
- Keep the greeting name and the sign-off.
- Reply with ONLY the rewritten email body, no subject line, no commentary.

EMAIL:
"""

_NUM_RE = re.compile(r"\d+")


def facts_preserved(original, rewritten, required_values):
    """True only if every required value appears verbatim and the rewrite
    introduced no digits that the original did not contain."""
    if not rewritten or not rewritten.strip():
        return False
    for v in required_values:
        if v and v not in rewritten:
            return False
    return set(_NUM_RE.findall(rewritten)) <= set(_NUM_RE.findall(original))


def polish(body, required_values, client=None):
    """Return (text, used_ai). Falls back to `body` on any problem."""
    client = client or ai_extract._client()
    if client is None:
        return body, False
    try:
        message = client.messages.create(
            model=ai_extract.MODEL, max_tokens=700,
            messages=[{"role": "user", "content": PROMPT + body}])
        text = "".join(b.text for b in message.content if b.type == "text").strip()
    except Exception:
        return body, False
    if facts_preserved(body, text, required_values):
        return text, True
    return body, False
