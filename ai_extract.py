"""AI document reader.

Same job as extract.py, different method: instead of format-specific
parsing rules, this hands each attachment to a vision-capable AI model
and asks it to read out the 7 shipment fields directly. Everything
downstream (normalizing, comparing, deciding OK/MISMATCH/NEEDS_REVIEW)
is untouched — it consumes the exact same ExtractResult shape either
way, so swapping this in for extract.extract() is the only change.

Requires an ANTHROPIC_API_KEY environment variable. Until one is set,
pipeline.py falls back to the rule-based reader in extract.py.
"""
import base64
import io
import json
import os
import re
import time

from extract import ExtractResult, _read_docx, _read_xlsx
from normalize import COMPARE_FIELDS

MODEL = "claude-sonnet-4-6"

FIELD_LIST = ", ".join(COMPARE_FIELDS)

PROMPT = f"""You are reading one shipping document (either a Shipping Instruction
or a draft Bill of Lading) to pull out exactly these 7 fields: {FIELD_LIST}.

Rules:
- Different documents label the same field differently (e.g. "Port of Loading",
  "Load Port", and "POL" are the same field). Match by MEANING, not by the exact
  header text.
- shipper / consignee / notify_party: return just the company name, not the
  address lines underneath it.
- container_count: return just the number (e.g. "6", not "6 x 40'HC").
- gross_weight_kg: return just the number in kilograms, no commas or units.
- port_of_loading / port_of_discharge: copy the port EXACTLY as printed,
  including any country after the comma (e.g. "KOPER, SLOVENIA"). Only drop a
  trailing port code in parentheses such as "(SIKOP)". Never shorten it to just
  the city and never add or change words: two documents that print the same port
  must give identical strings, and a genuinely different printed port must
  stay different.
- If a field's value on the document is blank, or a placeholder like "???",
  "TBA", "TBC", "N/A", or a row of underscores, return null for that field —
  do NOT invent a value.
- If this document is clearly not a Shipping Instruction or Bill of Lading at
  all (e.g. it's actually a Commercial Invoice, Packing List, or Certificate
  of Origin), set "wrong_document_type" to true.
- If the document is empty, corrupted, or otherwise unreadable, set
  "readable" to false and leave "fields" as an empty object.

Respond with ONLY this JSON object, no other text:
{{
  "readable": true,
  "wrong_document_type": false,
  "title": "<the document's own title/heading, if any>",
  "fields": {{
    "shipper": "...", "consignee": "...", "notify_party": "...",
    "port_of_loading": "...", "port_of_discharge": "...",
    "container_count": "...", "gross_weight_kg": "..."
  }}
}}
"""


def _get_key():
    """Read the key and strip stray whitespace -- a trailing space or
    newline from a copy-paste is an easy, invisible mistake, and HTTP
    flatly rejects a header value that has one."""
    # Hard off-switch: SDOC_NO_AI=1 forces the free rule-based reader even if
    # a key is present, so building and testing can never spend API credit.
    if os.environ.get("SDOC_NO_AI", "").strip().lower() in ("1", "true", "yes"):
        return None
    key = os.environ.get("ANTHROPIC_API_KEY")
    return key.strip() if key else None


def _client():
    key = _get_key()
    if not key:
        return None
    import anthropic
    return anthropic.Anthropic(api_key=key)


def available():
    """True once a real API key is present — pipeline.py checks this to
    decide whether to use the AI reader or fall back to extract.py."""
    return bool(_get_key())


def _content_block_for(data: bytes, filename: str):
    """Build the message content block(s) for one attachment. PDFs and
    plain text go to the model as-is (Claude reads PDFs natively, image-
    only pages included, so this covers scans too, no separate OCR
    step needed). docx/xlsx aren't natively readable by the model, so we
    mechanically unwrap them to plain text first — that's just format
    unwrapping, not field extraction; the model still does all the
    actual reading and label-matching."""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext == "pdf":
        return [{
            "type": "document",
            "source": {
                "type": "base64",
                "media_type": "application/pdf",
                "data": base64.b64encode(data).decode(),
            },
        }]
    if ext == "txt":
        return [{"type": "text", "text": data.decode("utf-8", errors="replace")}]
    if ext == "docx":
        text, _ = _read_docx(data)
        return [{"type": "text", "text": text}]
    if ext == "xlsx":
        text, _ = _read_xlsx(data)
        return [{"type": "text", "text": text}]
    return [{"type": "text", "text": data.decode("utf-8", errors="replace")}]


def _parse_json_response(raw_text):
    text = raw_text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def ai_extract(data: bytes, filename: str) -> ExtractResult:
    res = ExtractResult()

    if len(data) == 0:
        res.readable = False
        res.unreadable_reason = "empty_file"
        return res

    client = _client()
    if client is None:
        res.readable = False
        res.unreadable_reason = "no_api_key_configured"
        return res

    res.source = "ai"   # past this point, this result is the AI reader's own attempt (success or not)

    try:
        blocks = _content_block_for(data, filename)
        message = None
        last_exc = None
        for attempt in range(3):
            try:
                message = client.messages.create(
                    model=MODEL,
                    max_tokens=1000,
                    messages=[{"role": "user", "content": blocks + [{"type": "text", "text": PROMPT}]}],
                )
                break
            except Exception as exc:
                last_exc = exc
                if attempt < 2:
                    print(f"  [ai_extract] attempt {attempt + 1} failed on {filename} ({exc}); retrying...")
                    time.sleep(2 * (attempt + 1))
        if message is None:
            raise last_exc
        raw_text = "".join(b.text for b in message.content if b.type == "text")
        parsed = _parse_json_response(raw_text)
    except Exception as exc:
        print(f"  [ai_extract] AI call failed on {filename} after retries: {exc}")
        res.readable = False
        res.unreadable_reason = f"ai_call_failed:{type(exc).__name__}"
        return res

    res.readable = bool(parsed.get("readable", True))
    res.wrong_doc_type = bool(parsed.get("wrong_document_type", False))
    res.title = parsed.get("title")
    fields = parsed.get("fields", {}) or {}
    res.fields = {k: v for k, v in fields.items() if k in COMPARE_FIELDS and v is not None}
    return res
