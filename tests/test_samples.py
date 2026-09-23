"""Every sample must produce exactly the result it promises.
Run with: python tests/test_samples.py"""
import os
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)
import pipeline  # noqa: E402
import samples  # noqa: E402


def test_each_sample_gives_its_promised_result():
    for s in samples.SAMPLES:
        si_b, si_n, bl_b, bl_n = samples.load(s, ROOT)
        res, _, _ = pipeline.compare_documents(si_b, si_n, bl_b, bl_n, use_ai=False)
        assert (res["status"], res["review_reason"]) == (s["status"], s["reason"]), (s["id"], res)


def test_samples_cover_every_outcome():
    assert {s["status"] for s in samples.SAMPLES} == {"OK", "MISMATCH", "NEEDS_REVIEW"}
    assert {s["reason"] for s in samples.SAMPLES if s["reason"]} == {"missing_value", "wrong_doc_type", "unreadable"}


if __name__ == "__main__":
    test_each_sample_gives_its_promised_result()
    test_samples_cover_every_outcome()
    print("ok")
