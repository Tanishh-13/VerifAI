from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
from dotenv import load_dotenv
import easyocr
import io
from services.url_analyzer import analyze_url
from services.llm import analyze_claim
from services.evidence import search_news
from services.verifier import verify_claim


load_dotenv()

app = FastAPI(
    title="VerifAI API",
    description="AI-media and claim verification for viral content.",
    version="0.1.0",
)

reader = easyocr.Reader(["en"], gpu=False)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "VerifAI"
    }


@app.post("/verify")
async def verify(file: UploadFile = File(...)):

    if not file.content_type:
        raise HTTPException(
            status_code=400,
            detail="Missing file content type."
        )

    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="For now, VerifAI accepts image files only."
        )

    contents = await file.read()

    if not contents:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    try:
        image = Image.open(io.BytesIO(contents))
        image.verify()
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Invalid image file."
        )

    try:
        results = reader.readtext(
            contents,
            detail=1
        )

        extracted_text = " ".join(
            result[1]
            for result in results
        ).strip()

    except Exception as e:
        return {
            "filename": file.filename,
            "media_type": file.content_type,
            "extracted_text": "",
            "claim_analysis": None,
            "evidence": [],
            "verification": {
                "verdict": "INSUFFICIENT_EVIDENCE",
                "reasoning": "OCR processing failed.",
                "claim_components": [],
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "insufficient_evidence": [],
                "limitations": [str(e)]
            },
            "status": "analysis_failed"
        }

    if not extracted_text:
        return {
            "filename": file.filename,
            "media_type": file.content_type,
            "extracted_text": "",
            "claim_analysis": None,
            "evidence": [],
            "verification": {
                "verdict": "INSUFFICIENT_EVIDENCE",
                "reasoning": "No readable factual text was detected in the image.",
                "claim_components": [],
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "insufficient_evidence": [],
                "limitations": [
                    "The submitted image did not contain enough readable text for claim verification."
                ]
            },
            "status": "analysis_ready"
        }

    try:
        claim_analysis = analyze_claim(extracted_text)

    except Exception as e:
        return {
            "filename": file.filename,
            "media_type": file.content_type,
            "extracted_text": extracted_text,
            "claim_analysis": None,
            "evidence": [],
            "verification": {
                "verdict": "INSUFFICIENT_EVIDENCE",
                "reasoning": "Claim analysis failed.",
                "claim_components": [],
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "insufficient_evidence": [],
                "limitations": [str(e)]
            },
            "status": "analysis_failed"
        }

    if not claim_analysis or claim_analysis.get("error"):
        return {
            "filename": file.filename,
            "media_type": file.content_type,
            "extracted_text": extracted_text,
            "claim_analysis": claim_analysis,
            "evidence": [],
            "verification": {
                "verdict": "INSUFFICIENT_EVIDENCE",
                "reasoning": "The claim could not be reliably extracted.",
                "claim_components": [],
                "supporting_evidence": [],
                "contradicting_evidence": [],
                "insufficient_evidence": [],
                "limitations": [
                    "Claim extraction model failed."
                ]
            },
            "status": "analysis_failed"
        }

    search_query = claim_analysis.get("search_query")
    evidence = []

    if search_query:
        try:
            evidence = search_news(search_query)
        except Exception as e:
            evidence = [{
                "error": "Evidence retrieval failed",
                "details": str(e)
            }]

    try:
        verification = verify_claim(
            claim_analysis,
            evidence
        )

    except Exception as e:
        verification = {
            "verdict": "INSUFFICIENT_EVIDENCE",
            "reasoning": "The verification engine failed.",
            "claim_components": [],
            "supporting_evidence": [],
            "contradicting_evidence": [],
            "insufficient_evidence": [],
            "limitations": [str(e)]
        }

    return {
        "filename": file.filename,
        "media_type": file.content_type,
        "extracted_text": extracted_text,
        "claim_analysis": claim_analysis,
        "evidence": evidence,
        "verification": verification,
        "status": "analysis_ready"
    }

@app.post("/verify-url")
async def verify_url(url: str):

    url_data = analyze_url(url)

    if url_data["status"] != "success":
        return {
            "url": url,
            "status": "analysis_failed",
            "error": url_data.get("error")
        }

    extracted_text = url_data["text"]

    if not extracted_text.strip():
        return {
            "url": url,
            "status": "analysis_ready",
            "message": "Could not extract readable content from this URL.",
            "url_data": url_data
        }

    claim_analysis = analyze_claim(extracted_text)

    if not claim_analysis or claim_analysis.get("error"):
        return {
            "url": url,
            "url_data": url_data,
            "claim_analysis": claim_analysis,
            "evidence": [],
            "verification": None,
            "status": "analysis_failed"
        }

    search_query = claim_analysis.get("search_query")

    evidence = []

    if search_query:
        try:
            evidence = search_news(search_query)
        except Exception as e:
            evidence = [{
                "error": "Evidence retrieval failed",
                "details": str(e)
            }]

    verification = verify_claim(
        claim_analysis,
        evidence
    )

    return {
        "url": url,
        "url_data": url_data,
        "claim_analysis": claim_analysis,
        "evidence": evidence,
        "verification": verification,
        "status": "analysis_ready"
    }