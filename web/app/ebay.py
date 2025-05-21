import os
import time
import requests
from dotenv import load_dotenv
import base64

load_dotenv()

CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
MARKETPLACE_ID = "EBAY_US"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"

_token_cache = {"access_token": None, "expires_at": 0}


def get_ebay_token():
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

    data = {
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }
    
    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    result = response.json()

    _token_cache["access_token"] = result["access_token"]
    _token_cache["expires_at"] = (
        current_time + result["expires_in"] - 60
    )  # buffer of 60 seconds

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
