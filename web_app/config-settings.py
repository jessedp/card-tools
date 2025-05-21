import os
from pathlib import Path

# Base directories
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# Ensure directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Server settings
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", 8000))

# File paths
OFFER_DATA_FILE = os.environ.get("OFFER_DATA_FILE", "offer_data.json")
LOG_FILE = LOGS_DIR / "web_server.log"

# eBay OAuth settings
EBAY_CLIENT_ID = os.environ.get("EBAY_CLIENT_ID", "")
EBAY_CLIENT_SECRET = os.environ.get("EBAY_CLIENT_SECRET", "")
EBAY_REDIRECT_URI = os.environ.get("EBAY_REDIRECT_URI", "")
EBAY_SCOPE = "https://api.ebay.com/oauth/api_scope"  # Default scope, modify as needed
