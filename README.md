# VerifAI

> **Check before you share.**

VerifAI is a claim verification platform designed to help users determine whether a viral news claim is supported by reliable external evidence.

The project focuses on a simple but important problem:

**Given a claim and a set of trusted evidence headlines, can we determine whether the exact claim is actually supported, contradicted, or cannot be established?**

VerifAI accepts screenshots and URLs, extracts the relevant claim, retrieves current news evidence, and analyzes the relationship between the claim and the retrieved evidence.

---

## Why VerifAI?

Viral misinformation is often consumed through screenshots, social-media posts, forwarded messages, and news snippets.

The problem is not always finding information.

The harder problem is determining whether the information being shared is actually true.

A headline mentioning the same person, organization, or event does **not** automatically prove a claim.

For example:

> **Claim:** "MS Dhoni will represent India in FIFA."

An evidence headline saying:

> "FIFA celebrates MS Dhoni's birthday"

is related to Dhoni and FIFA, but it does **not** establish that Dhoni will represent India in FIFA.

VerifAI therefore focuses on the **exact factual proposition being claimed**, rather than simply searching for related information.

---

## Core Idea

The verification pipeline is:

```text
Input
  │
  ├── Screenshot
  │      │
  │      └── OCR
  │
  └── URL
         │
         └── Content Extraction
                │
                ▼
          Claim Extraction
                │
                ▼
          Evidence Retrieval
                │
                ▼
        Evidence Relevance
                │
                ▼
       Claim Verification
                │
                ▼
       Natural-language Result
```

The system is intentionally centered around **evidence-based claim verification** rather than attempting to classify whether an image or video was AI-generated.

---

# Features

## 1. Screenshot Verification

Users can upload a screenshot containing a viral news post, social-media post, or forwarded message.

VerifAI:

- extracts text using OCR
- identifies the factual claim
- extracts entities, dates, locations, and events
- generates a search query
- retrieves relevant external news evidence
- compares the claim against the evidence

---

## 2. URL Verification

Users can provide a URL instead of uploading a screenshot.

The URL analyzer attempts to extract publicly available information such as:

- page title
- description
- visible text
- publication information
- images when available
- video metadata when publicly exposed

This makes the system useful for publicly accessible articles and social-media posts.

---

## 3. Google News Evidence Retrieval

VerifAI uses the Google News RSS feed to retrieve recent news evidence.

The evidence contains information such as:

```json
{
  "title": "...",
  "url": "...",
  "source": "...",
  "published": "..."
}
```

The purpose of the RSS feed is **evidence discovery**, not to treat Google News itself as the verifier.

The verification engine evaluates the retrieved evidence against the exact claim.

---

## 4. Temporal Evidence Filtering

News can be misleading when the same event happens repeatedly.

For example, a claim may refer to an event occurring in 2026 while a retrieved headline refers to a similar event from 2024.

VerifAI therefore considers the temporal relationship between the claim and the evidence.

When a claim date is available:

- evidence published after the claim date is excluded
- recent evidence receives greater weight
- older evidence receives progressively lower weight
- evidence far outside the relevant time period has substantially less influence

This helps prevent an old article about a recurring event from being incorrectly treated as evidence for a newer claim.

---

## 5. Exact Claim Focus

One of the most important design principles of VerifAI is:

> **Related does not mean supporting.**

The system should not consider an evidence headline sufficient merely because it mentions:

- the same person
- the same organization
- the same location
- the same topic
- the same event category

Evidence should establish the actual factual proposition contained in the claim.

For example:

### Claim

```text
MS Dhoni will represent India in FIFA.
```

### Evidence

```text
FIFA celebrates MS Dhoni's birthday.
```

The evidence is related to the claim, but does not establish it.

Therefore, the evidence should not be treated as proof of the claim.

---

# Architecture

