import json
import os
import re
from datetime import datetime, timezone
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is not set. Add it to backend/.env")

client = InferenceClient(token=HF_TOKEN)


def normalize(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_date(value):
    if not value:
        return None

    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%B %d, %Y",
        "%b %d, %Y",
        "%d %B %Y",
        "%d %b %Y",
        "%Y-%m-%d",
    ]

    for fmt in formats:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue

    return None


def evaluate_temporal_relevance(claim_date, evidence_date):
    if not claim_date or not evidence_date:
        return 1.0

    claim_dt = parse_date(claim_date)
    evidence_dt = parse_date(evidence_date)

    if not claim_dt or not evidence_dt:
        return 1.0

    if claim_dt.tzinfo is None:
        claim_dt = claim_dt.replace(tzinfo=timezone.utc)

    if evidence_dt.tzinfo is None:
        evidence_dt = evidence_dt.replace(tzinfo=timezone.utc)

    days_diff = (evidence_dt - claim_dt).days

    if days_diff < -365:
        return 0.2
    elif days_diff < -30:
        return 0.5
    elif -30 <= days_diff <= 90:
        return 1.0
    else:
        return 0.7


def is_satire_or_fiction(claim_analysis: dict) -> bool:
    if claim_analysis.get("is_satire") or claim_analysis.get("event_type") == "satire":
        return True

    text_to_check = normalize(
        f"{claim_analysis.get('claim', '')} {claim_analysis.get('raw_text', '')}"
    )
    satire_keywords = ["satire", "parody", "satirical", "just a joke", "not real", "meme"]
    return any(kw in text_to_check for kw in satire_keywords)


def analyze_and_synthesize(claim: str, usable_evidence: list) -> dict:
    items_formatted = []
    for idx, item in enumerate(usable_evidence, start=1):
        items_formatted.append(
            f"Source ID {idx}: \"{item.get('title', '')}\" (Publisher: {item.get('source', 'Unknown')})"
        )

    headlines_text = "\n".join(items_formatted)

    prompt = f"""You are a strict, conservative fact-checking verifier. Analyze whether external news evidence verifies, disproves, or is insufficient to prove the exact claim.

EXACT CLAIM: "{claim}"

EVIDENCE HEADLINES:
{headlines_text}

STRICT CLASSIFICATION & REASONING RULES:
1. Numerical & Quantitative Precision:
   - Do NOT treat similar numbers, percentages, or estimates as identical proof (e.g., "544% surplus" is NOT exact proof for "9x normal rainfall").
   - If numbers differ, or if key details in the claim are not explicitly confirmed by the headline, mark as RELATED_NEUTRAL.

2. Headline Classifications:
   - DIRECT_SUPPORT: The headline explicitly confirms the core claim AND key figures/details stated.
   - DIRECT_CONTRADICTION: The headline explicitly disproves or presents facts that make the core claim impossible.
   - RELATED_NEUTRAL: The headline discusses the same topic, region, event, or entities, but lacks exact confirmation of the specific claim or numbers.
   - UNRELATED: Off-topic news.

3. Verdict Selection:
   - "TRUE": Only if at least one trusted source provides DIRECT_SUPPORT.
   - "FALSE": Only if at least one trusted source provides DIRECT_CONTRADICTION.
   - "UNVERIFIED": If sources are RELATED_NEUTRAL, conflicting, or do not offer exact proof.

Respond STRICTLY in JSON format with no additional text:
{{
  "verdict": "TRUE" | "FALSE" | "UNVERIFIED",
  "explanation": "A clear, objective explanation (2-3 sentences) detailing why this verdict was chosen, noting specifically what news sources confirm vs. where details/numbers differ or remain unconfirmed.",
  "featured_source_id": ,
  "evidence_analysis": [
    {{
      "source_id": 1,
      "relation": "DIRECT_SUPPORT" | "DIRECT_CONTRADICTION" | "RELATED_NEUTRAL" | "UNRELATED",
      "reasoning": "1-sentence explanation of why this headline specifically matches, contradicts, or is merely related."
    }}
  ]
}}"""

    messages = [
        {"role": "system", "content": "You are a conservative, highly accurate fact-checker. Output valid JSON only."},
        {"role": "user", "content": prompt}
    ]

    models_to_try = [
        "Qwen/Qwen2.5-72B-Instruct",
        "meta-llama/Llama-3.1-8B-Instruct",
        "google/gemma-2-9b-it"
    ]

    response_text = None
    for model in models_to_try:
        try:
            res = client.chat_completion(
                messages=messages,
                model=model,
                max_tokens=1200,
                temperature=0.01,
            )
            response_text = res.choices[0].message.content
            if response_text:
                break
        except Exception:
            continue

    if not response_text:
        return {
            "verdict": "UNVERIFIED",
            "explanation": "Verification reasoning service was temporarily unavailable to evaluate evidence headlines.",
            "featured_source_id": None,
            "evidence_analysis": [
                {"source_id": i + 1, "relation": "RELATED_NEUTRAL", "reasoning": "Inference unavailable."}
                for i in range(len(usable_evidence))
            ]
        }

    cleaned_json = response_text.strip()
    if "```json" in cleaned_json:
        cleaned_json = cleaned_json.split("```json")[1].split("```")[0].strip()
    elif "```" in cleaned_json:
        cleaned_json = cleaned_json.split("```")[1].split("```")[0].strip()

    try:
        parsed = json.loads(cleaned_json)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    return {
        "verdict": "UNVERIFIED",
        "explanation": "Could not parse verification structured reasoning output.",
        "featured_source_id": None,
        "evidence_analysis": [
            {"source_id": i + 1, "relation": "RELATED_NEUTRAL", "reasoning": "Unparseable verification output."}
            for i in range(len(usable_evidence))
        ]
    }


