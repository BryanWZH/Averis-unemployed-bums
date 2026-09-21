# DocHarbor submission material

## Competition context

This is **Averis x Monash Hackathon 2026**, and it runs in two rounds. What we're
submitting now is the **Preliminary Round** only — if we advance, the **Final
Round** must be "an extension and improvement" of this entry. So: don't talk
about this submission as if it's the finish line. The roadmap in the slides and
the video should be framed as what we'd build *for the Final Round*, not a vague
someday list.

- **Submission form:** https://forms.gle/XdfpiUEQDXZ6bdzi9
- **Deadline:** 22 Sept 2026, 12:00 PM

## The rubric (Preliminary Round, 100 pts) — and what it means for us

| Category | Points | What it rewards |
|---|---|---|
| Working Core Prototype | **25** (the single biggest line item) | The main technical idea working end-to-end |
| System Design & Architecture | 15 | The inbox -> classify -> read -> compare -> decide pipeline |
| Technology Integration | 15 | How the AI reader, OCR fallback, and the web app fit together |
| Technical Feasibility & Validation | 15 | Evidence of testing, not just a claim |
| Problem Statement Understanding | 10 | The use case, stated clearly |
| Innovation & Solution Approach | 10 | "AI reads, code decides" as the actual differentiator |
| Practical Value & Potential | 10 | Where this goes — tied to the Final Round |

Two things follow directly from this:

1. **"Working Core Prototype" is 25 of 100 points, and it explicitly means the
   main technical idea working live** — that's the AI reader, not the rule-based
   fallback. **The demo video must show AI mode actively working: enter the
   access code on camera, switch "Read documents with AI" on, and let a real AI
   read happen on screen.** The rule-based path is the safety net story, not
   the prototype the video leads with.
2. **"Technical Feasibility & Validation" (15 pts) rewards evidence of testing
   that is said out loud**, not left implicit. We have the evidence — the
   organizer's scorer, four independently generated datasets, 26 automated unit
   tests across 5 files, and 43 real-browser UI checks — but until now it wasn't
   stated anywhere in the script or the slides. It is now (see section 3).

## 1. Project description (paste into the submission form)

**Name:** DocHarbor, Shipping Document Verification

**Purpose:** Automatically triage a shipping-operations inbox and verify that a
Shipping Instruction (SI) and its draft Bill of Lading (BL) agree, so staff only
spend time on real problems.

**Problem:** Documentation teams manually compare SI and draft BL line by line
(shipper, consignee, notify party, ports, container count, gross weight) across
hundreds of emails and four file formats (txt, PDF, Word, Excel), including
scans. Typos and mismatches that slip through cause amended BLs, delays and cost.

**Solution and the innovation behind it — "AI reads, code decides":** DocHarbor
classifies every email into one of five categories and, for comparison requests,
reads both documents, compares the seven fields and returns OK, MISMATCH (naming
the exact fields) or NEEDS_REVIEW (unreadable file, wrong document type, missing
attachment, blank field). The core design decision, and our answer to "why is
this different from just asking an LLM to compare two documents": **an AI is
good at reading messy documents and bad at being trusted with a verdict it could
talk itself out of, so we split the job.** AI (optionally) does the reading;
plain, deterministic, auditable code does every comparison and every decision.
A language model never gets a vote on whether a discrepancy is real.

**[FILL IN AFTER RUNNING evaluate_ai.py]** — **AI-reader accuracy:** \_\_\_\_ on
the organizer's scorer (520 emails). **Rule-based accuracy:** a perfect
**1.0000** — this is the free-tier fallback result, and what's live in the app
by default with no API key. Lead the form and the video with the AI number once
it's measured; keep the 1.0000 as the "works with zero API cost" story, not the
headline.

**Where AI fits in, and where it deliberately doesn't:** by default DocHarbor
reads every document with free, rule-based parsing (txt/PDF/Word/Excel, plus OCR
for scans) — no API key needed. AI is an optional upgrade on top of that that a
visitor can switch on (enter the access code, toggle "Read documents with AI")
to see four things: (1) **AI document reading** — Claude reads the same seven
fields, including scans an OCR pass can't, and the exact same deterministic code
still makes the OK/MISMATCH/NEEDS_REVIEW call — the AI only ever supplies the
reading, never the verdict; (2) **cross-check** — the AI and rule-based readers
both read every document, and any field they disagree on sends the case to a
human instead of picking a side; (3) **AI second opinion** — on a case already
escalated to a human, the AI can offer an advisory read of its own, shown
separately and never allowed to change the verdict above it; (4) **AI reply
polish** — reword a drafted reply to sound more natural, guarded so the rewrite
is discarded outright if it changes a name, a number, or any other fact.

