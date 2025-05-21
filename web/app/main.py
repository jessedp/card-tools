import os
import hashlib
import json

from urllib.parse import urlparse
from typing import Optional, Tuple

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from starlette.websockets import WebSocket, WebSocketDisconnect

from pydantic import BaseModel

import httpx

from web.app.ebay import search_ebay_by_image
from web.app.logger import setup_logger
from analyze_card import analyze_trading_card, OCRResponse


from .routers import pubsub

logger = setup_logger()

app = FastAPI()

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)

app.include_router(pubsub.router)

# Create cache directory if it doesn't exist
os.makedirs("cache", exist_ok=True)

app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.post("/api/search-ebay")
async def search_ebay(imageFile: UploadFile = File(...)):
    try:
        image_data = await imageFile.read()
        results = search_ebay_by_image(image_data, imageFile.content_type)
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"eBay search failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/")
async def index():
    return FileResponse("web/static/index.html")


# Allowed image extensions and content types
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Optional: List of allowed domains (empty means all are allowed)
ALLOWED_DOMAINS: set[str] = set()  # Example: {'trusted-cdn.com', 'images.example.com'}

@app.get("/api/image-proxy")
async def proxy_image(url: str = Query(..., description="The image URL to proxy")):
    try:
        # Validate URL format
        parsed = urlparse(url)
        if not all([parsed.scheme, parsed.netloc]):
            raise HTTPException(status_code=400, detail="Invalid URL format")

        # Validate domain if allowed domains are specified
        if ALLOWED_DOMAINS and parsed.netloc not in ALLOWED_DOMAINS:
            raise HTTPException(status_code=403, detail="Domain not allowed")

        # # Validate file extension
        # if not any(parsed.path.lower().endswith(ext) for ext in ALLOWED_EXTENSIONS):
        #     raise HTTPException(status_code=400, detail="Invalid image extension")

        # Fetch the image
        async with httpx.AsyncClient() as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.10 Safari/605.1.1"
            }
            response = await client.get(url, headers=headers, timeout=10.0)

            # Check status
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code, detail="Upstream error"
                )

            # Validate content type
            content_type = response.headers.get("content-type", "").split(";")[0]
            # if content_type not in ALLOWED_CONTENT_TYPES:
            #     raise HTTPException(
            #         status_code=400, detail=f"Invalid content type - {content_type}"
            #     )

            # Validate size (5MB max)
            if "content-length" in response.headers:
                content_length = int(response.headers["content-length"])
                if content_length > 5 * 1024 * 1024:  # 5MB
                    raise HTTPException(status_code=400, detail="Image too large")

            # Return the image
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Cache-Control": "public, max-age=86400"  # Cache for 24 hours
                },
            )

    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Upstream timeout")
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=502, detail=f"Upstream connection error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


# class OCRResponse(BaseModel):
#     status: Optional[str] = "ok"
#     cache_hit: Optional[bool] = False
#     player_name: Optional[str] = None
#     team_name: Optional[str] = None
#     card_set_year: Optional[str] = None
#     card_number: Optional[str] = None
#     serial_number: Optional[str] = None
#     card_type: Optional[str] = None
#     other: Optional[str] = None


def get_file_hash(content: bytes) -> str:
    return hashlib.md5(content).hexdigest()


@app.post("/api/ocr-image", response_model=OCRResponse)
async def ocr_image(file: UploadFile = File(...)):
    try:
        # Read the file content
        content = await file.read()

        # Generate hash for filename
        file_hash = get_file_hash(content)
        img_cache_path = f"cache/{file_hash}.jpg"

        # Check cache
        img_cache_hit = os.path.exists(img_cache_path)

        # Save to cache if not exists
        if not img_cache_hit:
            with open(img_cache_path, "wb") as f:
                f.write(content)

        json_cache_path = f"cache/{file_hash}.json"
        json_cache_hit = os.path.exists(json_cache_path)

        # Save to cache if not exists
        if json_cache_hit:
            with open(json_cache_path, "r") as f:
                ocr_data = f.read()
            logger.info("OCR data FROM CACHE...")
        else:
            # Perform OCR
            ocr_data = analyze_trading_card(img_cache_path)
            with open(json_cache_path, "w") as f:
                f.write(ocr_data)
            logger.info("CACHED OCR data...")

        logger.info(f"OCR data: {ocr_data}")
        response = {"status": "ok", "cache_hit": img_cache_hit}

        response.update(json.loads(ocr_data))

        return response

    except Exception as e:
        raise e
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
