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

**Measured, not estimated:** run against a real key and the organizer's
official scorer, the AI reader also scores a perfect **1.0000** on all 520
emails — 240 real Claude calls, 200/200 comparisons decided exactly right,
plus all 20 edge cases correctly escalated, 46/46 defects caught, zero false
alarms, zero wrong escalations. The free
rule-based reader, which needs no API key at all, independently scores the
same perfect **1.0000**. Two different readers, one deterministic decision
engine, the same perfect result — that's the headline: the AI reader is fully
validated, not just claimed to work, and the rule-based path proves the system
still works at zero API cost if a visitor never unlocks AI.

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
8. **Results and validation:** both readers score a perfect 1.0000 on the
   organizer's scorer, 520 emails — the AI reader measured with a real key (240
   live Claude calls, 220/220 comparisons exact, 46/46 defects caught), the
   rule-based reader as the zero-API-cost path. Say the testing explicitly: the
   organizer's scorer, four independently generated datasets, 26 unit tests, 43
   browser checks.
9. **Roadmap — for the Final Round:** more document types, more fields, carrier
   and mailbox integration, one-click human review with an audit log. Framed
   explicitly as "if we advance, here's the extension," per the brief's
   requirement that the Final Round build on the Preliminary one.

## 3. Demo video script (target 4:40, hard limit 5:00)

**Priority order:** (1) AI mode working live on camera — "Working Core
Prototype" is 25 of 100 points, the single biggest line item, and it means
the AI reader, not the fallback; (2) say the validation numbers out loud —
"Technical Feasibility & Validation" is 15 points and is lost by staying
implicit; (3) everything else.

This is built from the team's actual screen recording, re-cut to this order —
trim and re-sequence the recorded clips to match the Show column below
rather than using the raw recording's original order. Three moments use a
slide from `docs/DocHarbor_slides.pptx` instead of live app footage (noted in
the Show column); everything else is the live app at
averis-unemployed-bums-yw82lbdvxstupvjeosomwc.streamlit.app.

| Time | Show | Say |
|---|---|---|
| 0:00 | **Slide 1 (Title)** | "Hi, we're Unemployed Bums. This is DocHarbor, a shipping document verification system, for the Averis x Monash Hackathon." |
| 0:12 | Dashboard opening (stat cards, donut, categories) | "Shipping teams manually check a Shipping Instruction against a draft Bill of Lading across seven fields, by eye, hundreds of times a day. One missed typo means an amended Bill of Lading, delays and cost." |
| 0:28 | Quick theme flip: dark → light → back (~3-4 sec) | *(no line — silent flourish)* |
| 0:32 | Sidebar: type the AI access code, toggle "Read documents with AI" ON | "Here's the core of it, working live — I'm switching on our AI reader now." |
| 0:47 | Badge changes to "AI reader on"; Compare Documents tab, run "Everything matches" | "Watch this: DocHarbor sends the document to Claude, which reads it, and this exact field table and verdict come back — live, not a script." |
| 1:12 | Point at the caption under the verdict | "That line is the proof. It only says that when AI actually did the reading — the verdict itself never comes from the model." |
| 1:27 | Open the Audit trail expander | "Every field's decision is auditable: the value as read, the normalised value, and the exact rule that made the call. A language model never gets a vote on whether a discrepancy is real." |
| 1:47 | Click "Open in my email app" | "This isn't a mockup — it hands off to your actual email client with the reply already drafted." |
| 2:02 | "Scanned image" sample -> NEEDS REVIEW | "It doesn't guess. A scan, a wrong document, a blank field — all escalated with a clear reason." |
| 2:17 | Click "Ask AI for a second opinion" | "For cases sent to a human, AI can offer a second opinion — advisory only, it can never override the verdict above it." |
| 2:37 | Talk over Inbox Browser | "We checked this against the organizer's official scorer, then separately against four independently generated datasets to rule out overfitting. It's backed by 26 automated unit tests and 43 real-browser checks." |
| 2:57 | **Slide 10 (Validation results)** | "Measured for real: a perfect 1.0000 with the AI reader live — 240 Claude calls, 200 out of 200 comparisons decided exactly right, plus all 20 edge cases correctly escalated. The free rule-based reader scores that same perfect 1.0000 with zero API cost — the AI mode is a validated upgrade, not a guess. You might ask — if the free reader already scores perfectly, why bother with AI? Because that perfect score is on label variants we already knew about. AI is the part that generalizes to the messy, unpredictable documents we haven't seen yet — which is exactly the challenge the Final Round roadmap is built around." |
| 3:42 | Outbox tab: "Simulation mode" banner, toggle "Hold mismatch replies for approval" | "The Outbox shows exactly what would be sent — nothing really is. Mismatch replies can be held back for a person to approve first." |
| 4:07 | Playground: edit the Shipper field live | "Change one letter, and the real decision engine reacts instantly — this is the same engine deciding, live." |
| 4:27 | **Slide 11 (Roadmap)** | "This is our Preliminary Round entry. For the Final Round, we'd add more document types, more fields, and a real mailbox connection. Thanks for watching." |

Recording tips:
- The theme flip at 0:28 and the walkthrough are cut from the two clips the
  team already recorded — trim and splice them to match the Show column above.
- Zoom the browser to ~110% before recording so on-screen text reads clearly.
- Upload to YouTube as Unlisted or Public (never Private), stay under 5:00.

## 4. Submission checklist

- [x] Public GitHub repo: https://github.com/isaaclew1102-web/Averis-unemployed-bums
- [x] Live deployed app (opens WITHOUT signing in, verified): https://averis-unemployed-bums-yw82lbdvxstupvjeosomwc.streamlit.app/
- [x] **Ran `evaluate_ai.py` for real** — the true `ai_only` score from
      `score_cli.py` is a perfect **1.0000** (240 live Claude calls, 200/200
      comparisons exact, plus all 20 edge cases correctly escalated, 46/46
      defects caught, 0 false alarms, 0 wrong escalations). Matches the
      rule-based reader's 1.0000 exactly.
- [ ] Demo video (YouTube, unlisted/public, max 5 min) — script above shows AI
      mode working live, per the rubric's biggest line item: [link]
- [x] Slide deck: `docs/DocHarbor_slides.pptx` — Results slide now has the real
      AI score, not a placeholder
- [x] Project description (section 1) — real AI score filled in
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
