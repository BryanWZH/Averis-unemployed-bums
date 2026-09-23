"""Run with: python tests/test_classify.py

Hand-written emails in wording the synthetic generator never uses, so the
classifier is not just memorising the dataset's templates."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import classify  # noqa: E402

CASES = [
    ("BL_COMPARISON", "Please check draft BL vs SI - MSC booking 5544",
     "Hi team, attached is our SI and the draft bill of lading. Kindly verify everything matches.", False),
    ("BL_COMPARISON", "BL draft for approval", "Could you compare the shipping instruction with the BL draft?", False),
    ("BL_COMPARISON", "Docs check pls", "Attached SI + draft BL for review.", True),
    ("SI_REQUEST", "Need shipping instruction for booking 8812",
     "We have not received the SI for this shipment. Please send it ASAP so we can prepare the BL.", False),
    ("SI_REQUEST", "SI outstanding - vessel cut off Friday", "Please submit your shipping instructions.", False),
    ("INVOICE_QUERY", "Question about invoice INV-2291", "The amount on your invoice does not match the quotation.", False),
    ("INVOICE_QUERY", "Payment reminder - overdue", "Your invoice for terminal handling is overdue.", False),
    ("INVOICE_QUERY", "Demurrage charges dispute", "We would like to contest the demurrage billed on MSKU1234567.", False),
    ("GENERAL", "Vessel schedule update", "The vessel ETA has been revised. No action required.", False),
    ("GENERAL", "Holiday closure notice", "Our office will be closed on 25 December.", False),
    ("GENERAL", "Meeting tomorrow 10am", "Reminder about the operations sync tomorrow.", False),
    ("SPAM", "You have won a free iPhone!!!", "Click here to claim your prize now, limited time offer.", False),
    ("SPAM", "Urgent: verify your mailbox", "Your account will be suspended. Log in to confirm your password.", False),
    ("SPAM", "Cheap watches 80% discount", "Buy now, best price guaranteed.", False),
    ("SPAM", "Re: Invoice attached", "Open the file and enter your bank login to view.", False),
]


def test_handwritten_emails():
    wrong = [(g, classify.classify({"subject": s, "body": b}, has_attachments=a)[0], s)
             for g, s, b, a in CASES if classify.classify({"subject": s, "body": b}, has_attachments=a)[0] != g]
    assert not wrong, wrong


if __name__ == "__main__":
    test_handwritten_emails()
    print("ok")
