
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import HTTPException, UploadFile

MAX_IMAGE_BYTES = 10 * 1024 * 1024

ALLOWED_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


async def analyze_uploaded_image(upload: UploadFile) -> dict:
    """Validate and analyze an uploaded civic-issue image."""
    content_type = (upload.content_type or "").lower().split(";")[0].strip()

    if content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=415,
            detail="Upload a JPEG, PNG, or WebP image.",
        )

    temp_path = None

    try:
        contents = await upload.read(MAX_IMAGE_BYTES + 1)

        if not contents:
            raise HTTPException(status_code=400, detail="The uploaded file is empty.")

        if len(contents) > MAX_IMAGE_BYTES:
            raise HTTPException(
                status_code=413,
                detail="Image size must not exceed 10 MB.",
            )

        with NamedTemporaryFile(
            suffix=ALLOWED_TYPES[content_type],
            delete=False,
        ) as temp_file:
            temp_file.write(contents)
            temp_path = Path(temp_file.name)

        # Import here so the API can start without loading the ML model.
        from ml.src.analyze_complaint import analyze_complaint

        result = analyze_complaint(str(temp_path))

        if not result.get("ok", False):
            error = result.get("error", "")

            if error == "invalid_image":
                raise HTTPException(
                    status_code=422,
                    detail="The uploaded file is not a valid readable image.",
                )

            raise HTTPException(
                status_code=500,
                detail="Image analysis failed. Please try again.",
            )

        return result

    except HTTPException:
        raise
    except FileNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="The trained detection model is unavailable.",
        ) from None
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Image analysis failed. Please try again.",
        ) from None
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

        await upload.close()
