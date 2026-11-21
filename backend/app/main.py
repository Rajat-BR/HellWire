from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routes.transfer import router as trasnfer_router

app = FastAPI()

app.include_router(trasnfer_router)

@app.get("/")
def home():
    return {"message": "HellWire is running. Lets goooooo"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/test-upload", response_class=HTMLResponse)
async def test_upload():
    html_path = Path(__file__).resolve().parents[1] / "upload_test.html"
    return html_path.read_text() 

