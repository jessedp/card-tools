import os
import hashlib
import json

from urllib.parse import urlparse
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from fastapi.middleware.cors import CORSMiddleware

import httpx

from web.app.google_api import add_order_to_sheets

import web.app.ebay_api as ebay_api

from .logger import setup_logger
from analyze_card import analyze_trading_card, OCRResponse


from .routers import pubsub, ebay_oauth


logger = setup_logger()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(pubsub.router)
app.include_router(ebay_oauth.router)
# app.include_router(ebay.router)

# Create cache directory if it doesn't exist
os.makedirs("cache", exist_ok=True)

app.mount("/static", StaticFiles(directory="web/static"), name="static")


@app.post("/api/search-ebay")
async def search_ebay(imageFile: UploadFile = File(...)):
    try:
        image_data = await imageFile.read()
        results = ebay_api.search_ebay_by_image(
            image_data, str(imageFile.content_type)
        )
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"eBay search failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/")
async def index():
    return FileResponse("web/static/index.html")


@app.get("/ebay-orders")
async def ebay_orders_page():
    return FileResponse("web/static/ebay-orders.html")


@app.get("/api/ebay-orders")
async def ebay_orders():
    try:
        results = ebay_api.get_ebay_orders()
        return JSONResponse(content=results)
    except Exception as e:
        logger.error(f"eBay search failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/add-to-sheets")
async def add_to_sheets(order: dict):
    try:
        return await add_order_to_sheets(order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add to Google Sheets: {str(e)}",
        )


# Allowed image extensions and content types
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

# Optional: List of allowed domains (empty means all are allowed)
ALLOWED_DOMAINS: set[str] = (
    set()
)  # Example: {'trusted-cdn.com', 'images.example.com'}


@app.get("/api/image-proxy")
async def proxy_image(
    url: str = Query(..., description="The image URL to proxy")
):
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
            content_type = response.headers.get("content-type", "").split(";")[
                0
            ]
            # if content_type not in ALLOWED_CONTENT_TYPES:
            #     raise HTTPException(
            #         status_code=400, detail=f"Invalid content type - {content_type}"
            #     )

            # Validate size (5MB max)
            if "content-length" in response.headers:
                content_length = int(response.headers["content-length"])
                if content_length > 5 * 1024 * 1024:  # 5MB
                    raise HTTPException(
                        status_code=400, detail="Image too large"
                    )

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
        raise HTTPException(
            status_code=500, detail=f"Internal server error: {str(e)}"
        )


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
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Initialize Jinja2Templates
templates = Jinja2Templates(directory="web/app/templates")


