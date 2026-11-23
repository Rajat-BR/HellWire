from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from zeroconf import IPVersion
from zeroconf.asyncio import AsyncZeroconf

from app.routes.peers import router as peers_router
from app.routes.transfer import router as trasnfer_router
from app.services.discovery_service import (
    HellWireAdvertiser,
    HellWireBrowser,
    PeerRegistery,
)

# Setup Peer Registry, Advertiser and Browser
peer_registry = PeerRegistery()
advertiser = HellWireAdvertiser(port=8000)
browser = HellWireBrowser(
    registry=peer_registry,
    ignore_instance_name=advertiser.instance_name
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.peer_registry = peer_registry
    aiozc = AsyncZeroconf(ip_version=IPVersion.V4Only)
    try:
        await advertiser.start(aiozc=aiozc)  # Await async registration
        await browser.start(aiozc=aiozc)
        yield

    finally:
        await advertiser.stop(close_aiozc=False)   # Await async cleanup
        await browser.stop(close_aiozc=False)
        await aiozc.async_close()





app = FastAPI(lifespan=lifespan)

app.include_router(trasnfer_router)
app.include_router(peers_router)


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