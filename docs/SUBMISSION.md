# SDOC submission material

Fill in the bracketed items (video link) before submitting.

## 1. Project description (paste into the submission form)

**Name:** SDOC, Shipping Document Verification

**Purpose:** Automatically triage a shipping-operations inbox and verify that a
Shipping Instruction (SI) and its draft Bill of Lading (BL) agree, so staff only
spend time on real problems.

**Problem:** Documentation teams manually compare SI and draft BL line by line
(shipper, consignee, notify party, ports, container count, gross weight) across
hundreds of emails and four file formats (txt, PDF, Word, Excel), including
scans. Typos and mismatches that slip through cause amended BLs, delays and cost.

**Solution:** SDOC classifies every email into one of five categories and, for
comparison requests, reads both documents, compares the seven fields and returns
OK, MISMATCH (naming the exact fields) or NEEDS_REVIEW (unreadable file, wrong
document type, missing attachment, blank field). AI reads the documents; plain,
auditable code makes the decision.

**Extras:** a dashboard with time-saved estimates, a review queue, a simulated Outbox that drafts a reply to every sender (uncertain cases are held for a person; nothing is really emailed), a Playground for breaking a document and watching the verdict change, an audit trail for every field, and optional AI second opinion and reply polishing that can never change a verdict.

## 2. Slide deck outline (about 8 slides)

1. **Title:** SDOC, name, team, one-line pitch.
2. **Problem:** manual SI vs BL checking; volume, formats, cost of a missed error.
3. **Solution overview:** inbox in, category + verdict out; three outcomes.
4. **Technical architecture:** diagram: Inbox loader -> classifier -> document
   reader (Claude vision API, rule-based fallback) -> normalizer -> deterministic
   comparator -> submission JSON / web app. Hosted on Streamlit Community Cloud.
5. **Key design decision:** AI reads, code decides. Exact defect fields carry half
   the score, so a language model is never allowed to "reason away" a discrepancy.
   Rule-based fallback keeps the system working with no API key.
6. **Implementation details:** label aliasing ("Load Port" = "Port of Loading"),
   value normalization (commas, port codes, "6 x 40'HC"), font-based PDF parsing,
   OCR for scans, escalate-don't-guess policy.
7. **Challenges:** label variants across formats; PDF column overlap corrupting
   text; scanned documents; the AI returning inconsistent port strings (fixed by
   tightening the prompt); an invisible trailing space in the API key.
8. **Results and future roadmap:** perfect score with the rule-based reader on
   the organizer's scoring script (two datasets). Roadmap: more document types
   (invoice, packing list), more fields, carrier-system integration, human-review
   queue with one-click approve, audit log.

## 3. Demo video script (target 4:00, hard limit 5:00)

| Time | Show | Say |
|---|---|---|
| 0:00 | Title slide | Who we are; the problem in one sentence. |
| 0:30 | Architecture slide | AI reads, plain code decides, and why. |
| 1:15 | Live app, "Upload" tab | Upload a matching SI and BL: green OK. |
| 2:00 | Same tab, mismatched pair | Red MISMATCH naming the exact fields. |
| 2:45 | "Sample inbox" tab | Pick a scan / wrong document / missing attachment: NEEDS REVIEW with reason. |
| 3:30 | README / results | Scoring result, fallback, deployment. |
| 3:50 | Roadmap slide | Where this goes next; thanks. |

Record with any screen recorder, upload to YouTube as **Unlisted** or Public
(not Private), and keep it under 5 minutes (1 mark lost per 30 s over).

## 4. Submission checklist

- [x] Public GitHub repo: https://github.com/isaaclew1102-web/Averis-unemployed-bums
- [ ] Live deployed app (must open WITHOUT signing in): https://averis-unemployed-bums-yw82lbdvxstupvjeosomwc.streamlit.app/
- [ ] Demo video (YouTube, unlisted/public, max 5 min): [link]
- [ ] Slide deck / documentation
- [ ] Project description (section 1)
- [ ] `ground_truth.json` NOT in the repo (already in `.gitignore`)
- [ ] API key NOT in the repo (only in Streamlit Secrets)
