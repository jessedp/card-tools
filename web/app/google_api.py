from fastapi import HTTPException
import gspread
from google.oauth2.service_account import Credentials

from .logger import setup_logger

logger = setup_logger()


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