**Validation:** checked against the organizer's official scorer, and separately
against four independently generated datasets to rule out overfitting to one
sample. Backed by 26 automated unit tests across 5 files (normalization,
classification, the AI safety guards, the outbox logic) plus 43 real-browser UI
checks confirming the interface itself works, not just the code behind it.

**Extras:** a dashboard with time-saved estimates, a review queue, a simulated
Outbox that drafts a reply to every sender (uncertain cases are held for a
person; nothing is really emailed), a Playground for breaking a document and
watching the verdict change, and an audit trail for every field.

**For the Final Round, if we advance:** more document types (invoice, packing
list, certificate of origin), more fields (vessel, voyage, cargo description,
HS code), a real mailbox connection instead of the simulated Outbox, and
one-click human review with an audit log. This submission is the foundation for
that, not the finished product.

## 2. Slide deck outline (about 9 slides)

1. **Title:** DocHarbor, name, team, one-line pitch.
2. **Problem:** manual SI vs BL checking; volume, formats, cost of a missed error.
3. **Solution overview:** inbox in, category + verdict out; three outcomes.
4. **Technical architecture:** diagram: Inbox loader -> classifier -> document
   reader (Claude vision API, rule-based fallback) -> normalizer -> deterministic
   comparator -> submission JSON / web app. Hosted on Streamlit Community Cloud.
5. **Key design decision / the innovation:** AI reads, code decides — say
   explicitly that this *is* our answer to "what's innovative here," not just an
   architecture footnote. Exact defect fields carry half the score, so a
   language model is never allowed to "reason away" a discrepancy. Rule-based
   fallback keeps the system working with no API key.
6. **Implementation details:** label aliasing ("Load Port" = "Port of Loading"),
   value normalization (commas, port codes, "6 x 40'HC"), font-based PDF parsing,
   OCR for scans, escalate-don't-guess policy.
7. **Challenges:** label variants across formats; PDF column overlap corrupting
   text; scanned documents; the AI returning inconsistent port strings (fixed by
   tightening the prompt); an invisible trailing space in the API key.
