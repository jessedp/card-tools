import os
import time
import requests
from dotenv import load_dotenv
import base64

load_dotenv()

AUTH_TOKEN = os.getenv("EBAY_AUTH_TOKEN")
CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
MARKETPLACE_ID = "EBAY_US"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

_token_cache = {"access_token": None, "expires_at": 0}

"""
Get an eBay application level access token using client credentials.
"""


def get_ebay_token(user: bool = False):
    if user:
        return AUTH_TOKEN
    current_time = time.time()
    if (
        _token_cache["access_token"]
        and _token_cache["expires_at"] is not None
        and current_time < _token_cache["expires_at"]
    ):
        return _token_cache["access_token"]

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + _encode_credentials(),
    }

    scopes = "https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly"
    # scopes = "https://api.ebay.com/oauth/api_scope"

    data = {
        "grant_type": "client_credentials",
        "scope": scopes,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    result = response.json()

    _token_cache["access_token"] = result["access_token"]
    _token_cache["expires_at"] = (
        current_time + result["expires_in"] - 60
    )  # buffer of 60 seconds

    # Check if the token has the required scopes
    # if scopes not in result.get("scope", ""):
    #     raise Exception(
    #         f"The eBay token does not have the required scopes ({scopes}). "
    #         f"The granted scopes are: {result.get('scope', '')}. "
    #         "Please update the application's OAuth configuration to include these scopes."
    #     )

    return _token_cache["access_token"]


def _encode_credentials():

    credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
    return base64.b64encode(credentials.encode()).decode()


def search_ebay_by_image(image_bytes: bytes, image_type: str):
    headers = {
        "Authorization": f"Bearer {get_ebay_token()}",
        "Content-Type": "application/json",
        "X-EBAY-C-MARKETPLACE-ID": MARKETPLACE_ID,
    }

    url = "https://api.ebay.com/buy/browse/v1/item_summary/search_by_image"

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")

    params = {"filter": "itemEndDate:[..2025-05-20T00:00:00Z]"}
    payload = {"image": image_base64}  # The API expects base64-encoded string

    response = requests.post(url, headers=headers, json=payload, params=params)
    response.raise_for_status()
    return response.json()


def get_ebay_orders():
    headers = {
        "Authorization": f"Bearer {get_ebay_token(user=True)}",
        "Content-Type": "application/json",
    }

    url = "https://api.ebay.com/sell/fulfillment/v1/order"
    orders = []
    offset = 0
    limit = 100  # Maximum allowed limit

    while True:
        params = {
            "limit": limit,
            "offset": offset,
            # "filter": "orderfulfillmentstatus:{FULFILLED|IN_PROGRESS}",
        }

        response = requests.get(url, headers=headers, params=params)

        try:
            response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
            data = response.json()
            orders.extend(data.get("orders", []))
            break
            if data.get("total") is None or len(orders) >= data.get("total"):
                break

            offset += limit

        except requests.exceptions.HTTPError as e:
            print(f"HTTP error occurred: {e}")
            print(f"Response status code: {response.status_code}")
            print(f"Response text: {response.text}")
            break  # Exit the loop if there's an error

        except Exception as e:
            print(f"An error occurred: {e}")
            break  # Exit the loop if there's an error

    return orders
