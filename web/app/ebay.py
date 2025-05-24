import os
import time
import requests
from dotenv import load_dotenv
import base64
import json
import gzip
from urllib.parse import quote
from .logger import setup_logger

load_dotenv()

logger = setup_logger("ebay")

AUTH_TOKEN = os.getenv("EBAY_AUTH_TOKEN")
CLIENT_ID = os.getenv("EBAY_CLIENT_ID")
CLIENT_SECRET = os.getenv("EBAY_CLIENT_SECRET")
MARKETPLACE_ID = "EBAY_US"
TOKEN_URL = "https://api.ebay.com/identity/v1/oauth2/token"
OAUTH_TOKEN_FILE = "config/ebay_oauth_token.json"

_token_cache = {"access_token": None, "expires_at": 0}

"""
Get an eBay application level access token using client credentials.
"""

def get_ebay_user_token():
    """
    Get a valid eBay user token, handling refresh and validation.

    This function:
    1. Checks if AUTH_TOKEN is empty - raises exception if so
    2. Validates if AUTH_TOKEN is expired by parsing the token structure
    3. If expired and REFRESH_TOKEN exists, refreshes the token automatically
    4. If expired and no REFRESH_TOKEN, provides OAuth URL for re-authentication
    5. Updates the token file with new tokens when refreshed

    Returns:
        str: A valid AUTH_TOKEN

    Raises:
        Exception: If AUTH_TOKEN is empty, refresh fails, or token file issues
    """
    # Read tokens from JSON file
    token_data = _load_token_data()

    auth_token = token_data.get("AUTH_TOKEN", "").strip()
    refresh_token = token_data.get("REFRESH_TOKEN", "").strip()

    # Check if AUTH_TOKEN is empty
    if not auth_token:
        raise Exception("AUTH_TOKEN is empty. Please provide a valid eBay user token.")

    # Check if token is expired
    if _is_token_expired(auth_token):
        logger.info("AUTH_TOKEN is expired, attempting to refresh...")

        if not refresh_token:
            # If no refresh token, we need to get one through OAuth flow
            auth_url_example = generate_oauth_authorization_url("jesse_peterson-jessepet-UserSc-dhzfjwzn")
            raise Exception(
                "AUTH_TOKEN is expired and REFRESH_TOKEN is empty. "
                "Please re-authenticate through eBay's OAuth flow to obtain new tokens. "
                f"You can start the process by visiting: {auth_url_example} "
                "(Replace the redirect_uri with your actual registered redirect URI)"
            )

        # Refresh the token
        try:
            new_auth_token, new_refresh_token, expires_at = _refresh_user_token(refresh_token)

            # Update token data
            token_data["AUTH_TOKEN"] = new_auth_token
            token_data["EXPIRES_AT"] = expires_at
            if new_refresh_token:  # eBay may return a new refresh token
                token_data["REFRESH_TOKEN"] = new_refresh_token

            # Save updated tokens
            _save_token_data(token_data)

            logger.info(f"Successfully refreshed AUTH_TOKEN (expires at {expires_at})")
            return new_auth_token

        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            raise Exception(
                f"Failed to refresh expired AUTH_TOKEN: {e}. "
                "Please re-authenticate through eBay's OAuth flow."
            )

    # Token is valid, return it
    return auth_token


def _load_token_data():
    """
    Load token data from JSON file.

    Returns:
        dict: Token data containing AUTH_TOKEN, REFRESH_TOKEN, and EXPIRES_AT

    Raises:
        Exception: If file not found or contains invalid JSON
    """
    try:
        with open(OAUTH_TOKEN_FILE, 'r') as f:
            token_data = json.load(f)
        
        # Migrate existing token file if it doesn't have EXPIRES_AT
        if "EXPIRES_AT" not in token_data and token_data.get("AUTH_TOKEN"):
            logger.info("Migrating token file to include EXPIRES_AT field")
            # For existing tokens without expiration, assume they expire in 2 hours
            # This will trigger a refresh on next use, which is safe
            token_data["EXPIRES_AT"] = int(time.time()) + 7200
            _save_token_data(token_data)
            
        return token_data
    except FileNotFoundError:
        raise Exception(f"Token file {OAUTH_TOKEN_FILE} not found.")
    except json.JSONDecodeError as e:
        raise Exception(f"Invalid JSON in token file {OAUTH_TOKEN_FILE}: {e}")