8. **Results and validation:** lead with the AI-reader score once measured
   (organizer's scorer, 520 emails); the rule-based reader's perfect 1.0000 as
   the zero-API-cost fallback story. Say the testing explicitly: the organizer's
   scorer, four independently generated datasets, 26 unit tests, 43 browser
   checks.
9. **Roadmap — for the Final Round:** more document types, more fields, carrier
   and mailbox integration, one-click human review with an audit log. Framed
   explicitly as "if we advance, here's the extension," per the brief's
   requirement that the Final Round build on the Preliminary one.

## 3. Demo video script (target 4:40, hard limit 5:00)

**Priority order, since the rubric weights this:** (1) AI mode working live on
camera — "Working Core Prototype" is 25 of 100 points, the single biggest line
item, and it means the AI reader, not the fallback; (2) say the validation
numbers out loud — "Technical Feasibility & Validation" is 15 points and is
lost by staying implicit; (3) everything else.

Read the "Say" column roughly as written — it's timed to fit. Everything in
"Show" is the live app at
averis-unemployed-bums-yw82lbdvxstupvjeosomwc.streamlit.app, except the title
and roadmap beats, which can be a slide or just you talking over the DocHarbor
header. **Test this entire run-through once before recording** — confirm the
access code and "Read documents with AI" actually work on the live site first
(see the checklist item below); don't discover a problem while filming.

| Time | Show | Say |
|---|---|---|
| 0:00 | Title slide / app header | "Hi, we're [team name]. This is DocHarbor, a shipping document verification system, for the Averis x Monash Hackathon. Shipping teams manually check a Shipping Instruction against a draft Bill of Lading across seven fields, by eye, hundreds of times a day. One missed typo means an amended Bill of Lading, delays and cost." |
| 0:20 | Dashboard tab | "DocHarbor sorts every email into one of five categories, and every document comparison gets a clear verdict: OK, MISMATCH with the exact fields named, or NEEDS REVIEW when something can't be trusted." |
| 0:40 | Sidebar: type the AI access code, toggle "Read documents with AI" ON | "Here's the core of it, working live. This is our AI reader — I'm entering the access code and switching it on now." |
| 1:00 | Compare documents tab -> a sample, with AI reading ON, watch it actually read and decide | "Watch this: DocHarbor sends the real document to Claude, which reads it, and this exact field table and verdict come back — read by AI, decided by deterministic code underneath, live, not a script." |
| 1:25 | Point at the small caption right under the verdict badge | "That line right there — 'Read with AI, Claude' — is the proof. It only says that when AI actually did the reading; switch AI off and it says 'rule-based reader' instead." |
| 1:35 | Point at the field table + open "Audit trail" expander | "That split — AI reads, code decides — is the actual innovation here, not just an architecture note. A language model never gets a vote on whether a discrepancy is real. This audit trail shows the value as read, the cleaned-up value that was compared, and the rule that made the call." |
| 2:00 | Compare documents -> "Scanned image" sample -> "Ask AI for a second opinion" | "For cases sent to a human, like an unreadable scan, AI can offer a second opinion. It's advisory only — it can never change the verdict above it." |
| 2:20 | Open "Draft reply", press "Polish wording with AI" | "Every reply is drafted automatically, and AI can optionally reword it — guarded so that if it changes a number or a name, the rewrite is thrown away and the original wording is kept." |
| 2:40 | Just talk, over the dashboard or a slide | "We didn't just claim this works — we checked it against the organizer's official scorer, then separately against four independently generated datasets to rule out overfitting to one sample. It's backed by 26 automated unit tests and 43 real-browser checks of the interface itself." |
| 3:00 | Results slide / dashboard KPI tiles | "[SAY THE REAL evaluate_ai.py NUMBER HERE once measured] on the AI reader. The free rule-based reader — no API key needed — scores a perfect 1.0000, so DocHarbor works at zero API cost by default, and the AI mode you just saw is the upgrade on top." |
| 3:25 | Outbox tab: toggle hold, press "Process the inbox" | "The Outbox simulates replying to every sender — OK and mismatch replies go out automatically, anything uncertain is held for a person. No real email is ever sent; that's simulated on purpose." |
| 3:50 | Playground tab: pick a sample, press "Weight" or "Name typo" | "The Playground lets you break a document on purpose and watch the real decision engine react instantly — the same engine deciding, live." |
| 4:10 | Roadmap slide | "This is our Preliminary Round entry. For the Final Round, if we advance, we'd add more document types, more fields, and a real mailbox connection instead of a simulation. Thanks for watching." |

Recording tips:
- Screen-record the live site in a real browser (not the code). Zoom the browser to ~110%
  so text reads clearly on video.
- Show both light and dark theme at least once if you have time — it's a design highlight,
  but only after the AI-mode beat above; don't let it push that out of the video.
- Record with any screen recorder (Windows: Xbox Game Bar, Win+G), upload to YouTube as
  **Unlisted** or Public (never Private, judges can't open it), and stay under 5 minutes —
  the brief says marks are lost for going over.

## 4. Submission checklist

- [x] Public GitHub repo: https://github.com/isaaclew1102-web/Averis-unemployed-bums
- [x] Live deployed app (opens WITHOUT signing in, verified): https://averis-unemployed-bums-yw82lbdvxstupvjeosomwc.streamlit.app/
- [ ] **Run `evaluate_ai.py` for real, get the true `ai_only` score from `score_cli.py`**
      — do this *before* recording, both because the video needs the real number
      and because it's the dry run that confirms AI mode actually works live
      before you're on camera. Commands are below.
- [ ] Demo video (YouTube, unlisted/public, max 5 min) — script above shows AI
      mode working live, per the rubric's biggest line item: [link]
- [x] Slide deck: `docs/DocHarbor_slides.pptx` — still needs slide 8/9 updated
      once the real AI score is in (see section 2)
- [x] Project description (section 1) — has one blank left for the real AI score
- [x] `ground_truth.json` NOT in the repo (in `.gitignore`, confirmed absent)
- [x] API key NOT in the repo (only in Streamlit Secrets)
- [ ] Notes for judges — paste into the submission form only, never into this repo
      (the AI access code goes here; Claude has it and will remind you, but it is
      deliberately not written down in any tracked file)
- [ ] Submit via the actual form: https://forms.gle/XdfpiUEQDXZ6bdzi9

### Running the real AI evaluation

Cost check already done: only 124 of the 520 emails' comparisons need a real
document read (the rest resolve with no attachment), which is 248 document
reads total, and the cross-check pass reuses the same cached reads for free.
Estimated cost for the full run: roughly $1.50-$2.00. Run these in your own
terminal (not pasted into chat):

```powershell
cd "c:\Users\User\Documents\Projects\AVERIS HACK\sdoc-pipeline\sdoc"
$env:ANTHROPIC_API_KEY = "sk-ant-...your key..."
python evaluate_ai.py . --truth "..\..\sdoc-hackathon-docker\data_v2\ground_truth.json"
```

then:

```powershell
cd "c:\Users\User\Documents\Projects\AVERIS HACK\sdoc-hackathon-docker\server"
$env:PYTHONIOENCODING = "utf-8"
python score_cli.py "..\..\sdoc-pipeline\sdoc\submission_ai_only.json"
```

Paste both console outputs back (no key in either) and the real number goes
into the form text, the slides, and the video script's 3:00 beat.
