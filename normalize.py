"""Field-label normalisation and value normalisation.

The SI and BL render the same field under different headers ("Port of
Loading" vs "Load Port"). This module maps every header variant we can
observe to one of the 7 canonical field keys, and normalises raw extracted
values so the comparator isn't fooled by formatting differences (commas in
weights, a trailing "(CODE)" on a port, "6 x 40'HC" vs "6", etc).
"""
import re
from decimal import Decimal, InvalidOperation

# Canonical field -> every label string we've seen used for it (SI or BL,
# any file format). Matching is case-insensitive and tolerant of a trailing
# parenthetical gloss (docx adds Chinese translations) so new variants that
# follow the same shape are still caught.
LABEL_ALIASES = {
    "shipper": [
        "shipper", "shipper/exporter", "shipper (principal or seller)",
        "exporter", "seller",
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


def clean_label(raw_label, strip_total=True):
    """Strip a trailing parenthetical / CJK gloss, punctuation, and case
    so 'Shipper (发货人)' or 'SHIPPER' both become 'shipper'."""
    s = raw_label.strip()
    # a leading "TOTAL " is dropped ("TOTAL Gross Weight"), but callers also
    # try the label with it kept because "Total Containers" is an alias.
    if strip_total:
        s = re.sub(r"^total\s+", "", s, flags=re.I)
    # drop a trailing parenthetical that holds non-ASCII text (CJK glosses
    # appended by the docx renderer); "(POL)" is meaningful, so it stays.
    s = re.sub(r"\s*\([^)]*[^\x00-\x7F][^)]*\)\s*$", "", s)
    s = s.strip().rstrip(":").strip()
    return s.lower()


def _squash(text):
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


_SQUASHED_LOOKUP = {_squash(k): f for k, f in _LOOKUP.items()}
# Short aliases (POL, POD) are too easy to hit by accident for prefix matching.
_PREFIX_ALIASES = sorted((a for a in _LOOKUP if len(a) >= 4), key=len, reverse=True)
_LABEL_TAIL_RE = re.compile(r"[a-z]{0,3}\s?\([^)]*\)")


def field_for_label(raw_label):
    """Return the canonical field name for a raw label string, or None.

    Matching is exact after cleaning (case, punctuation, a leading TOTAL,
    a trailing CJK gloss, CJK characters glued onto the label). Substring
    matching is deliberately NOT used: it maps unrelated labels such as
    "Shipper Reference" or "Consignee Tel" onto real fields, and the first
    hit wins, so that would silently corrupt the extracted value."""
    if raw_label is None:
        return None
    for strip_total in (False, True):
        key = clean_label(raw_label, strip_total)
        if key in _LOOKUP:
            return _LOOKUP[key]
        squashed = _squash(key)
        if squashed in _SQUASHED_LOOKUP:
            return _SQUASHED_LOOKUP[squashed]
        # CJK text glued straight onto the label, e.g. "gross weight毛重(kgs)"
        ascii_only = _squash(re.sub(r"[^\x00-\x7F]+", " ", key))
        if ascii_only in _SQUASHED_LOOKUP:
            return _SQUASHED_LOOKUP[ascii_only]
        # A known label followed only by a parenthesised unit/gloss, allowing
        # a few stray glyphs before it: PDF extraction can print
        # "Gross Weightnn(KGS)" when label and value columns overlap.
        for alias in _PREFIX_ALIASES:
            if key.startswith(alias) and _LABEL_TAIL_RE.fullmatch(key[len(alias):]):
                return _LOOKUP[alias]
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
        return _container_count(v)

    if field == "gross_weight_kg":
        return _weight_kg(v)

    return v


def _container_count(v):
    """'3 x 40'HC' -> '3', "40'HC x 3" -> '3', '03 CONTAINERS' -> '3'."""
    for pat in (r"^\s*(\d+)\s*[xX×]",                        # "3 x 40'HC"
                r"\d+\s*['’]?\s*[A-Za-z]{0,3}\s*[xX×]\s*(\d+)\b",  # "40'HC x 3"
                r"(\d+)"):
        m = re.search(pat, v)
        if m:
            return str(int(m.group(1)))
    return None


_TONNE_RE = re.compile(r"\b(mts?|tonnes?|tons?|t)\b", re.I)
_LB_RE = re.compile(r"\b(lbs?|pounds?)\b", re.I)


def _weight_kg(v):
    """Parse a printed weight into kilograms as a canonical string, so
    '61,026 KG', '61,026.00 KGS', '61.026,00' and '61.026 MT' all agree."""
    m = re.search(r"\d[\d.,\s]*", v)
    if not m:
        return None
    num = m.group(0).strip().replace(" ", "")
    tonnes = bool(_TONNE_RE.search(v))
    dots, commas = num.count("."), num.count(",")
    if dots and commas:
        dec = "." if num.rfind(".") > num.rfind(",") else ","
    elif dots > 1 or commas > 1:
        dec = None                                   # only thousands separators
    elif dots or commas:
        sep = "." if dots else ","
        tail = num.split(sep)[1]
        # one separator + exactly 3 digits is thousands ("61,026") unless
        # the unit is tonnes, where "61.026 MT" is a decimal.
        dec = sep if (len(tail) != 3 or tonnes) else None
    else:
        dec = None
    if dec:
        int_part, _, frac = num.rpartition(dec)
        int_part = re.sub(r"[.,]", "", int_part)
        num = f"{int_part or '0'}.{frac}"
    else:
        num = re.sub(r"[.,]", "", num)
    try:
        val = Decimal(num)
    except InvalidOperation:
        return None
    if tonnes:
        val *= 1000
    elif _LB_RE.search(v):
        val *= Decimal("0.45359237")
    val = val.quantize(Decimal("0.001")).normalize()
    return format(val, "f")
