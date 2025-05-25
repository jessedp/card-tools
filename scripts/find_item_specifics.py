#!/usr/bin/env python3
"""
Script to search eBay for items in a specific category (default: 261328 - sports trading cards),
extract item specifics, and collect them in a structured JSON file.

This script uses eBay's Browse API to search for items in category 261328 and
for each item retrieves the details to extract ItemSpecifics.
"""

import os
import sys
import json
import argparse
import requests
import time
import logging
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET
from urllib.parse import quote

# Add the parent directory to the path so we can import from web.app
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
)
from web.app.ebay_api import get_item_details
from web.app.ebay_auth import get_ebay_token
from web.app.logger import setup_logger

# Constants
CATEGORY_ID = "261328"  # Sports Trading Cards
EBAY_BROWSE_API_URL = "https://api.ebay.com/buy/browse/v1"
ITEM_SPECIFICS_FILE = "data/item_specifics.json"

logger = setup_logger("item_specifics")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Search eBay for items and collect their specifics."
    )
    parser.add_argument(
        "--start-date", type=str, help="Start date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date", type=str, help="End date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to look back if no dates provided",
    )
    parser.add_argument(
        "--entries",
        type=int,
        default=100,
        help="Number of search entries to process",
    )
    parser.add_argument(
        "--debug", action="store_true", help="Enable debug logging"
    )
    return parser.parse_args()


def get_date_range(args):
    """Get start and end dates based on args."""
    if args.start_date and args.end_date:
        start_date = datetime.strptime(args.start_date, "%Y-%m-%d")
        end_date = datetime.strptime(args.end_date, "%Y-%m-%d")
    else:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=args.days)

    return start_date.strftime("%Y-%m-%dT00:00:00.000Z"), end_date.strftime(
        "%Y-%m-%dT23:59:59.999Z"
    )


def search_ebay_items(
    category_id, max_entries=100, start_date=None, end_date=None, debug=False
):
    """
    Search eBay for items in a specific category using the Browse API.
    Returns a list of item IDs.
    """
    token = get_ebay_token()
    if not token:
        logger.error("Failed to get eBay OAuth token.")
        return []

    # Set up headers for the Browse API
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
    }

    # Create the API URL with query parameters
    # Setting limit to 50 per request (API maximum)
    limit = min(50, max_entries)
    url = f"{EBAY_BROWSE_API_URL}/item_summary/search?category_ids={category_id}&limit={limit}"

    # Add date filters if provided
    filter_params = []
    if start_date and end_date:
        # Format for the filter is: filter=itemEndDate:[2016-10-25T00:00:01.000Z..2016-11-25T23:59:59.000Z]
        filter_params.append(f"itemEndDate:[{start_date}..{end_date}]")

    # Add filter to get only fixed price items, which are more likely to have complete item specifics
    filter_params.append("buyingOptions:{FIXED_PRICE}")

    if filter_params:
        url += f"&filter={quote(','.join(filter_params))}"

    item_ids = []
    offset = 0
    total_collected = 0

    logger.info(f"Searching for items in category {category_id}")

    try:
        while total_collected < max_entries:
            logger.debug(f"Making Browse API request with offset {offset}")
            logger.debug(f"Request URL: {url}&offset={offset}")

            # Make the request
            response = requests.get(f"{url}&offset={offset}", headers=headers)

            # Check if successful
            if response.status_code != 200:
                logger.error(
                    f"Error in Browse API request: {response.status_code}"
                )
                logger.error(f"Response: {response.text[:1000]}")
                break

            # Parse the response
            data = response.json()

            # Extract item IDs
            if "itemSummaries" in data:
                for item in data["itemSummaries"]:
                    # Extract the middle part of the item ID (e.g., "306301462145" from "v1|306301462145|605976574136")
                    full_item_id = item["itemId"]
                    try:
                        # Split by '|' and take the second part
                        legacy_item_id = full_item_id.split("|")[1]
                        item_ids.append(legacy_item_id)
                        logger.debug(
                            f"Extracted item ID: {legacy_item_id} from {full_item_id}"
                        )

                        # Also log the item title for debugging
                        if "title" in item:
                            logger.debug(f"Item title: {item['title']}")
                    except IndexError:
                        # Fallback to using the full ID if parsing fails
                        logger.warning(
                            f"Could not parse legacy item ID from {full_item_id}, using as-is"
                        )
                        item_ids.append(full_item_id)

                    total_collected += 1

                    # Break if we've reached our target
                    if total_collected >= max_entries:
                        break

                # Check if there are more items to fetch
                if "next" in data and total_collected < max_entries:
                    offset += limit
                    logger.info(
                        f"Collected {total_collected}/{max_entries} items, fetching more..."
                    )
                else:
                    break
            else:
                logger.info("No more items found in response")
                break

            # Add a small delay to avoid rate limiting
            time.sleep(0.5)

    except Exception as e:
        logger.error(f"Error searching eBay with Browse API: {str(e)}")

    logger.info(f"Found {len(item_ids)} items in category {category_id}")
    return item_ids


