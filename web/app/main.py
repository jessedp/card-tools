import os
import hashlib
import json

from urllib.parse import urlparse

from fastapi import FastAPI, UploadFile, File, HTTPException, Query, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import httpx

from web.app.ebay import search_ebay_by_image, get_ebay_orders
from web.app.logger import setup_logger
from analyze_card import analyze_trading_card, OCRResponse


from .routers import pubsub

from typing import Optional

import gspread
from google.oauth2.service_account import Credentials

logger = setup_logger()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
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


async def add_order_to_sheets(order: dict):
    # Google Sheets API configuration
    # Replace with your actual credentials file path
    credentials_path = "web/app/credentials.json"
    # Replace with your actual spreadsheet ID
    spreadsheet_id = "1RQENLNjh4ULFAwGkyjIpibnZASaIqEkpCyLBVVWdGkA"
    sheet_name = "Sheet1"

    try:
        # Authenticate with Google Sheets API
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )
        gc = gspread.service_account(filename=credentials_path)

        # Open the spreadsheet and get the worksheet
        sh = gc.open_by_key(spreadsheet_id)

        worksheet = sh.worksheet(sheet_name)

        # Extract the required data from the order
        order_id = order.get("orderId", "")

        # Extract lastModifiedDate from paymentSummary
        payment_summary = order.get("paymentSummary", {})
        payments = payment_summary.get("payments", [])
        sale_date = payments[0].get("paymentDate", "") if payments else ""

        line_items = order.get("lineItems", [])
        desc = "\\n".join([item.get("title", "") for item in line_items])
        sold = sum(
            float(item.get("lineItemCost", {}).get("value", 0))
            for item in line_items
        )
        shipping = sum(
            float(
                item.get("deliveryCost", {})
                .get("shippingCost", {})
                .get("value", 0)
            )
            for item in line_items
            if item.get("deliveryCost")
            and item.get("deliveryCost").get("shippingCost")
        )
        total_marketplace_fee = order.get("totalMarketplaceFee", {}).get(
            "value", 0
        )

        # Prepare the data for Google Sheets
        data = [
            sale_date,  # A
            order_id,  # B
            desc,  # C
            "",  # D (empty)
            "",  # E (empty)
            sold,  # F
            shipping,  # G
            "",  # H (empty)
            "",  # I (empty)
            total_marketplace_fee,  # J
        ]

        # Find the first empty row based on the sale_date column (column A)
        sale_dates = worksheet.col_values(1)  # Column A
        first_empty_row = len(sale_dates) + 1

        # Add the data to the first empty row
        worksheet.insert_row(data, first_empty_row)

        return {"message": "Order added to Google Sheets successfully!"}

    except Exception as e:
        logger.error(f"Google Sheets API error: {e}")
        logger.info(f"Google Sheets API error: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to add to Google Sheets: {str(e)}"
        )


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


@app.get("/ebay-orders")
async def ebay_orders_page():
    return FileResponse("web/static/ebay-orders.html")


# logger.info("OCR data FROM CACHE...")
async def add_order_to_sheets2(order: dict):
    # Google Sheets API configuration
    # Replace with your actual credentials file path
    credentials_path = "web/app/credentials.json"
    # Replace with your actual spreadsheet ID
    spreadsheet_id = "your-spreadsheet-id"
    sheet_name = "Sheet1"

    try:
        # Authenticate with Google Sheets API
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        credentials = Credentials.from_service_account_file(
            credentials_path, scopes=scopes
        )
        gc = gspread.service_account(filename=credentials_path)

        # Open the spreadsheet and get the worksheet
        sh = gc.open_by_key(spreadsheet_id)
        worksheet = sh.worksheet(sheet_name)

        # Extract the required data from the order
        order_id = order.get("orderId", "")

        # Extract lastModifiedDate from paymentSummary
        payment_summary = order.get("paymentSummary", {})
        payments = payment_summary.get("payments", [])
        sale_date = payments[0].get("paymentDate", "") if payments else ""

        line_items = order.get("lineItems", [])
        desc = "\\n".join([item.get("title", "") for item in line_items])
        sold = sum(
            float(item.get("lineItemCost", {}).get("value", 0))
            for item in line_items
        )
        shipping = sum(
            float(
                item.get("deliveryCost", {})
                .get("shippingCost", {})
                .get("value", 0)
            )
            for item in line_items
            if item.get("deliveryCost")
            and item.get("deliveryCost").get("shippingCost")
        )
        total_marketplace_fee = order.get("totalMarketplaceFee", {}).get(
            "value", 0
        )

        # Prepare the data for Google Sheets
        data = [
            sale_date,  # A
            order_id,  # B
            desc,  # C
            "",  # D (empty)
            "",  # E (empty)
            sold,  # F
            shipping,  # G
            "",  # H (empty)
            "",  # I (empty)
            total_marketplace_fee,  # J
        ]

        # Find the first empty row based on the sale_date column (column A)
        sale_dates = worksheet.col_values(1)  # Column A
        first_empty_row = len(sale_dates) + 1

        # Add the data to the first empty row
        worksheet.insert_row(data, first_empty_row)

        return {"message": "Order added to Google Sheets successfully!"}

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add to Google Sheets: {str(e)}"
        )
    # Extract the required data from the order
    order_id = order.get("orderId", "")

    # Extract lastModifiedDate from paymentSummary
    payment_summary = order.get("paymentSummary", {})
    payments = payment_summary.get("payments", [])
    sale_date = payments[0].get("paymentDate", "") if payments else ""

    line_items = order.get("lineItems", [])
    desc = "\\n".join([item.get("title", "") for item in line_items])
    sold = sum(
        float(item.get("lineItemCost", {}).get("value", 0))
        for item in line_items
    )
    shipping = sum(
        float(
            item.get("deliveryCost", {}).get("shippingCost", {}).get("value", 0)
        )
        for item in line_items
        if item.get("deliveryCost")
        and item.get("deliveryCost").get("shippingCost")
    )
    total_marketplace_fee = order.get("totalMarketplaceFee", {}).get("value", 0)

    # Prepare the data for Google Sheets
    data = {
        "order_id": order_id,
        "sale_date": sale_date,
        "desc": desc,
        "sold": sold,
        "shipping": shipping,
        "fees": total_marketplace_fee,
    }
    # Replace with your actual Google Sheets API endpoint
    google_sheets_api_url = "https://your-google-sheets-api.com/add-row"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(google_sheets_api_url, json=data)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"Google Sheets API error: {e.response.text}",
        )


@app.post("/api/add-to-sheets")
async def add_to_sheets(order: dict):
    try:
        return await add_order_to_sheets(order)
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to add to Google Sheets: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to add to Google Sheets: {str(e)}",
        )


@app.get("/api/ebay-orders")
async def ebay_orders():
    try:
        results = get_ebay_orders()
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
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/ebay-orders")
async def ebay_orders_page():
    return FileResponse("web/static/ebay-orders.html")
