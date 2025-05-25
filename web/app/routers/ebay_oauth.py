from fastapi import APIRouter

from fastapi import Query, Response
from fastapi.responses import FileResponse, JSONResponse

from web.app.ebay_auth import (
    generate_oauth_authorization_url,
    exchange_code_for_tokens,
)

from web.app.logger import setup_logger

from typing import Optional
import time

router = APIRouter()

logger = setup_logger(__name__)


@router.get("/api/ebay-oauth-url")
async def get_ebay_oauth_url():
    """Generate eBay OAuth authorization URL for popup authentication."""
    try:
        # Use eBay RuName - eBay will redirect to configured callback URLs
        redirect_uri = "jesse_peterson-jessepet-UserSc-dhzfjwzn"
        state = "ebay_oauth_" + str(
            int(time.time())
        )  # Add timestamp for security

        auth_url = generate_oauth_authorization_url(redirect_uri, state)

        return JSONResponse(content={"auth_url": auth_url, "state": state})
    except Exception as e:
        logger.error(f"Failed to generate OAuth URL: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/ebay-oauth-accept")
async def ebay_oauth_accept(
    code: Optional[str] = Query(None),
    state: Optional[str] = Query(None),
    error: Optional[str] = Query(None),
):
    """Handle eBay OAuth accept callback and return a page that communicates with popup opener."""
    if error:
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>eBay OAuth Error</title>
        </head>
        <body>
            <h1>Authorization Error</h1>
            <p>Error: {error}</p>
            <script>
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'ebay_oauth_error',
                        error: '{error}'
                    }}, '*');
                    window.close();
                }} else {{
                    document.body.innerHTML += '<p>Please close this window and try again.</p>';
                }}
            </script>
        </body>
        </html>
        """
        return Response(content=html_content, media_type="text/html")

    if not code:
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>eBay OAuth Error</title>
        </head>
        <body>
            <h1>Authorization Error</h1>
            <p>No authorization code received.</p>
            <script>
                if (window.opener) {
                    window.opener.postMessage({
                        type: 'ebay_oauth_error',
                        error: 'No authorization code received'
                    }, '*');
                    window.close();
                } else {
                    document.body.innerHTML += '<p>Please close this window and try again.</p>';
                }
            </script>
        </body>
        </html>
        """
        return Response(content=html_content, media_type="text/html")

    # Return success page that communicates with popup opener
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>eBay OAuth Success</title>
    </head>
    <body>
        <h1>Authorization Successful</h1>
        <p>Exchanging authorization code for tokens...</p>
        <script>
            // Exchange code for tokens immediately
            fetch('/api/ebay-exchange-token', {{
                method: 'POST',
                headers: {{ 'Content-Type': 'application/json' }},
                body: JSON.stringify({{ code: '{code}', state: '{state}' }})
            }})
            .then(response => response.json())
            .then(data => {{
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'ebay_oauth_success',
                        data: data
                    }}, '*');
                    window.close();
                }} else {{
                    document.body.innerHTML = '<h1>Success!</h1><p>Authentication completed. You can close this window.</p>';
                }}
            }})
            .catch(error => {{
                if (window.opener) {{
                    window.opener.postMessage({{
                        type: 'ebay_oauth_error',
                        error: error.message
                    }}, '*');
                    window.close();
                }} else {{
                    document.body.innerHTML = '<h1>Error</h1><p>Token exchange failed. Please try again.</p>';
                }}
            }});
        </script>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")


@router.get("/ebay-oauth-decline")
async def ebay_oauth_decline(
    error: Optional[str] = Query(None), state: Optional[str] = Query(None)
):
    """Handle eBay OAuth decline callback."""
    error_message = error or "User declined authorization"
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>eBay OAuth Declined</title>
        <style>
            body {{ font-family: Arial, sans-serif; text-align: center; margin: 50px; }}
            h1 {{ color: #d32f2f; }}
            p {{ color: #666; }}
        </style>
    </head>
    <body>
        <h1>Authorization Declined</h1>
        <p>You declined to authorize the application or an error occurred.</p>
        <p>Error: {error_message}</p>
        <script>
            if (window.opener) {{
                window.opener.postMessage({{
                    type: 'ebay_oauth_error',
                    error: '{error_message}'
                }}, '*');
                window.close();
            }} else {{
                document.body.innerHTML += '<p>You can close this window now.</p>';
            }}
        </script>
    </body>
    </html>
    """
    return Response(content=html_content, media_type="text/html")


@router.post("/api/ebay-exchange-token")
async def ebay_exchange_token(request_data: dict):
    """Exchange authorization code for eBay tokens."""
    try:
        code = request_data.get("code")
        if not code:
            return JSONResponse(
                status_code=400,
                content={"error": "Authorization code is required"},
            )

        # Use the same RuName as in the authorization request
        redirect_uri = "jesse_peterson-jessepet-UserSc-dhzfjwzn"

        # Exchange code for tokens (also perists them)
        exchange_code_for_tokens(code, redirect_uri)

        return JSONResponse(
            content={
                "success": True,
                "message": "Tokens obtained and saved successfully",
            }
        )

    except Exception as e:
        logger.error(f"Token exchange failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})


@router.get("/ebay-oauth-demo")
async def ebay_oauth_demo():
    return FileResponse("web/static/ebay-oauth-demo.html")


@router.get("/ebay-oauth-test")
async def ebay_oauth_test():
    return FileResponse("web/static/ebay-oauth-test.html")


@router.get("/api/ebay-token-status")
async def ebay_token_status():
    """Check eBay token expiration status."""
    try:
        from web.app.ebay_auth import (
            _load_user_token_data,
            _is_user_token_expired,
        )

        token_data = _load_user_token_data()
        auth_token = token_data.get("AUTH_TOKEN", "")
        expires_at = token_data.get("EXPIRES_AT")

        if not auth_token:
            return JSONResponse(
                content={"status": "no_token", "message": "No AUTH_TOKEN found"}
            )

        is_expired = _is_user_token_expired(auth_token)
        current_time = int(time.time())

        status_info = {
            "status": "expired" if is_expired else "valid",
            "expires_at": expires_at,
            "current_time": current_time,
            "is_expired": is_expired,
            "has_refresh_token": bool(token_data.get("REFRESH_TOKEN")),
        }

        if expires_at:
            status_info["seconds_until_expiry"] = expires_at - current_time

        return JSONResponse(content=status_info)

    except Exception as e:
        logger.error(f"Token status check failed: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})
