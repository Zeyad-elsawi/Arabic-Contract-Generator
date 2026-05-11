# ⚖️ Egyptian Arabic Contract Drafting Assistant

A Streamlit app that drafts, reviews, and exports professional Arabic contracts under Egyptian law. Built for lawyers to use as a drafting copilot — not as a replacement for legal review.

> النسخة العربية المختصرة في نهاية الملف.

---

## What it does

```
        ┌──────────────────────────────────────────────────────────────┐
        │                       User Inputs                            │
        │  Form fields  +  Arabic voice memo (Whisper Large v3)        │
        └─────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  RAG retrieval over ~70 Egyptian contract templates          │
        │  (BAAI/bge-m3 multilingual embeddings, FAISS persisted)      │
        └─────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  DRAFTER agent — Qwen3-32B on Groq, streamed JSON            │
        │  Egyptian Civil Code-aware system prompt, 8K output tokens   │
        └─────────────────────────┬────────────────────────────────────┘
                                  │  structured: parties, articles, ...
                                  ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  STRICT CRITIC — Llama-3.3-70B on Groq, JSON-mode             │
        │  Flags: missing clauses, one-sided obligations, vagueness,   │
        │  Civil-Code violations, formal requirements (شهر عقاري…),    │
        │  internal contradictions. Severity-rated, with civil-code    │
        │  article references.                                         │
        └─────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  Chat-based refinement (per-clause edits, streamed)          │
        └─────────────────────────┬────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────────────────┐
        │  Export: DOCX (RTL + Arabic font + signature block)          │
        │          PDF  (reshaped + bidi, A4)                          │
        │          Plain text + JSON backup                            │
        └──────────────────────────────────────────────────────────────┘
```

---

## Quickstart

### 1. Install dependencies

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

First run will download the `BAAI/bge-m3` embedding model (~2 GB). After that it's cached locally.

### 2. Add your Groq API key

Get a free key from https://console.groq.com/keys, then open
`.streamlit/secrets.toml` and replace the placeholder:

```toml
GROQ_API_KEY = "gsk_yourActualKeyHere"
```

The file is already in `.gitignore` — it will not be committed.

### 3. Run

```bash
streamlit run app.py
```

The first startup builds the FAISS index from all contract templates
(~30 seconds). Subsequent startups load the cached index in <1 second.

---

## Project layout

```
Contracts_writer/
├── app.py              ← Streamlit UI, page tabs, session state
├── config.py           ← Paths, model IDs, contract categories
├── llm.py              ← Groq client wrappers (chat + Whisper)
├── prompts.py          ← Egyptian-legal system prompts
├── schema.py           ← Pydantic models for structured contract & critique
├── agents.py           ← Drafter → Critic → Refiner pipeline
├── templates.py        ← .docx + legacy .doc loaders (pure Python)
├── rag.py              ← Arabic-aware chunking + FAISS retrieval
├── export.py           ← DOCX (RTL) + PDF + plain-text rendering
├── requirements.txt
├── .streamlit/
│   ├── secrets.toml    ← YOUR API KEY (gitignored)
│   └── config.toml     ← theme + server config
├── vector_db/          ← persisted FAISS index (auto-generated)
└── نماذج عقود/مصري - Copy/   ← Arabic contract templates (~70 files)
```

---

## Models used

| Role | Model | Why |
|---|---|---|
| Drafter | `qwen/qwen3-32b` (Groq) | Best free Arabic of the Groq lineup, fast |
| Strict critic | `llama-3.3-70b-versatile` (Groq) | Larger model, different family → better critique |
| Voice transcription | `whisper-large-v3` (Groq) | Excellent Arabic ASR, ~3 s for a 30 s clip |
| Embeddings | `BAAI/bge-m3` (local) | Multilingual, strong on Arabic legal text |

Change them in `config.py` if Groq retires a model.

---

## What the strict critic looks for

Configured via `prompts.CRITIC_SYSTEM`:

- **missing_clause** — no penalty clause, no force majeure, no dispute-resolution mechanism, no termination triggers
- **one_sided** — obligations on one party only
- **vague** — undefined amounts, open-ended dates, undefined terms
- **contradiction** — clauses that conflict with each other or with stated party data
- **civil_code_violation** — references Articles 135, 136, 217 of the Egyptian Civil Code (void clauses, immoral consideration, indemnity-from-gross-negligence)
- **formal_requirement** — no notarization in real-estate sales (Law 114/1946), missing witness requirements for gifts of real estate

Each red flag has a severity (`critical` / `high` / `medium` / `low`) and includes a suggested fix.

---

## Security

- API keys are read from `.streamlit/secrets.toml` (gitignored) or environment variables.
- Never paste keys in code, commits, issues, or chat with assistants.
- The old hardcoded Gemini key (`AIzaSyAx...`) from the previous version has been removed — rotate it on Google AI Studio if you haven't.

---

## Disclaimer

The output is AI-generated reference text. A qualified Egyptian lawyer must review every contract before it is signed, registered, or relied upon.

---

## نظرة عربية موجزة

تطبيق Streamlit يساعد المحامين على صياغة عقود مصرية بالعربية، يتكون من خطّ تنفيذ متعدد العملاء (Agent pipeline):

1. **الصياغة** عبر نموذج Qwen3-32B على منصة Groq، مع تغذية سياقية من ~٧٠ نموذج عقد مصري.
2. **المراجعة الصارمة** عبر نموذج Llama-3.3-70B، يكتشف البنود المفقودة والمخالفات لأحكام القانون المدني المصري.
3. **تعديل بالمحادثة**: تطلب التعديل بالعربية فيُعدَّل البند المعني فقط.
4. **إدخال صوتي** عبر Whisper Large v3 لتفريغ الشروط الخاصة.
5. **تصدير** إلى DOCX (مع ضبط الاتجاه من اليمين لليسار وخط عربي) و PDF ونص.

ضع مفتاح Groq في `.streamlit/secrets.toml` ثم شغّل:

```bash
streamlit run app.py
```

⚠️ المحتوى المولّد مرجعي فقط ولا يغني عن مراجعة محامٍ مختص.