def parse_item_specifics(item_specifics_xml):
    """
    Parse item specifics XML into a dictionary.
    Returns a dictionary of name-value pairs.
    """
    if not item_specifics_xml:
        logger.debug("No item specifics XML provided")
        return {}
    item_specifics_xml = item_specifics_xml.replace("ns0:", "")
    try:
        # logger.error(f"ItemSpecfics XML {item_specifics_xml}")
        # Create a proper XML from the fragment
        xml_string = f"<Root>{item_specifics_xml}</Root>"
        root = ET.fromstring(xml_string)

        result = {}
        for name_value_list in root.findall(".//NameValueList"):
            name_elem = name_value_list.find("Name")
            value_elem = name_value_list.find("Value")

            if name_elem is not None and value_elem is not None:
                name = name_elem.text
                value = value_elem.text
                if name and value:
                    result[name] = value

        logger.debug(f"Parsed {len(result)} item specifics")
        return result

    except ET.ParseError as e:
        logger.error(f"Failed to parse item specifics XML: {str(e)}")
        logger.error(f"XML snippet: {item_specifics_xml[:100]}...")
        return {}


def load_existing_specifics():
    """
    Load existing item specifics from the JSON file if it exists.
    """
    if os.path.exists(ITEM_SPECIFICS_FILE):
        try:
            with open(ITEM_SPECIFICS_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(
                f"Error parsing {ITEM_SPECIFICS_FILE}, creating new file"
            )

    return []


def update_item_specifics(existing_specifics, new_specifics):
    """
    Update the existing specifics with new ones.
    Returns the updated list of specifics.
    """
    for name, value in new_specifics.items():
        # Skip empty values
        if not value or value.strip() == "":
            continue

        # Find if this name already exists
        found = False
        for item in existing_specifics:
            if item["name"] == name:
                # If value not already in list, add it
                if value not in item["value"]:
                    item["value"].append(value)
                found = True
                break

        # If not found, add a new entry
        if not found:
            existing_specifics.append({"name": name, "value": [value]})

    return existing_specifics


def save_item_specifics(specifics):
    """
    Save the item specifics to a JSON file.
    """
    os.makedirs(os.path.dirname(ITEM_SPECIFICS_FILE), exist_ok=True)
    with open(ITEM_SPECIFICS_FILE, "w") as f:
        json.dump(specifics, f, indent=2)

    logger.info(f"Saved item specifics to {ITEM_SPECIFICS_FILE}")


def main():
    """Main function to execute the script."""
    args = parse_args()

    # Set logger to debug level if requested
    if args.debug:
        logger.setLevel(logging.DEBUG)
        logger.debug("Debug mode enabled")

    # Get date range if specified
    start_date, end_date = get_date_range(args)
    logger.info(f"Using date range: {start_date} to {end_date}")

    # Search for items
    item_ids = search_ebay_items(
        CATEGORY_ID, args.entries, start_date, end_date, args.debug
    )

    if not item_ids:
        logger.error("No items found. Exiting.")
        return

    # Load existing specifics
    item_specifics = load_existing_specifics()
    logger.info(f"Loaded {len(item_specifics)} existing item specifics")

    # Process each item
    processed_count = 0
    error_count = 0
    start_time = time.time()
    total_items = len(item_ids)

    for i, item_id in enumerate(item_ids):
        try:
            # Calculate progress and ETA
            percent_complete = (i / total_items) * 100
            elapsed_time = time.time() - start_time
            items_per_sec = i / elapsed_time if elapsed_time > 0 else 0
            remaining_items = total_items - i
            eta_seconds = (
                remaining_items / items_per_sec if items_per_sec > 0 else 0
            )
            eta_str = (
                f"{int(eta_seconds // 60)}m {int(eta_seconds % 60)}s"
                if eta_seconds > 0
                else "unknown"
            )

            logger.info(
                f"Processing item {item_id} ({i+1}/{total_items}, {percent_complete:.1f}%, ETA: {eta_str})"
            )

            # Get item details using the existing method
            title, description, item_specifics_xml, error = get_item_details(
                item_id
            )

            if error:
                logger.error(
                    f"Error getting details for item {item_id}: {error}"
                )
                error_count += 1
                continue

            # Parse item specifics
            specifics_dict = parse_item_specifics(item_specifics_xml)

            if specifics_dict:
                # Update item specifics
                item_specifics = update_item_specifics(
                    item_specifics, specifics_dict
                )
                processed_count += 1

                # Log the number of specifics found for this item
                logger.debug(
                    f"Found {len(specifics_dict)} specifics for item {item_id}"
                )
            else:
                logger.warning(f"No item specifics found for item {item_id}")

            # Sleep to avoid hitting rate limits
            time.sleep(0.5)

        except Exception as e:
            logger.error(f"Error processing item {item_id}: {str(e)}")
            error_count += 1

    # Save results
    save_item_specifics(item_specifics)

    # Calculate stats
    total_values = sum(len(item["value"]) for item in item_specifics)
    total_names = len(item_specifics)

    # Log results
    logger.info(f"Script completed in {time.time() - start_time:.1f} seconds")
    logger.info(
        f"Processed {processed_count} items successfully, {error_count} errors"
    )
    logger.info(
        f"Collected {total_names} unique item specific names with {total_values} total values"
    )
    logger.info(f"Results saved to {ITEM_SPECIFICS_FILE}")


if __name__ == "__main__":
    main()
