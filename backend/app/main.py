import uuid
from pathlib import Path
from fastapi.responses import HTMLResponse

from fastapi import FastAPI, File, HTTPException, UploadFile, Request

app = FastAPI()
UPLOAD_DIR = Path("receieved_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 1024 * 1024 * 1024  #1GB

 
@app.get("/")
def home():
    return {"message": "HellWire is running. Lets goooooo"}

@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/test-upload", response_class=HTMLResponse)
async def test_upload():
    return (Path("upload_test.html")).read_text()


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="File name is missing."
        )

    filename = Path(file.filename).name

    if filename in {"", ".", ".."}:
        raise HTTPException(
            status_code=400,
            detail="Invaild File name"
        )

    destination = UPLOAD_DIR / filename

    try:
        with destination.open("wb") as output:
            while chunk := await file.read(1024 * 1024):
                output.write(chunk)

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Could not save the uploaded file."
        )

    finally:
        await file.close()


    return{
        "message": "File uploaded successfully.",
        "filename": filename,
        "size_bytes": destination.stat().st_size
    }


@app.post("/upload-stream")
async def upload_stream(request: Request, filename: str):
    #1. Sanitize Filename
    filename = filename.replace("\\", "/")
    filename = Path(filename).name

    if filename in {".", "..", ""}:
        raise HTTPException(status_code=400, detail="Invalid Filename")

    #2. Generate Unique Filename
    file_id = uuid.uuid4().hex

    temp_path = UPLOAD_DIR / f".{file_id}.part"
    final_path = UPLOAD_DIR / f"{filename}"

    total_bytes = 0

    try:
        # 3. Read incoming request body in chunks
        with temp_path.open("xb") as output:

            async for chunk in request.stream():
                print("Received chunk:", len(chunk), "bytes")
                total_bytes += len(chunk)
                output.write(chunk)
                print("Total received:", total_bytes)

            # 4. Enforce upload size limit
            if total_bytes > MAX_UPLOAD_SIZE:
                raise HTTPException(status_code=413, detail="File exceeds maximum upload size")

            output.write(chunk)

        # Finalize the upload
        temp_path.replace(final_path)

    except HTTPException:
        raise

    except OSError:
        raise HTTPException(
            status_code=500,
            detail="Could not save uploaded file"
        )

    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "message": "File uploaded successfully",
        "filename": filename,
        "stored_as": final_path.name,
        "size_bytes": total_bytes
    }
