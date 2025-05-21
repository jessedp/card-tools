import json
import logging
from pathlib import Path
import aiohttp
from aiohttp import web
from config.settings import DATA_DIR, OFFER_DATA_FILE, EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REDIRECT_URI, EBAY_SCOPE
from web.services.ebay_service import EbayOAuthClient

logger = logging.getLogger('web_server')

async def handle_post(request):
    try:
        data = await request.json()
        action = data.get('action')
        payload = data.get('data')
        
        if not action:
            return web.json_response({"error": "Missing 'action' parameter"}, status=400)
        
        if not payload:
            return web.json_response({"error": "Missing 'data' parameter"}, status=400)
        
        if action == "append-scp-offer-data":
            return await append_offer_data(payload)
        else:
            return web.json_response({"error": f"Unknown action: {action}"}, status=400)
    
    except json.JSONDecodeError:
        return web.json_response({"error": "Invalid JSON payload"}, status=400)
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_get(request):
    action = request.query.get('action')
    
    if not action:
        return web.json_response({"error": "Missing 'action' parameter"}, status=400)
    
    if action == "ebay-oauth-token":
        return await get_ebay_oauth_token(request)
    else:
        return web.json_response({"error": f"Unknown action: {action}"}, status=400)

async def append_offer_data(new_data):
    file_path = DATA_DIR / OFFER_DATA_FILE
    
    try:
        # Create file with empty array if it doesn't exist
        if not file_path.exists():
            with open(file_path, 'w') as f:
                json.dump([], f)
        
        # Read existing data
        with open(file_path, 'r') as f:
            try:
                existing_data = json.load(f)
                if not isinstance(existing_data, list):
                    existing_data = []
            except json.JSONDecodeError:
                existing_data = []
        
        # Append new data
        existing_data.append(new_data)
        
        # Write back to file
        with open(file_path, 'w') as f:
            json.dump(existing_data, f, indent=2)
        
        logger.info(f"Successfully appended data to {OFFER_DATA_FILE}")
        return web.json_response({"success": True})
    
    except Exception as e:
        logger.error(f"Error appending offer data: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

async def get_ebay_oauth_token(request):
    try:
        if not all([EBAY_CLIENT_ID, EBAY_CLIENT_SECRET, EBAY_REDIRECT_URI]):
            return web.json_response(
                {"error": "Missing eBay OAuth credentials in configuration"}, 
                status=500
            )
        
        # Get the authorization code from query parameters if present
        auth_code = request.query.get('code')
        
        # Initialize eBay OAuth client
        ebay_client = EbayOAuthClient(
            client_id=EBAY_CLIENT_ID,
            client_secret=EBAY_CLIENT_SECRET,
            redirect_uri=EBAY_REDIRECT_URI
        )
        
        if not auth_code:
            # If no auth code is provided, redirect to eBay authorization URL
            auth_url = ebay_client.get_authorization_url(EBAY_SCOPE)
            return web.json_response({"authorization_url": auth_url})
        else:
            # Exchange authorization code for access token
            token_data = await ebay_client.get_access_token(auth_code)
            logger.info("Successfully obtained eBay OAuth token")
            return web.json_response(token_data)
            
    except Exception as e:
        logger.error(f"Error getting eBay OAuth token: {str(e)}")
        return web.json_response({"error": str(e)}, status=500)

def setup_routes(app, cors):
    # Add routes
    post_resource = cors.add(app.router.add_resource("/"))
    cors.add(post_resource.add_route("POST", handle_post))
    cors.add(post_resource.add_route("GET", handle_get))
    
    logger.info("Routes have been set up")