def verify_claim(claim_analysis: dict, evidence: list) -> dict:
    claim = claim_analysis.get("claim", "").strip()
    claim_date = claim_analysis.get("date")

    # 1. No claim extracted
    if not claim:
        return {
            "verdict": "NO_CLAIM",
            "explanation": "No distinct factual claim could be extracted from the provided media to verify against news reports.",
            "featured_source": None,
            "evidence_analysis": [],
            "limitations": ["Claim extraction produced no usable factual proposition."]
        }

    # 2. Satire detection
    if is_satire_or_fiction(claim_analysis):
        return {
            "verdict": "SATIRE",
            "explanation": "The content contains explicit satire, parody, or humorous disclaimer indicators and should not be treated as genuine news.",
            "featured_source": None,
            "evidence_analysis": [],
            "claim_date": claim_date,
            "limitations": ["Satirical or meme posts do not represent real-world factual reporting."]
        }

    usable_evidence = [
        item for item in evidence
        if isinstance(item, dict) and item.get("title") and not item.get("error")
    ]

    # 3. No usable external evidence
    if not usable_evidence:
        return {
            "verdict": "UNVERIFIED",
            "explanation": "No matching external news articles were retrieved to confirm or disprove this claim.",
            "featured_source": None,
            "evidence_analysis": [],
            "limitations": ["No trusted news articles were available for verification."]
        }

    # 4. Perform LLM analysis and synthesis
    synthesis = analyze_and_synthesize(claim, usable_evidence)

    verdict = synthesis.get("verdict", "UNVERIFIED")
    explanation = synthesis.get("explanation", "Insufficient evidence to conclusively establish claim.")
    featured_source_id = synthesis.get("featured_source_id")

    raw_analyses = synthesis.get("evidence_analysis", [])
    eval_lookup = {}
    if isinstance(raw_analyses, list):
        for item in raw_analyses:
            if isinstance(item, dict) and "source_id" in item:
                eval_lookup[item["source_id"]] = item

    analyses = []
    support_count = 0
    contradiction_count = 0
    neutral_count = 0

    featured_source = None

    for index, item in enumerate(usable_evidence, start=1):
        title = item.get("title", "")
        url = item.get("url", "")
        source_name = item.get("source", "Trusted News Source")
        published = item.get("published", "")

        temporal_weight = evaluate_temporal_relevance(claim_date, published)
        eval_item = eval_lookup.get(index, {})

        relation = eval_item.get("relation", "RELATED_NEUTRAL")
        reasoning = eval_item.get("reasoning", "Discusses related topic or entities.")

        if temporal_weight < 0.3:
            relation = "TEMPORALLY_IRRELEVANT"

        if relation == "DIRECT_SUPPORT":
            support_count += 1
        elif relation == "DIRECT_CONTRADICTION":
            contradiction_count += 1
        else:
            neutral_count += 1

        source_obj = {
            "source_id": index,
            "title": title,
            "url": url,
            "source": source_name,
            "published": published,
            "relation": relation,
            "temporal_weight": temporal_weight,
            "reasoning": reasoning
        }
        analyses.append(source_obj)

        if featured_source_id == index or (featured_source is None and relation in ["DIRECT_SUPPORT", "DIRECT_CONTRADICTION"]):
            featured_source = {
                "title": title,
                "source": source_name,
                "url": url
            }

    # Fallback featured source if unverified but related evidence exists
    if featured_source is None and usable_evidence:
        first_item = usable_evidence[0]
        featured_source = {
            "title": first_item.get("title", ""),
            "source": first_item.get("source", "News Source"),
            "url": first_item.get("url", "")
        }

    return {
        "verdict": verdict,
        "explanation": explanation,
        "featured_source": featured_source,
        "evidence_analysis": analyses,
        "claim_date": claim_date,
        "support_count": support_count,
        "contradiction_count": contradiction_count,
        "neutral_count": neutral_count,
        "limitations": [
            "Verification requires direct propositional and numerical alignment with retrieved news headlines.",
            "Topical relevance or approximate figures without exact proof are treated as UNVERIFIED.",
            "Coverage depends on available real-time news indexing."
        ]
    }