```text
                    ┌─────────────────────┐
                    │      Frontend       │
                    │   Web Application   │
                    └──────────┬──────────┘
                               │
                               │ HTTP
                               ▼
                    ┌─────────────────────┐
                    │       FastAPI       │
                    │      /verify        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        ┌──────────┐     ┌────────────┐   ┌──────────────┐
        │   OCR    │     │ URL Parser │   │ Claim Engine │
        │ EasyOCR  │     │            │   │              │
        └────┬─────┘     └─────┬──────┘   └──────┬───────┘
             │                 │                 │
             └─────────────────┴─────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Evidence Search    │
                    │   Google News RSS   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Verification Engine │
                    │                     │
                    │ Claim ↔ Evidence    │
                    │ Temporal Relevance  │
                    │ Semantic Relation   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Verification Result │
                    └─────────────────────┘
```

---

# Project Structure

```text
VerifAI/
│
├── backend/
│   │
│   ├── main.py
│   │
│   └── services/
│       ├── __init__.py
│       ├── evidence.py
│       ├── llm.py
│       ├── url_analyzer.py
│       └── verifier.py
│
├── frontend/
│   └── ...
│
├── .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

# Backend Components

## `main.py`

The FastAPI entry point.

It handles:

- file uploads
- input validation
- image validation
- OCR
- claim analysis
- evidence retrieval
- claim verification
- API responses

Main endpoint:

```text
POST /verify
```

Health endpoint:

```text
GET /health
```

---

## `services/evidence.py`

Responsible for retrieving external news evidence.

It uses Google News RSS and returns a structured list of articles containing:

- title
- URL
- source
- publication date

---

## `services/llm.py`

Responsible for extracting structured information from the content.

The claim analysis can contain information such as:

```json
{
  "claim": "...",
  "location": "...",
  "date": "...",
  "entities": [],
  "event_type": "...",
  "search_query": "..."
}
```

This allows the evidence retrieval and verification stages to work with structured information instead of raw OCR text alone.

---

## `services/url_analyzer.py`

Handles publicly accessible URLs.

It attempts to extract useful information from pages and publicly available social-media metadata.

The system does not attempt to bypass authentication, private accounts, or platform security mechanisms.

---

## `services/verifier.py`

The core verification engine.

Its job is **not** to determine whether two pieces of text are merely related.

Its job is to determine whether the retrieved evidence actually establishes or contradicts the factual proposition represented by the claim.

The verifier also considers temporal relevance when dates are available.

---

# API

## Health Check

```http
GET /health
```

Example response:

```json
{
  "status": "ok",
  "service": "VerifAI"
}
```

---

## Verify Screenshot

```http
POST /verify
```

Upload an image using the `file` field.

Example using cURL:

```bash
curl -X POST "http://localhost:8000/verify" \
  -H "accept: application/json" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@screenshot.png"
```

---

# Example Verification Flow

Suppose a user uploads a screenshot containing:

```text
Amitabh Bachchan has passed away today.
```

The system extracts the claim and searches for relevant evidence.

If recent trusted evidence instead contains headlines such as:

```text
Amitabh Bachchan attends an event in Mumbai
```

then the evidence provides a strong reason to question the death claim because the reported event is incompatible with the claim's factual proposition and timeline.

The system should therefore use the evidence semantically rather than simply looking for exact keyword matches.

---

# Important Design Principle

VerifAI deliberately avoids the following simplistic strategy:

```text
Same person mentioned
        ↓
Same topic
        ↓
Therefore TRUE
```

Instead:

```text
Claim
  ↓
What exact factual proposition is being asserted?
  ↓
What does each evidence source actually establish?
  ↓
Does the evidence entail the proposition?
  ↓
Does the evidence contradict the proposition?
  ↓
Is the evidence temporally relevant?
  ↓
Final conclusion
```

This distinction is critical for real-world misinformation detection.

---

# Technology Stack

### Backend

- Python
- FastAPI
- EasyOCR
- Hugging Face inference models
- Google News RSS
- BeautifulSoup / web extraction utilities
- Pillow

### Frontend

- Web-based frontend
- Designed for simple interaction
- Screenshot upload
- URL submission
- Human-readable verification results

---

# Local Development

## 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/VerifAI.git
cd VerifAI
```

