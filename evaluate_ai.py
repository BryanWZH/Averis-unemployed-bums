"""One paid run that measures everything about the AI reader.

    python evaluate_ai.py [data_dir] --truth path/to/ground_truth.json [--limit N]

Needs ANTHROPIC_API_KEY. Each document is read by the AI ONCE and saved to
.ai_cache/, so re-running (or changing the checks) costs nothing more. From
those reads it builds two submissions and compares them with the free
rule-based reader:

  * ai_only     - AI reads, deterministic code decides (scans still go to a human)
  * cross_check - as above, but any field the AI and rule-based readers
                  disagree on sends the case to a human

and reports, against the ground truth, how many decisions each got right, how
many real defects each caught, and how many clean cases each wrongly escalated.
Writes submission_ai_only.json and submission_cross_check.json for the
official scorer.
"""
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import ai_extract
import classify
import extract
import pipeline
from loader import Inbox

CACHE = Path(".ai_cache")


def cached_reader(real_reader, counter):
    """Wrap an AI reader so each distinct document is only ever read once."""
    CACHE.mkdir(exist_ok=True)

    def read(data, name):
        key = hashlib.sha1(data).hexdigest() + "_" + os.path.basename(name)
        f = CACHE / (key + ".json")
        if f.exists():
            d = json.loads(f.read_text(encoding="utf-8"))
        else:
            counter["calls"] += 1
            r = real_reader(data, name)
            d = {"readable": r.readable, "wrong_doc_type": r.wrong_doc_type,
                 "title": r.title, "fields": r.fields, "why": r.unreadable_reason}
            if r.readable or r.unreadable_reason == "empty_file":   # never cache a failed API call
                f.write_text(json.dumps(d), encoding="utf-8")
        out = extract.ExtractResult()
        out.readable, out.wrong_doc_type = d["readable"], d["wrong_doc_type"]
        out.title, out.fields, out.unreadable_reason = d["title"], d["fields"], d.get("why")
        return out
    return read


def build(inbox, emails, cross_check):
    sub = {}
    for email in emails:
        atts = email.get("attachments", []) or []
        category, _ = classify.classify(email, has_attachments=bool(atts))
        si, bl = pipeline._pick_si_bl(atts) if len(atts) >= 2 else (None, None)
        if category == "BL_COMPARISON" and si and bl:
            res, _, _ = pipeline.compare_documents(
                inbox.read_bytes(si), si, inbox.read_bytes(bl), bl, use_ai=True, cross_check=cross_check)
        elif category == "BL_COMPARISON":
            res = pipeline.decide_comparison(email, inbox)
        else:
            res = pipeline._empty_result("OK")
        sub[email["email_id"]] = {"category": category, "status": res["status"],
                                  "review_reason": res["review_reason"], "has_defect": res["status"] == "MISMATCH",
                                  "defect_fields": res["defect_fields"]}
    return sub


def summarize(name, sub, truth):
    total = sum(1 for k in truth if truth[k]["category"] == "BL_COMPARISON")
    exact = caught = defects = false_esc = missed_esc = false_alarm = 0
    for k, t in truth.items():
        if t["category"] != "BL_COMPARISON":
            continue
        s = sub[k]
        same = (s["status"], s["review_reason"], sorted(s["defect_fields"])) == (
            t["status"], t["review_reason"], sorted(t["defect_fields"]))
        exact += same
        if t["status"] == "MISMATCH":
            defects += 1
            caught += s["status"] == "MISMATCH" and sorted(s["defect_fields"]) == sorted(t["defect_fields"])
        if t["status"] != "NEEDS_REVIEW" and s["status"] == "NEEDS_REVIEW":
            false_esc += 1
        if t["status"] == "NEEDS_REVIEW" and s["status"] != "NEEDS_REVIEW":
            missed_esc += 1
        if t["status"] == "OK" and s["status"] == "MISMATCH":
            false_alarm += 1
    print(f"\n{name}")
    print(f"  decisions exactly right      {exact}/{total}")
    print(f"  real defects caught exactly  {caught}/{defects}")
    print(f"  clean cases wrongly flagged as a mismatch {false_alarm}")
    print(f"  clean cases wrongly escalated to a human  {false_esc}")
    print(f"  cases that should escalate but did not {missed_esc}")
    return exact == total


def main(argv=None, reader=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir", nargs="?", default=".")
    ap.add_argument("--truth", required=True)
    ap.add_argument("--limit", type=int, default=None, help="only the first N emails (cheap test run)")
    args = ap.parse_args(argv)

    if reader is None:
        if not ai_extract.available():
            sys.exit("No API key detected (or SDOC_NO_AI is set). Set ANTHROPIC_API_KEY, unset SDOC_NO_AI, "
                     "and run again. Nothing was spent.")
        reader = ai_extract.ai_extract
    counter = {"calls": 0}
    ai_extract.ai_extract = cached_reader(reader, counter)

    inbox = Inbox(args.data_dir)
    emails = list(inbox)[: args.limit] if args.limit else list(inbox)
    truth = {k: v for k, v in json.loads(Path(args.truth).read_text(encoding="utf-8")).items()
             if k in {e["email_id"] for e in emails}}

    print(f"Reading {len(emails)} emails with the AI (cached reads are free)...")
    ai_only = build(inbox, emails, cross_check=False)
    crossed = build(inbox, emails, cross_check=True)      # served from the cache: no extra calls
    Path("submission_ai_only.json").write_text(json.dumps(ai_only, indent=2), encoding="utf-8")
    Path("submission_cross_check.json").write_text(json.dumps(crossed, indent=2), encoding="utf-8")
    print(f"New AI calls made this run: {counter['calls']}")

    ai_ok = summarize("AI reads, code decides", ai_only, truth)
    cc_ok = summarize("AI + rule-based cross-check", crossed, truth)
    print("\nWrote submission_ai_only.json and submission_cross_check.json.")
    print("Score them with the official scorer, then submit whichever is better.")
    return ai_ok, cc_ok


if __name__ == "__main__":
    main()
