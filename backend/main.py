from fastapi import FastAPI, UploadFile, File, HTTPException
from PIL import Image
import easyocr
import io

app = FastAPI(
    title="VerifAI API",
    description="AI-media and claim verification for viral content.",
    version="0.1.0",
)

reader = easyocr.Reader(["en"], gpu=False)


@app.get("/health")
def health():
    return {"status": "ok", "service": "VerifAI"}


@app.post("/verify")
async def verify(file: UploadFile = File(...)):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="For now, VerifAI accepts image files only."
        )

    contents = await file.read()

    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid image.")

    results = reader.readtext(contents, detail=1)

    extracted_text = " ".join(
        result[1] for result in results
    )

    return {
        "filename": file.filename,
        "media_type": file.content_type,
        "extracted_text": extracted_text,
        "ocr_detections": len(results),
        "status": "analysis_ready"
    }