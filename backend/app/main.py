from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.routes.transfer import router as trasnfer_router
from app.services.discovery_service import HellWireAdvertiser


# Setup the advertiser
advertiser = HellWireAdvertiser(port=8000)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await advertiser.start()  # Await async registration
    yield
    await advertiser.stop()   # Await async cleanup


app = FastAPI(lifespan=lifespan)

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