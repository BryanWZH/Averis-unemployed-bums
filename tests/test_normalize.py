"""Run with: python -m pytest tests   (or: python tests/test_normalize.py)"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from normalize import normalize_value as n  # noqa: E402

SAME = [
    ("gross_weight_kg", "61,026 KG", "61,026.00 KG"),
    ("gross_weight_kg", "61,026.500 KG", "61026.5"),
    ("gross_weight_kg", "61.026,00 KGS", "61,026 KG"),
    ("gross_weight_kg", "61,026 KG", "61.026 MT"),
    ("gross_weight_kg", "61 MT", "61,000 KG"),
    ("gross_weight_kg", "1,234,567 KG", "1.234.567,00 KG"),
    ("container_count", "3 x 40'HC", "3"),
    ("container_count", "3 X 40'HC", "03 CONTAINERS"),
    ("container_count", "40'HC x 3", "3"),
    ("port_of_loading", "Nhava Sheva, India (INNSA)", "NHAVA SHEVA, INDIA"),
    ("consignee", "SAFQA  LIMITED", "Safqa Limited"),
]
DIFFERENT = [
    ("gross_weight_kg", "61,026 KG", "61,062 KG"),
    ("gross_weight_kg", "61,026 KG", "61,026.5 KG"),
    ("gross_weight_kg", "61,026 KG", "6,102 KG"),
    ("container_count", "3 x 40'HC", "4 x 40'HC"),
    ("container_count", "3 x 40'HC", "30"),
    ("consignee", "AL GURQ STATIONERY LLC", "AL GURG STATIONERY LLC"),
    ("port_of_discharge", "KOPER, SLOVENIA", "KOPER, ITALY"),
]


def test_equivalent_values_compare_equal():
    for field, a, b in SAME:
        assert n(field, a) == n(field, b), (field, a, b)


def test_real_differences_stay_different():
    for field, a, b in DIFFERENT:
        assert n(field, a) != n(field, b), (field, a, b)


if __name__ == "__main__":
    test_equivalent_values_compare_equal()
    test_real_differences_stay_different()
    print("ok")
