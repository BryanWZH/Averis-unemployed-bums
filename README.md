# SDOC Verification Pipeline

Reads a shipping-ops inbox, classifies every email, and for document-comparison
requests, checks a Shipping Instruction (SI) against a draft Bill of Lading (BL)
across 7 fields — flagging mismatches, or escalating to a human when it can't
tell confidently.

## What's in this folder

| File | What it does |
|---|---|
| `pipeline.py` | Runs everything end to end, writes `submission.json` |
| `classify.py` | Sorts each email into one of 5 categories |
| `extract.py`  | Rule-based document reader (txt/pdf/docx/xlsx) + OCR fallback for scans |
| `ai_extract.py` | AI-powered document reader — used automatically once an API key is set |
| `normalize.py` | Shared field-label matching ("Load Port" = "Port of Loading") and value cleanup |
| `loader.py` | Reads the inbox/attachments from disk (or an HTTP server) |
| `inbox/`, `attachments/` | The test dataset |
| `app.py` | Web app (Streamlit): inbox dashboard, review queue, document comparison with a visual diff, draft replies |
| `report.py` | Diffs, draft-reply emails, downloadable reports and inbox analytics used by the app |
| `tests/` | Regression tests: `python tests/test_normalize.py`, `tests/test_report.py`, `tests/test_classify.py` |
| `score_cli.py` | Scores a `submission.json` against a ground-truth file |
| `packages.txt` | System packages (Tesseract, Poppler) installed on Streamlit Cloud |
| `docs/` | Project description, slide outline and demo-video script |
| `sample_submission.json` | The required output shape |

## Setup

1. Install Python 3.10 or newer.
2. Install the Python packages:
   ```
   pip install -r requirements.txt
   ```
3. Two things are also needed at the operating-system level (not pip) for
   reading scanned PDFs — most systems don't have these by default:
   - **Tesseract OCR** — Mac: `brew install tesseract` · Ubuntu/Debian: `sudo apt install tesseract-ocr` · Windows: install from https://github.com/UB-Mannheim/tesseract/wiki
   - **Poppler** (PDF rendering) — Mac: `brew install poppler` · Ubuntu/Debian: `sudo apt install poppler-utils` · Windows: https://github.com/oschwartz10612/poppler-windows
4. (Optional — turns on AI-based document reading) Set your Anthropic API key
   as an environment variable:
   - Mac/Linux (Terminal): `export ANTHROPIC_API_KEY="paste-your-key-here"`
   - Windows (PowerShell): `$env:ANTHROPIC_API_KEY="paste-your-key-here"`

   **Without this set, the pipeline automatically falls back to the rule-based
   reader instead — nothing breaks either way.** This lets you test the pipeline
   immediately, before the key is ready, and confirms the AI reader turned on
   correctly once it is.

## Run it

```
python3 pipeline.py . submission.json
```

This reads every email in `inbox/`, classifies it, and for comparison emails,
compares the SI against the BL — writing results to `submission.json`.

## Features

- **Dashboard** of the whole inbox: outcomes, most common defects, reasons for escalation, CSV / `submission.json` export
- **Review queue** of every case that needs a human, with the reason and next step
- **Visual diff** highlighting the exact characters that differ between SI and BL
- **Audit trail** per field: value as read, normalised value, rule applied
- **Draft reply** to the sender, and a downloadable Markdown report per case
- **Batch mode**: upload many SI/BL files at once, auto-paired by file name

## Try it in the browser

```
streamlit run app.py
```

Opens a page where you can upload an SI and a draft BL, or pick any email from
the sample inbox, and see the field-by-field result.

## Deploy (Streamlit Community Cloud)

1. Push this folder to a public GitHub repository.
2. On https://share.streamlit.io choose **New app**, pick the repo, and set the
   main file to `app.py`.
3. Under **Advanced settings > Secrets**, paste
   `ANTHROPIC_API_KEY = "your-key"` (see `.streamlit/secrets.toml.example`).
   Without it the app still works, using the rule-based reader.

`packages.txt` and `requirements.txt` are picked up automatically.

## Check how it did

If you have `ground_truth.json` (organizer-side only):
```
python3 score_cli.py submission.json --ground-truth path/to/ground_truth.json
```

Otherwise, submit `submission.json` through the hackathon's official self-eval
endpoint (see the participant bundle's own README for that).

## Security note

Never commit the API key to GitHub or paste it in chat/Slack. Set it as an
environment variable only, as shown above.

## Working without spending API credit

AI reading is used only when `ANTHROPIC_API_KEY` is set. To be certain it is
never used (for example while developing), set `SDOC_NO_AI=1`; the free
rule-based reader is used even if a key is present:

- PowerShell: `$env:SDOC_NO_AI="1"`
- Mac/Linux: `export SDOC_NO_AI=1`
