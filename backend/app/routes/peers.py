from fastapi import APIRouter, Request

router = APIRouter()

@router.get("/peers")
async def get_peers(request: Request):
    registry = request.app.state.peer_registry
    peers = registry.list_peers()
    return{
        "count": len(peers),
        "peers": peers,
    }