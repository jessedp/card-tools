import logging
from urllib.parse import urlencode
import aiohttp
import base64

logger = logging.getLogger('web_server')

class EbayOAuthClient:
    """Client for handling eBay OAuth authentication."""
    
    def __init__(self, client_id, client_secret, redirect_uri, sandbox=False):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.sandbox = sandbox
        
        # API endpoints
        if sandbox:
            self.auth_url = "https://auth.sandbox.ebay.com/oauth2/authorize"
            self.token_url = "https://api.sandbox.ebay.com/identity/v1/oauth2/token"
        else:
            self.auth_url = "https://auth.ebay.com/oauth2/authorize"
            self.token_url = "https://api.ebay.com/identity/v1/oauth2/token"
    
    def get_authorization_url(self, scope):
        """Generate the authorization URL to redirect the user to."""
        params = {
            'client_id': self.client_id,
            'response_type': 'code',
            'redirect_uri': self.redirect_uri,
            'scope': scope
        }
        return f"{self.auth_url}?{urlencode(params)}"
    
    async def get_access_token(self, auth_code):
        """Exchange the authorization code for an access token."""
        # Create basic auth header
        auth_string = f"{self.client_id}:{self.client_secret}"
        encoded_auth = base64.b64encode(auth_string.encode()).decode()
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Authorization': f'Basic {encoded_auth}'
        }
        
        data = {
            'grant_type': 'authorization_code',
            'code': auth_code,
            'redirect_uri': self.redirect_uri
        }
        
        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.token_url, headers=headers, data=data) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        error_text = await response.text()
                        logger.error(f"eBay OAuth error: {error_text}")
                        raise Exception(f"eBay OAuth error: {response.status}, {error_text}")
            except Exception as e:
                logger.error(f"Error in eBay OAuth request: {str(e)}")
                raise
