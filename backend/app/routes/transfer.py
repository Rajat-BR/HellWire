from fastapi import APIRouter, HTTPException, Request

from app.services.transfer_service import (
    save_stream,
    InvalidFilenameError,
    UploadTooLargeError,
    FileStorageError
)

router = APIRouter()

def handle_transer_error(error: Exception):
    if isinstance(error, InvalidFilenameError):
        raise HTTPException(status_code=400, detil=str(error))

    if isinstance(error, UploadTooLargeError):
        raise HTTPException(status_code=413, detail=str(error))

    if isinstance(error, FileStorageError):
        raise HTTPException(status_code=500, detail=str(error))


# Upload
@router.post("/upload")
async def upload(request: Request, filename: str):
    try:
        result = await save_stream(request.stream(), filename)

    except (InvalidFilenameError, UploadTooLargeError, FileStorageError) as error:
        handle_transer_error(error)

    return{
        "message": "File uploaded successfully",
        **result
    }