@app.get("/ebay/new-item", response_class=HTMLResponse)
async def ebay_new_item_get(request: Request, item_id: str = None):
    """
    Renders the form to input eBay Item ID or shows results for GET requests.
    """
    if item_id is None:
        return templates.TemplateResponse(
            "new_item_form.html",
            {
                "request": request,
                "item_id": None,
                "new_item_id": None,
                "fees": None,
                "error": None,
                "structured_errors": None,
                "edit_url": None,
            },
        )

    title, description, item_specifics_xml, get_item_error = (
        ebay_api.get_item_details(item_id)
    )
    if get_item_error:
        # Handle both old string format and new structured format
        if (
            isinstance(get_item_error, dict)
            and get_item_error.get("type") == "structured"
        ):
            return templates.TemplateResponse(
                "new_item_form.html",
                {
                    "request": request,
                    "item_id": item_id,
                    "new_item_id": None,
                    "fees": None,
                    "structured_errors": get_item_error["errors"],
                    "error": None,
                    "edit_url": None,
                },
            )
        else:
            return templates.TemplateResponse(
                "new_item_form.html",
                {
                    "request": request,
                    "item_id": item_id,
                    "new_item_id": None,
                    "fees": None,
                    "error": f"Error fetching item details: {get_item_error}",
                    "structured_errors": None,
                    "edit_url": None,
                },
            )

    new_item_id, fees, add_item_result = ebay.add_new_item(
        title or "", description or "", item_specifics_xml or ""
    )

    # Check if it's an actual error (no new_item_id) or just warnings (has new_item_id)
    if add_item_result and not new_item_id:
        # This is an actual error - no listing was created
        if (
            isinstance(add_item_result, dict)
            and add_item_result.get("type") == "structured"
        ):
            return templates.TemplateResponse(
                "new_item_form.html",
                {
                    "request": request,
                    "item_id": item_id,
                    "new_item_id": None,
                    "fees": None,
                    "structured_errors": add_item_result["errors"],
                    "error": None,
                    "edit_url": None,
                },
            )
        else:
            return templates.TemplateResponse(
                "new_item_form.html",
                {
                    "request": request,
                    "item_id": item_id,
                    "new_item_id": None,
                    "fees": None,
                    "error": f"Error creating new item: {add_item_result}",
                    "structured_errors": None,
                    "edit_url": None,
                },
            )

    # Construct the edit draft URL
    edit_url = f"https://www.ebay.com/sl/list?mode=SellLikeItem&draft_id={new_item_id}&ReturnURL=https%3A%2F%2Fwww.ebay.com%2Fsh%2Flst%2Fdrafts&DraftURL=https%3A%2F%2Fwww.ebay.com%2Fsh%2Flst%2Fdrafts"

    # If there are warnings (add_item_result contains warnings), include them with the success
    warnings = None
    if (
        add_item_result
        and isinstance(add_item_result, dict)
        and add_item_result.get("type") == "structured"
    ):
        warnings = add_item_result["errors"]  # These are actually warnings

    return templates.TemplateResponse(
        "new_item_form.html",
        {
            "request": request,
            "item_id": item_id,
            "new_item_id": new_item_id,
            "fees": fees,
            "edit_url": edit_url,
            "error": None,
            "structured_errors": warnings,
        },
    )