def _save_token_data(token_data):
    """
    Save token data to JSON file.

    Args:
        token_data (dict): Token data to save

    Raises:
        Exception: If file cannot be written
    """
    try:
        with open(OAUTH_TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save token data: {e}")
        raise Exception(f"Failed to save updated tokens to {OAUTH_TOKEN_FILE}: {e}")


def _is_token_expired(auth_token):
    """
    Check if eBay user token is expired using stored expiration time.
    
    Uses the EXPIRES_AT field stored in the OAuth token file to determine expiration.
    If no expiration time is stored, considers the token expired to force refresh.

    Args:
        auth_token (str): eBay user token to check

    Returns:
        bool: True if token is expired or will expire within 5 minutes, False if valid
    """
    try:
        # Load token data to check stored expiration
        token_data = _load_token_data()
        expires_at = token_data.get("EXPIRES_AT")
        
        if not expires_at:
            logger.warning("No EXPIRES_AT found in token file - considering expired")
            return True
        
        current_time = int(time.time())
        # Consider expired if expiring within 5 minutes (300 seconds)
        buffer_time = 300
        
        is_expired = current_time >= (expires_at - buffer_time)
        logger.info(f"Token expires at {expires_at}, current time {current_time}, expired: {is_expired}")
        
        return is_expired

    except Exception as e:
        logger.warning(f"Error checking token expiration: {e}")
        # If we can't determine expiration, consider it expired to force refresh
        return True


def _refresh_user_token(refresh_token):
    """
    Refresh eBay user token using refresh token.

    Args:
        refresh_token (str): Valid refresh token

    Returns:
        tuple: (new_auth_token, new_refresh_token or None, expires_at)

    Raises:
        Exception: If refresh request fails or no access_token received
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + _encode_credentials(),
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)

    if response.status_code != 200:
        raise Exception(f"Token refresh failed with status {response.status_code}: {response.text}")

    result = response.json()

    new_auth_token = result.get("access_token")
    new_refresh_token = result.get("refresh_token")  # May be None if not provided
    expires_in = result.get("expires_in", 7200)  # Default to 2 hours if not provided

    if not new_auth_token:
        raise Exception("No access_token received in refresh response")

    # Calculate expiration timestamp
    expires_at = int(time.time()) + expires_in

    return new_auth_token, new_refresh_token, expires_at


def generate_oauth_authorization_url(redirect_uri, state=None):
    """
    Generate eBay OAuth authorization URL for obtaining initial tokens.

    Use this when you need to get initial tokens or when refresh token is empty.
    User must visit this URL, grant permissions, and you'll receive an authorization
    code that can be exchanged for tokens using exchange_code_for_tokens().

    Args:
        redirect_uri (str): The redirect URI registered with your eBay application
        state (str, optional): State parameter for security (recommended)

    Returns:
        str: Authorization URL that user should visit to grant permissions
    """
    base_url = "https://auth.ebay.com/oauth2/authorize"

    # Required scopes for selling operations
    scopes = [
        "https://api.ebay.com/oauth/api_scope",
        "https://api.ebay.com/oauth/api_scope/sell.marketing.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.marketing",
        "https://api.ebay.com/oauth/api_scope/sell.inventory.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.inventory",
        "https://api.ebay.com/oauth/api_scope/sell.account.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.account",
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.fulfillment",
        "https://api.ebay.com/oauth/api_scope/sell.analytics.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.finances",
        "https://api.ebay.com/oauth/api_scope/sell.payment.dispute",
        "https://api.ebay.com/oauth/api_scope/commerce.identity.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.reputation",
        "https://api.ebay.com/oauth/api_scope/sell.reputation.readonly",
        "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription",
        "https://api.ebay.com/oauth/api_scope/commerce.notification.subscription.readonly",
        "https://api.ebay.com/oauth/api_scope/sell.stores",
        "https://api.ebay.com/oauth/api_scope/sell.stores.readonly",
        "https://api.ebay.com/oauth/scope/sell.edelivery"

    ]

    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": redirect_uri,
        "scope": " ".join(scopes),
    }

    if state:
        params["state"] = state

    # Build URL
    param_string = "&".join([f"{k}={quote(str(v))}" for k, v in params.items()])
    auth_url = f"{base_url}?{param_string}"

    return auth_url


def exchange_code_for_tokens(authorization_code, redirect_uri):
    """
    Exchange authorization code for access and refresh tokens.

    Call this after user visits the OAuth URL and grants permissions.
    eBay will redirect to your redirect_uri with an authorization code.
    This function exchanges that code for actual tokens and saves them to file.

    Args:
        authorization_code (str): The code received from eBay after user authorization
        redirect_uri (str): The same redirect URI used in the authorization request

    Returns:
        dict: Dictionary with 'access_token' and 'refresh_token' keys

    Raises:
        Exception: If token exchange fails or tokens are not received
    """
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + _encode_credentials(),
    }

    data = {
        "grant_type": "authorization_code",
        "code": authorization_code,
        "redirect_uri": redirect_uri,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)

    if response.status_code != 200:
        raise Exception(f"Token exchange failed with status {response.status_code}: {response.text}")

    result = response.json()

    access_token = result.get("access_token")
    refresh_token = result.get("refresh_token")
    expires_in = result.get("expires_in", 7200)  # Default to 2 hours if not provided

    if not access_token or not refresh_token:
        raise Exception("Did not receive both access_token and refresh_token in response")

    # Calculate expiration timestamp
    expires_at = int(time.time()) + expires_in

    # Save tokens with expiration time
    token_data = {
        "AUTH_TOKEN": access_token,
        "REFRESH_TOKEN": refresh_token,
        "EXPIRES_AT": expires_at
    }
    _save_token_data(token_data)

    logger.info(f"Successfully obtained and saved new tokens (expires at {expires_at})")

    return {
        "access_token": access_token,
        "refresh_token": refresh_token
    }


# Example usage for OAuth flow:
"""
EXAMPLE USAGE FOR INITIAL SETUP (when you have no tokens):

1. Generate authorization URL:
   auth_url = generate_oauth_authorization_url("https://yourapp.com/callback")
   print(f"Visit this URL to authorize: {auth_url}")

2. User visits URL, grants permissions, gets redirected with authorization code

3. Exchange code for tokens:
   tokens = exchange_code_for_tokens(authorization_code, "https://yourapp.com/callback")
   # This automatically saves tokens to config/ebay_oauth_token.json

4. Now you can use get_ebay_user_token() which will handle refresh automatically

EXAMPLE USAGE FOR NORMAL OPERATIONS (after initial setup):

try:
    user_token = get_ebay_user_token()
    # Use user_token for eBay API calls that require user authentication

except Exception as e:
    print(f"Token error: {e}")
    # If refresh fails, you may need to re-authenticate using steps 1-3 above
"""

def get_ebay_token(user: bool = False):
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

    # scopes = "https://api.ebay.com/oauth/api_scope/sell.fulfillment https://api.ebay.com/oauth/api_scope/sell.fulfillment.readonly"
    scopes = "https://api.ebay.com/oauth/api_scope"

    data = {
        "grant_type": "client_credentials",
        "scope": scopes,
    }

    response = requests.post(TOKEN_URL, headers=headers, data=data)
    response.raise_for_status()
    result = response.json()
    logger.info("result...", result)
    # pprint.pprint(result)

    _token_cache["access_token"] = result["access_token"]
    _token_cache["expires_at"] = (
        current_time + result["expires_in"] - 60
    )  # buffer of 60 seconds
    print(f"eBay scopes: {result.get("scope", "")}")
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
        "Authorization": f"Bearer {get_ebay_user_token()}",
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
