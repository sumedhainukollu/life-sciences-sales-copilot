# Life Sciences Sales Copilot

A RAG (Retrieval-Augmented Generation) agent that helps pharma/biotech sales
reps and MSLs prepare for HCP (healthcare provider) calls. It combines:

- **Live clinical trial data** pulled from the official [ClinicalTrials.gov API](https://clinicaltrials.gov/data-api/api)
- **Rep call notes** (from a CRM export, e.g. Veeva or Salesforce Life Sciences Cloud)
- **Claude** to draft a structured, source-grounded call prep sheet

This is the kind of AI feature Salesforce's Life Sciences Cloud doesn't do
well today: most CRM AI is generic ("summarize this note"), not fluent in
compound data, trial phases, and MSL workflows.

---

## How it works (architecture)

```
ClinicalTrials.gov API  ──┐
                           ├──> chunked text docs ──> embeddings ──> ChromaDB (local vector DB)
Rep notes CSV (CRM export)┘                                              │
                                                                          │ semantic search
                                                                          ▼
                                                            retrieved context (trials + notes)
                                                                          │
                                                                          ▼
                                                    Claude (Anthropic API) drafts the
                                                    structured HCP Call Prep Sheet
```

This is a genuine RAG pipeline — Claude never "makes up" trial data; it only
drafts using text that was actually retrieved from ClinicalTrials.gov or
your rep notes. That grounding is what makes the output usable (and
defensible) in a regulated industry.

---

## Step-by-step setup (beginner-friendly)

### 1. Install Python
You need Python 3.10 or newer. Check with:
```bash
python3 --version
```
If you don't have it, install from [python.org](https://www.python.org/downloads/).

### 2. Download/unzip this project
Put the `life-sciences-sales-copilot` folder somewhere on your computer, then
open a terminal and `cd` into it:
```bash
cd life-sciences-sales-copilot
```

### 3. Create a virtual environment (keeps dependencies isolated)
```bash
python3 -m venv venv
source venv/bin/activate        # on Mac/Linux
venv\Scripts\activate           # on Windows
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```
(First run will also download a small ~80MB embedding model automatically —
that's normal and only happens once.)

### 5. Get an Anthropic API key
- Go to https://console.anthropic.com/
- Create an account and generate an API key.

### 6. Set up your API key
```bash
cp .env.example .env
```
Open `.env` in any text editor and paste your key in place of the placeholder:
```
ANTHROPIC_API_KEY=sk-ant-your-real-key-here
```

### 7. Build the index (pulls real trial data + loads example rep notes)
```bash
python build_index.py --drug "pembrolizumab" --condition "non-small cell lung cancer"
```
This will:
- Call the ClinicalTrials.gov API for matching trials
- Load `data/rep_notes_example.csv`
- Embed everything and store it in a local `chroma_db/` folder

You should see output like:
```
Fetching trials for drug='pembrolizumab' condition='non-small cell lung cancer'...
Fetched 15 trials from ClinicalTrials.gov.
Indexed 15 documents into 'life_sciences_kb'.
Loading rep notes from data/rep_notes_example.csv...
Loaded 5 rep notes.
Indexed 5 documents into 'life_sciences_kb'.
Index build complete.
```

### 8. Run the app
```bash
streamlit run app.py
```
This opens a browser window. Fill in an HCP name, drug, and condition, and
click **Generate call prep sheet**.

### 9. (Optional) Try it from the command line instead of the UI
```bash
python -m src.generate_call_prep
```
This runs the example at the bottom of `src/generate_call_prep.py`.

---

## Using your own data

- **Different drug/condition:** just re-run `build_index.py` with new
  `--drug` / `--condition` flags — it adds to the index without duplicating.
- **Your own rep notes:** replace `data/rep_notes_example.csv` (or point
  `--notes` at a different file) with the same columns:
  `hcp_name, hcp_specialty, institution, date, drug, topic, note_text`
  — this is the shape of a typical CRM export, so mapping a real Veeva/
  Salesforce export into this format is usually a light pandas script.
- **Reset the index:** `python build_index.py --reset --drug "..." --condition "..."`

---

## Why this is a strong differentiator (for your pitch)

- **Domain-specific grounding, not generic summarization.** The retrieval
  layer is structured around trial phase, NCT ID, sponsor, and eligibility —
  the actual vocabulary a rep or MSL uses — not just "chat with your PDF."
- **Compliance-aware by design.** The system prompt (`src/prompts.py`)
  explicitly flags investigational/off-label content and forces an MLR
  (Medical/Legal/Regulatory) disclaimer on every output — a requirement
  general-purpose CRM AI assistants typically ignore.
- **Cites its sources.** Every generated bullet point should be traceable to
  either an NCT number or a specific rep note, which builds trust with
  reps and makes review by Medical/Legal much faster.
- **Extensible.** Swap ClinicalTrials.gov for an internal compound database,
  add PubMed ingestion, or plug into Veeva CRM's actual API to auto-pull
  notes instead of using a CSV — the RAG architecture doesn't change.

---

## Important compliance disclaimer

This is a prototype/demo. In a real pharma deployment:
- Content should never reach an HCP without going through your company's
  Medical/Legal/Regulatory (MLR) review process.
- Generated text must not imply off-label promotion of any approved product.
- Real patient data must never be included in rep notes used here — only
  aggregate HCP interaction notes, consistent with your company's data
  privacy and Sunshine Act reporting obligations.
- Treat this as a call-prep drafting aid for the rep's own use, not a
  source of approved marketing claims.

---

## Project structure

```
life-sciences-sales-copilot/
├── README.md
├── requirements.txt
├── .env.example
├── build_index.py            # CLI script: fetch + embed + store data
├── app.py                    # Streamlit UI
├── data/
│   └── rep_notes_example.csv # sample CRM-style rep notes
└── src/
    ├── ingest_trials.py      # ClinicalTrials.gov API v2 client
    ├── ingest_notes.py       # CSV rep-notes loader
    ├── vectorstore.py        # ChromaDB + embeddings (the "R" in RAG)
    ├── prompts.py            # system + user prompt templates
    └── generate_call_prep.py # retrieval + Claude generation (the "G" in RAG)
```