@app.post("/ebay/new-item", response_class=HTMLResponse)
async def ebay_new_item_post(request: Request):
    """
    Handles POST requests with image uploads for creating new eBay listings.
    """
    import os
    import hashlib

    try:
        # Parse form data
        form = await request.form()
        item_id = form.get("item_id")

        if not item_id:
            return templates.TemplateResponse(
                "new_item_form.html",
                {
                    "request": request,
                    "item_id": None,
                    "new_item_id": None,
                    "fees": None,
                    "error": "Item ID is required",
                    "structured_errors": None,
                    "edit_url": None,
                },
            )

        # Get item details
        title, description, item_specifics_xml, get_item_error = (
            ebay_api.get_item_details(item_id)
        )
        if get_item_error:
            # Handle both old string format and new structured format
            if (
                isinstance(get_item_error, dict)
                and get_item_error.get("type") == "structured"
            ):
                return templates.TemplateResponse(
                    "new_item_form.html",
                    {
                        "request": request,
                        "item_id": item_id,
                        "new_item_id": None,
                        "fees": None,
                        "structured_errors": get_item_error["errors"],
                        "error": None,
                        "edit_url": None,
                    },
                )
            else:
                return templates.TemplateResponse(
                    "new_item_form.html",
                    {
                        "request": request,
                        "item_id": item_id,
                        "new_item_id": None,
                        "fees": None,
                        "error": f"Error fetching item details: {get_item_error}",
                        "structured_errors": None,
                        "edit_url": None,
                    },
                )

        # Process uploaded images
        picture_urls = []
        upload_errors = []

        # Get all uploaded files and sort by index
        image_files = []
        for key, file in form.items():
            if (
                key.startswith("image_")
                and hasattr(file, "filename")
                and getattr(file, "filename", None)
            ):
                try:
                    index = int(key.split("_")[1])
                    image_files.append((index, file))
                except (ValueError, IndexError):
                    continue

        # Sort by index to maintain order
        image_files.sort(key=lambda x: x[0])

        # Upload each image to eBay
        for index, file in image_files:
            try:
                # Read file content
                file_content = await file.read()

                # Save to cache
                cache_dir = "cache"
                os.makedirs(cache_dir, exist_ok=True)

                # Create unique filename
                file_hash = hashlib.md5(file_content).hexdigest()[:8]
                cache_filename = (
                    f"{item_id}_{index}_{file_hash}_{file.filename}"
                )
                cache_path = os.path.join(cache_dir, cache_filename)

                with open(cache_path, "wb") as cache_file:
                    cache_file.write(file_content)

                # Upload to eBay
                picture_url, upload_error = (
                    ebay_api.upload_site_hosted_pictures(
                        file_content, file.filename
                    )
                )

                if upload_error:
                    if (
                        isinstance(upload_error, dict)
                        and upload_error.get("type") == "structured"
                    ):
                        upload_errors.extend(upload_error["errors"])
                    else:
                        upload_errors.append(
                            {
                                "short_message": f"Image Upload Failed: {file.filename}",
                                "long_message": str(upload_error),
                                "error_code": "IMAGE_UPLOAD_ERROR",
                                "severity": "Error",
                                "classification": "RequestError",
                            }
                        )
                else:
                    picture_urls.append(picture_url)

            except Exception as e:
                upload_errors.append(
                    {
                        "short_message": f"Image Processing Failed: {file.filename}",
                        "long_message": f"Failed to process image: {str(e)}",
                        "error_code": "IMAGE_PROCESS_ERROR",
                        "severity": "Error",
                        "classification": "SystemError",
                    }
                )

        # If there were image upload errors, return them
        if upload_errors:
            return templates.TemplateResponse(
                "new_item_form.html",
                {
                    "request": request,
                    "item_id": item_id,
                    "new_item_id": None,
                    "fees": None,
                    "structured_errors": upload_errors,
                    "error": None,
                    "edit_url": None,
                },
            )

        # Create the listing with uploaded images
        new_item_id, fees, add_item_result = ebay_api.add_new_item(
            title or "",
            description or "",
            item_specifics_xml or "",
            picture_urls,
        )

        # Check if it's an actual error (no new_item_id) or just warnings (has new_item_id)
        if add_item_result and not new_item_id:
            # This is an actual error - no listing was created
            if (
                isinstance(add_item_result, dict)
                and add_item_result.get("type") == "structured"
            ):
                return templates.TemplateResponse(
                    "new_item_form.html",
                    {
                        "request": request,
                        "item_id": item_id,
                        "new_item_id": None,
                        "fees": None,
                        "structured_errors": add_item_result["errors"],
                        "error": None,
                        "edit_url": None,
                    },
                )
            else:
                return templates.TemplateResponse(
                    "new_item_form.html",
                    {
                        "request": request,
                        "item_id": item_id,
                        "new_item_id": None,
                        "fees": None,
                        "error": f"Error creating new item: {add_item_result}",
                        "structured_errors": None,
                        "edit_url": None,
                    },
                )

        # Construct the edit draft URL
        edit_url = f"https://www.ebay.com/sl/list?mode=SellLikeItem&draft_id={new_item_id}&ReturnURL=https%3A%2F%2Fwww.ebay.com%2Fsh%2Flst%2Fdrafts&DraftURL=https%3A%2F%2Fwww.ebay.com%2Fsh%2Flst%2Fdrafts"

        # If there are warnings (add_item_result contains warnings), include them with the success
        warnings = None
        if (
            add_item_result
            and isinstance(add_item_result, dict)
            and add_item_result.get("type") == "structured"
        ):
            warnings = add_item_result["errors"]  # These are actually warnings

        return templates.TemplateResponse(
            "new_item_form.html",
            {
                "request": request,
                "item_id": item_id,
                "new_item_id": new_item_id,
                "fees": fees,
                "edit_url": edit_url,
                "error": None,
                "structured_errors": warnings,
            },
        )

    except Exception as e:
        return templates.TemplateResponse(
            "new_item_form.html",
            {
                "request": request,
                "item_id": None,
                "new_item_id": None,
                "fees": None,
                "error": f"Unexpected error: {str(e)}",
                "structured_errors": None,
                "edit_url": None,
            },
        )