---

## 2. Create a virtual environment

Windows:

```bash
python -m venv .venv
```

Activate it:

```bash
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## 4. Configure environment variables

Create:

```text
.env
```

Example:

```env
HF_TOKEN=your_huggingface_token
```

Do **not** commit `.env` to GitHub.

---

## 5. Start the backend

From the project root:

```bash
uvicorn backend.main:app --reload
```

The API will be available at:

```text
http://localhost:8000
```

FastAPI documentation:

```text
http://localhost:8000/docs
```

---

# Environment Variables

| Variable | Purpose |
|---|---|
| `HF_TOKEN` | Hugging Face API authentication |

Never expose API tokens in the frontend or commit them to the repository.

---

# Deployment

The intended deployment architecture is:

```text
                 User
                  │
                  ▼
        ┌──────────────────┐
        │     Frontend     │
        │      Netlify     │
        └────────┬─────────┘
                 │
                 │ HTTPS API requests
                 ▼
        ┌──────────────────┐
        │     FastAPI      │
        │      Render      │
        └────────┬─────────┘
                 │
        ┌────────┴─────────┐
        ▼                  ▼
   Google News RSS    Hugging Face
     Evidence          Inference
```

The frontend communicates with the deployed FastAPI backend rather than running the backend locally.

---

# Current Scope

VerifAI currently focuses on **news and claim verification**.

The project intentionally does not attempt to solve every misinformation-related problem.

In particular, detecting whether arbitrary media was generated by AI is not considered a core verification mechanism.

AI-generated-media detection is an extremely difficult problem and a simple LLM classification prompt would not provide sufficiently reliable results.

Instead, VerifAI focuses on a narrower and more measurable problem:

> **Given a factual claim and external evidence, determine what the evidence actually says about that claim.**

---

# Limitations

VerifAI is an evidence-based verification system, not an oracle of truth.

Important limitations include:

- Google News RSS provides headlines rather than complete articles.
- A headline may omit important context.
- Some events may not be reported by major news organizations.
- Multiple news articles may originate from the same underlying report.
- Social-media platforms may restrict access to content.
- Private or login-protected content cannot reliably be extracted.
- Absence of evidence does not automatically prove that a claim is false.
- A claim may contain multiple factual propositions.
- Evidence quality depends partly on the sources returned by the search system.
- Historical and recurring events require careful temporal interpretation.

For these reasons, the system should communicate uncertainty rather than confidently inventing conclusions when the available evidence is insufficient.

---

# Security

Do not commit:

```text
.env
HF_TOKEN
API keys
credentials
private configuration
```

The repository should use `.gitignore` to prevent secrets and generated files from being committed.

---

# Future Improvements

Potential future improvements include:

- Better evidence-source diversity
- Full article extraction instead of headline-only evidence
- Evidence deduplication
- Source credibility weighting
- Better handling of multiple claims in a single post
- Improved temporal reasoning
- Multilingual OCR and claim extraction
- Better support for publicly accessible social-media content
- Evidence citation and source previews
- Improved handling of conflicting reports

---

# Philosophy

VerifAI is built around a simple principle:

> **Don't ask whether the evidence is related to the claim. Ask whether the evidence actually proves what the claim says.**

A person, place, organization, or event appearing in a headline is not enough.

The evidence must be relevant to the **specific factual proposition** being evaluated.

---

# Disclaimer

VerifAI provides automated analysis based on available external evidence.

Its output should not be treated as an absolute guarantee of truth or falsity, especially when evidence is incomplete, conflicting, outdated, or unavailable.

Always consult the underlying sources when making important decisions.

---

# License

This project is currently distributed under the license specified in the repository.

If no license has been selected yet, the repository should be considered **unlicensed** until an explicit open-source license is added.
