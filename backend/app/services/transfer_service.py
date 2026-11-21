import os
import uuid
from pathlib import Path
from typing import AsyncIterator

UPLOAD_DIR = Path(__file__).resolve().parents[2] / "received_files"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

MAX_UPLOAD_SIZE = 1024 * 1024 * 1024 #1GB


class InvalidFilenameError(Exception):
    pass

class UploadTooLargeError(Exception):
    pass

class FileStorageError(Exception):
    pass

async def save_stream(chunks: AsyncIterator[bytes], filename: str):

    # 1. Sanitize filename
    filename = filename.replace("\\", "/")
    filename = Path(filename).name

    if filename in {".", "..", ""} or "\x00" in filename:
        raise InvalidFilenameError("Invalid Filename")


    # 2. Generate temporary filename
    file_id = uuid.uuid4().hex
    temp_path = UPLOAD_DIR / f".{file_id}.part"
    final_path = None

    total_bytes = 0

    try:
        # 3. Receive and save chunks
        with temp_path.open("xb") as output:

            async for chunk in chunks:

                if not chunk:
                    continue

                if total_bytes + len(chunk) > MAX_UPLOAD_SIZE:
                    raise UploadTooLargeError("File exceeds maximum upload size")

                output.write(chunk)
                total_bytes += len(chunk)

        # 4. Finalize file without overwriting exisiting file
        counter = 0

        while True:

            if counter == 0:
                candidate = UPLOAD_DIR / filename

            else:
                original = Path(filename)
                new_name = f"{original.stem} ({counter}){original.suffix}"
                candidate = UPLOAD_DIR / new_name

            try:
                os.link(temp_path, candidate)
                final_path = candidate
                break

            except FileExistsError:
                counter += 1


    except UploadTooLargeError:
        raise

    except OSError as error:
        raise FileStorageError("Could not save uploaded file") from error

    finally:
        temp_path.unlink(missing_ok=True)


    return{
        "filename": final_path.name,
        "size_bytes": total_bytes
    }