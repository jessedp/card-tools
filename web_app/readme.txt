# Web API Server

A simple Python web server that handles JSON data operations and eBay OAuth integration.

## Project Structure

```
project_root/
├── README.md              # This file
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore file
├── config/                # Configuration files
│   └── settings.py        # Central place for settings
├── scripts/               # Shell scripts
│   └── utils/             # Shared utilities
├── web/                   # Web server code
│   ├── app.py             # Main web application
│   ├── routes.py          # URL routing
│   ├── middleware.py      # Middleware components
│   └── services/          # Service modules
│       └── ebay_service.py # eBay OAuth handling
├── data/                  # Data files 
├── logs/                  # Output logs
└── supervisor.py          # Script to control the server
```

## Setup

1. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```
   export PORT=8000
   export OFFER_DATA_FILE=offer_data.json
   export EBAY_CLIENT_ID=your_client_id
   export EBAY_CLIENT_SECRET=your_client_secret
   export EBAY_REDIRECT_URI=your_redirect_uri
   ```

   Alternatively, create a `.env` file in the project root.

## Running the Server

Use the supervisor script to manage the server:

```
# Start the server
python supervisor.py start

# Stop the server
python supervisor.py stop

# Restart the server
python supervisor.py restart

# Check server status
python supervisor.py status
```

## API Endpoints

### POST /

Appends data to an offer data file.

**Parameters:**
- `action`: Must be "append-scp-offer-data"
- `data`: JSON object to append

**Example Request:**
```json
{
  "action": "append-scp-offer-data",
  "data": {
    "id": "12345",
    "name": "Example Offer",
    "price": 19.99
  }
}
```

### GET /?action=ebay-oauth-token

Gets an OAuth token from eBay.

**Response:**
- If no code is provided, returns an authorization URL
- If code is provided as a query parameter, returns the token data

## License

[Your License Here]
