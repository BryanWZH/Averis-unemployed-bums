# DocHarbor submission material

Fill in the bracketed items (video link) before submitting.

## 1. Project description (paste into the submission form)

**Name:** DocHarbor, Shipping Document Verification

**Purpose:** Automatically triage a shipping-operations inbox and verify that a
Shipping Instruction (SI) and its draft Bill of Lading (BL) agree, so staff only
spend time on real problems.

**Problem:** Documentation teams manually compare SI and draft BL line by line
(shipper, consignee, notify party, ports, container count, gross weight) across
hundreds of emails and four file formats (txt, PDF, Word, Excel), including
scans. Typos and mismatches that slip through cause amended BLs, delays and cost.

**Solution:** DocHarbor classifies every email into one of five categories and, for
comparison requests, reads both documents, compares the seven fields and returns
OK, MISMATCH (naming the exact fields) or NEEDS_REVIEW (unreadable file, wrong
document type, missing attachment, blank field). AI reads the documents; plain,
auditable code makes the decision.

**Where AI fits in, and where it deliberately doesn't:** by default DocHarbor reads
every document with free, rule-based parsing (txt/PDF/Word/Excel, plus OCR for
scans) — no API key needed, and it's what produced the submitted result: a
**perfect 1.0000** on the organizer's scorer across the 520-email dataset,
46/46 defects caught end to end. AI is an optional upgrade on top of that, off by default, that a
visitor can switch on to see four things: (1) **AI document reading** — Claude
reads the same seven fields, including scans an OCR pass can't, and the exact
same deterministic code still makes the OK/MISMATCH/NEEDS_REVIEW call — the AI
only ever supplies the reading, never the verdict; (2) **cross-check** — the AI
and rule-based readers both read every document, and any field they disagree
on sends the case to a human instead of picking a side; (3) **AI second
opinion** — on a case already escalated to a human, the AI can offer an
advisory read of its own, shown separately and never allowed to change the
verdict above it; (4) **AI reply polish** — reword a drafted reply to sound
more natural, guarded so the rewrite is discarded outright if it changes a
name, a number, or any other fact. In short: the free reader is what earned
the perfect score; AI is there to read harder documents and add a second set
of eyes, never to make or overrule a decision.

**Extras:** a dashboard with time-saved estimates, a review queue, a simulated Outbox that drafts a reply to every sender (uncertain cases are held for a person; nothing is really emailed), a Playground for breaking a document and watching the verdict change, and an audit trail for every field.

## 2. Slide deck outline (about 8 slides)

1. **Title:** DocHarbor, name, team, one-line pitch.
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

## 3. Demo video script (target 4:20, hard limit 5:00)

Read the "Say" column roughly as written — it's timed to fit. Everything in "Show" is the
live app at averis-unemployed-bums-yw82lbdvxstupvjeosomwc.streamlit.app, except the two
title/roadmap beats, which can be a slide or just you talking over the DocHarbor header.

| Time | Show | Say |
|---|---|---|
| 0:00 | Title slide / app header | "Hi, we're [team name]. This is DocHarbor, a shipping document verification system. Shipping teams manually check a Shipping Instruction against a draft Bill of Lading across seven fields, by eye, hundreds of times a day. One missed typo means an amended Bill of Lading, delays and cost. DocHarbor does that check automatically." |
| 0:25 | Dashboard tab | "Every email in the inbox gets sorted into one of five categories, and every document comparison gets a clear verdict: OK, MISMATCH with the exact fields named, or NEEDS REVIEW when something can't be trusted. On the 520-email test set that's 46 mismatches caught and 20 correctly escalated to a human — nothing guessed." |
| 0:55 | Scroll the Dashboard: donut, funnel, defect fields, "What this saves" | "The dashboard shows how the whole inbox was handled, where the defects are, and roughly how much manual checking this replaces." |
| 1:20 | Compare documents tab -> "Wrong weight and container count" sample | "Here's a real mismatch. DocHarbor compares all seven fields and shows exactly which ones differ, side by side." |
| 1:45 | Point at the field table + open "Audit trail" expander | "This audit trail shows the value as read from each document, the cleaned-up value that was actually compared, and the rule that made the call. Every verdict here comes from plain code, not a model's judgment." |
| 2:05 | Open "Draft reply", press "Polish wording with AI" | "A reply to the sender is drafted automatically. AI can optionally reword it to sound more natural — but it's guarded: if it changes a number or a name, the rewrite is thrown away and the original wording is kept instead." |
| 2:30 | Compare documents -> "Scanned image" sample -> "Ask AI for a second opinion" | "For cases sent to a human, like this unreadable scan, AI can offer a second opinion. It's advisory only — it can never change the verdict above it." |
| 2:55 | Outbox tab: toggle hold, press "Process the inbox" | "The Outbox simulates replying to every sender — OK and mismatch replies go out automatically, and anything uncertain is held for a person to check. No real email is ever sent; that's simulated on purpose." |
| 3:20 | Playground tab: pick "Everything matches", press "Weight" or "Name typo" | "The Playground lets you break a document on purpose — change a weight, a name, a port — and watch the real decision engine react instantly. This is the same engine deciding, live." |
| 3:45 | Sidebar: point at reader toggle / theme switch | "It works with no AI key at all, using a free rule-based reader that scores a perfect 1.0000 on the organizer's scorer. AI reading is optional, and off by default so it never spends API credit without asking." |
| 4:05 | Roadmap slide or just the app | "Next we'd add more document types, more fields, and a real mailbox connection. Thanks for watching." |

Recording tips:
- Screen-record the live site in a real browser (not the code). Zoom the browser to ~110%
  so text reads clearly on video.
- Show both light and dark theme at least once if you have time — it's a design highlight.
- Record with any screen recorder (Windows: Xbox Game Bar, Win+G), upload to YouTube as
  **Unlisted** or Public (never Private, judges can't open it), and stay under 5 minutes —
  the brief says marks are lost for going over.

## 4. Submission checklist

- [x] Public GitHub repo: https://github.com/isaaclew1102-web/Averis-unemployed-bums
- [x] Live deployed app (opens WITHOUT signing in, verified): https://averis-unemployed-bums-yw82lbdvxstupvjeosomwc.streamlit.app/
- [ ] Demo video (YouTube, unlisted/public, max 5 min): [link]
- [x] Slide deck: `docs/DocHarbor_slides.pptx` — open it once and check nothing overflows
- [x] Project description (section 1)
- [x] `ground_truth.json` NOT in the repo (in `.gitignore`, confirmed absent)
- [x] API key NOT in the repo (only in Streamlit Secrets)
- [ ] Notes for judges — paste into the submission form only, never into this repo
      (the AI access code goes here; Claude has it and will remind you, but it is
      deliberately not written down in any tracked file)
