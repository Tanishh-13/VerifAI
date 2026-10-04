from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from dotenv import load_dotenv
import io
import os
import requests

from services.url_analyzer import analyze_url
from services.llm import analyze_claim
from services.evidence import search_news
from services.verifier import verify_claim


load_dotenv()

OCR_API_KEY = os.getenv("OCR_API_KEY")

app = FastAPI(
    title="VerifAI API",
    description="AI-media and claim verification for viral content.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def extract_text_from_image(contents: bytes, filename: str) -> str:

    if not OCR_API_KEY:
        raise RuntimeError("OCR_API_KEY is not configured.")

    response = requests.post(
        "https://api.ocr.space/parse/image",
        files={
            "file": (
                filename or "image.jpg",
                contents
            )
        },
        data={
            "apikey": OCR_API_KEY,
            "language": "eng",
            "isOverlayRequired": "false",
            "OCREngine": "2",
            "scale": "true",
        },
        timeout=60,
    )

    response.raise_for_status()

    data = response.json()

    if data.get("IsErroredOnProcessing"):
        errors = data.get("ErrorMessage", "OCR processing failed.")

        if isinstance(errors, list):
            errors = " ".join(str(error) for error in errors)

        raise RuntimeError(str(errors))

    parsed_results = data.get("ParsedResults", [])

    extracted_text = " ".join(
        result.get("ParsedText", "")
        for result in parsed_results
        if isinstance(result, dict)
    ).strip()

    return extracted_text


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
            detail="VerifAI accepts image files only."
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
        extracted_text = extract_text_from_image(
            contents,
            file.filename or "image.jpg"
        )

    except Exception as e:
        return {
            "filename": file.filename,
            "media_type": file.content_type,
            "extracted_text": "",
            "claim_analysis": None,
            "evidence": [],
            "verification": {
                "conclusion": "The image could not be processed for verification.",
                "explanation": f"OCR processing failed: {str(e)}",
                "evidence_analysis": [],
                "limitations": [
                    "The OCR service could not extract readable text."
                ]
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
                "conclusion": "The image does not contain enough readable text to verify a claim.",
                "explanation": "No readable factual text was detected.",
                "evidence_analysis": [],
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
                "conclusion": "The claim could not be analyzed.",
                "explanation": f"Claim analysis failed: {str(e)}",
                "evidence_analysis": [],
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
                "conclusion": "A sufficiently clear factual claim could not be extracted.",
                "explanation": "The claim extraction step did not produce a usable factual proposition.",
                "evidence_analysis": [],
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
            "conclusion": "The claim could not be reliably verified.",
            "explanation": f"The verification engine failed: {str(e)}",
            "evidence_analysis": [],
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