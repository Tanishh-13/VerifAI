from fastapi import FastAPI

app = FastAPI(
    title="VerifAI API",
    description="Evidence-based verification for viral media and claims.",
    version="0.1.0",
)


@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "VerifAI API"
    }