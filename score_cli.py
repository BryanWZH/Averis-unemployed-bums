"""Score a submission against a ground-truth file.

    python3 score_cli.py submission.json --ground-truth ground_truth.json [--show-errors]

Both files map email_id -> {category, status, review_reason, has_defect,
defect_fields}. Only keys present in the ground truth are scored.
"""
import argparse
import json
from collections import Counter


def _load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score(sub, truth):
    total = len(truth)
    counts = Counter()
    errors = []
    for eid, t in truth.items():
        s = sub.get(eid)
        if s is None:
            counts["missing"] += 1
            errors.append((eid, "missing from submission", None, None))
            continue
        cat_ok = s.get("category") == t.get("category")
        status_ok = s.get("status") == t.get("status")
        reason_ok = s.get("review_reason") == t.get("review_reason")
        fields_ok = sorted(s.get("defect_fields") or []) == sorted(t.get("defect_fields") or [])
        counts["category"] += cat_ok
        counts["status"] += status_ok
        counts["review_reason"] += reason_ok
        counts["defect_fields"] += fields_ok
        if cat_ok and status_ok and reason_ok and fields_ok:
            counts["exact"] += 1
        else:
            errors.append((eid, "mismatch", s, t))
    return total, counts, errors


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("submission")
    ap.add_argument("--ground-truth", required=True)
    ap.add_argument("--show-errors", action="store_true")
    args = ap.parse_args()

    total, counts, errors = score(_load(args.submission), _load(args.ground_truth))
    if not total:
        print("Ground truth is empty.")
        return
    for key in ("category", "status", "review_reason", "defect_fields", "exact"):
        print(f"{key:14s} {counts[key]:4d}/{total}  ({100 * counts[key] / total:.1f}%)")
    if counts["missing"]:
        print(f"missing        {counts['missing']}")
    if args.show_errors:
        for eid, why, s, t in sorted(errors):
            print(f"\n{eid}: {why}")
            if s is not None:
                print("  got     ", s)
                print("  expected", t)


if __name__ == "__main__":
    main()
