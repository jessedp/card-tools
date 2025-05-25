import os
import json
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Server settings
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8050))

# File paths
OFFER_DATA_FILE = os.environ.get("OFFER_DATA_FILE", "offer_data.json")
SERVER_LOG_FILE = LOGS_DIR / "server.log"

# googs
GOOGLE_GEMINI_API_KEY = os.environ.get("GOOGLE_GEMINI_API_KEY", "")

# eBay OAuth settings
EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET", "")
EBAY_REDIRECT_URI = os.environ.get("EBAY_REDIRECT_URI", "")

ebay_info = json.loads(open("config/ebay_oauth_token.json").read())
EBAY_AUTH_TOKEN = ebay_info.get('AUTH_TOKEN', "")
EBAY_REFRESH_TOKEN = ebay_info.get('REFRESH_TOKEN', "")

# EBAY_AUTH_TOKEN = os.environ.get("EBAY_AUTH_TOKEN", "")
EBAY_SCOPE = (
    "https://api.ebay.com/oauth/api_scope"  # Default scope, modify as needed
)

