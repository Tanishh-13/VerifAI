# VerifAI

### Check before you share.

VerifAI is a lightweight news and viral-claim verification system designed to help users evaluate potentially misleading content circulating through social media, messaging platforms, and the web.

Instead of deciding whether something is true based only on an LLM's opinion, VerifAI extracts the factual claim and compares it against external news evidence retrieved from trusted sources.

The core objective is simple:

> Given a factual claim and external evidence, determine whether the evidence supports the exact claim, contradicts it, or is insufficient to establish it.

---

## Why VerifAI?

Misleading information often spreads through screenshots, social-media posts, viral images, and forwarded messages.

A major problem with automated verification is that a source discussing a similar topic does **not** necessarily prove the claim.

For example:

> "MS Dhoni will represent India in FIFA."

An article saying:

> "FIFA celebrates MS Dhoni's birthday"

is related to Dhoni and FIFA, but it does **not** establish that Dhoni will represent India in FIFA.

VerifAI therefore focuses on the **exact factual proposition being made**, rather than relying on keyword overlap or topical similarity alone.

---

## How It Works

```text
User Content
     │
     ├── Image / Screenshot
     │        │
     │        ▼
     │      EasyOCR
     │        │
     │        ▼
     │   Extracted Text
     │
     └── URL
              │
              ▼
        Content Extraction
              │
              ▼
        Claim Extraction
              │
              ▼
        Search Query
              │
              ▼
       Google News RSS
              │
              ▼
       External Evidence
              │
              ▼
      Claim Verification
              │
              ▼
        Final Explanation
