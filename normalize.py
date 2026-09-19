"""Field-label normalisation and value normalisation.

The SI and BL render the same field under different headers ("Port of
Loading" vs "Load Port"). This module maps every header variant we can
observe to one of the 7 canonical field keys, and normalises raw extracted
values so the comparator isn't fooled by formatting differences (commas in
weights, a trailing "(CODE)" on a port, "6 x 40'HC" vs "6", etc).
"""
import re

# Canonical field -> every label string we've seen used for it (SI or BL,
# any file format). Matching is case-insensitive and tolerant of a trailing
# parenthetical gloss (docx adds Chinese translations) so new variants that
# follow the same shape are still caught.
LABEL_ALIASES = {
    "shipper": [
        "shipper", "shipper/exporter", "shipper (principal or seller)",
    ],
    "consignee": [
        "consignee", "consignee (non-negotiable)", "to the order of",
    ],
    "notify_party": [
        "notify party", "notify", "notify party/intermediate consignee",
    ],
    "port_of_loading": [
        "port of loading", "port of loading (pol)", "load port", "pol",
    ],
    "port_of_discharge": [
        "port of discharge", "port of discharge (pod)", "discharge port", "pod",
    ],
    "container_count": [
        "no. of containers", "total containers",
        "no. of containers or packages", "container count",
    ],
    "gross_weight_kg": [
        "gross weight (kg)", "gross wt (kgs)", "gross weight",
        "gross weight毛重(kgs)",
    ],
}

# Flatten to a single lookup: normalised label text -> canonical field.
_LOOKUP = {}
for field, aliases in LABEL_ALIASES.items():
    for a in aliases:
        _LOOKUP[a.lower()] = field

COMPARE_FIELDS = [
    "shipper", "consignee", "notify_party",
    "port_of_loading", "port_of_discharge",
    "container_count", "gross_weight_kg",
]

# Tokens the generator uses to mean "left blank" -- these signal
# missing_value, never an actual mismatch.
BLANK_PATTERNS = [
    re.compile(r"^\?+$"),
    re.compile(r"^_+$"),
    re.compile(r"^_+mt$", re.I),
    re.compile(r"^n/?a$", re.I),
    re.compile(r"^tba$", re.I),
    re.compile(r"^tbc$", re.I),
    re.compile(r"^$"),
]


def clean_label(raw_label):
    """Strip a trailing parenthetical / CJK gloss, punctuation, and case
    so 'Shipper (发货人)' or 'SHIPPER' both become 'shipper'."""
    s = raw_label.strip()
    # drop a leading "TOTAL " (used once, on the PDF gross-weight line)
    s = re.sub(r"^total\s+", "", s, flags=re.I)
    # drop any parenthetical suffix, e.g. "(发货人)", "(POL)" is meaningful
    # only when it's the WHOLE label carrying no other text before it --
    # but "Port of Loading (POL)" is itself a known alias, so only strip
    # parens that contain non-ASCII (CJK glosses) or look like a gloss tail
    # appended by the docx renderer.
    s = re.sub(r"\s*\([^)]*[^\x00-\x7F][^)]*\)\s*$", "", s)  # trailing CJK paren
    s = s.strip().rstrip(":").strip()
    return s.lower()


def field_for_label(raw_label):
    """Return the canonical field name for a raw label string, or None."""
    if raw_label is None:
        return None
    key = clean_label(raw_label)
    if key in _LOOKUP:
        return _LOOKUP[key]
    # loose fallback 1: punctuation-normalised
    key2 = re.sub(r"[^a-z0-9]+", " ", key).strip()
    if key2 in _LOOKUP:
        return _LOOKUP[key2]
    for alias_key, field in _LOOKUP.items():
        alias2 = re.sub(r"[^a-z0-9]+", " ", alias_key).strip()
        if alias2 and alias2 == key2:
            return field
    # loose fallback 2: substring containment either way (catches odd
    # concatenations we haven't anticipated, e.g. embedded CJK glosses)
    for alias_key, field in _LOOKUP.items():
        if len(alias_key) >= 4 and (alias_key in key or key in alias_key):
            return field
    return None


# All known raw label strings (not the lowercase lookup keys) sorted
# longest-first, for prefix matching against lines that have no colon and
# no reliable whitespace gap (e.g. PDF text where a wide column gap
# collapses to a single space).
_ALL_RAW_LABELS = sorted(
    {a for aliases in LABEL_ALIASES.values() for a in aliases},
    key=len, reverse=True,
)


def match_prefix_label(line):
    """If `line` starts with a known label immediately followed by its
    value (no colon, single-space gap -- the PDF case), return
    (field, value). Otherwise None."""
    low = line.lower()
    for alias in _ALL_RAW_LABELS:
        if low.startswith(alias):
            rest = line[len(alias):]
            if rest and rest[0] not in (" ", ":", "\t"):
                continue  # false prefix hit inside a longer word
            value = rest.lstrip(" :\t").strip()
            if value:
                return _LOOKUP[alias], value
    return None


def is_blank_value(raw_value):
    if raw_value is None:
        return True
    v = raw_value.strip()
    if v == "":
        return True
    for pat in BLANK_PATTERNS:
        if pat.match(v):
            return True
    return False


def normalize_value(field, raw_value):
    """Normalise an extracted raw value for a given field so equal
    shipments compare equal regardless of source format. Returns a
    normalised comparable string, or None if the value is unusable."""
    if raw_value is None:
        return None
    v = str(raw_value).strip()
    if v == "":
        return None

    if field in ("shipper", "consignee", "notify_party"):
        # Name is the first line/segment; strip a trailing address that
        # sometimes rides along in the same cell (xlsx uses " | " to join
        # name and address on one line).
        v = v.split("\n")[0]
        v = v.split(" | ")[0]
        v = re.sub(r"\s+", " ", v).strip().upper()
        return v or None

    if field in ("port_of_loading", "port_of_discharge"):
        v = v.split("\n")[0]
        # drop a trailing "(CODE)" like "(CNNTG)"
        v = re.sub(r"\s*\([A-Z0-9]{3,6}\)\s*$", "", v)
        v = re.sub(r"\s+", " ", v).strip().upper()
        v = v.rstrip(",")
        return v or None

    if field == "container_count":
        m = re.search(r"\d+", v)
        return m.group(0) if m else None

    if field == "gross_weight_kg":
        digits = re.sub(r"[^\d]", "", v)
        return digits if digits else None

    return v
