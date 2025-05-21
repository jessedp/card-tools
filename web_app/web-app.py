import logging
import sys
from aiohttp import web
import aiohttp_cors
from web.routes import setup_routes
from config.settings import PORT, HOST, LOG_FILE

# Configure logging to file and console
def setup_logging():
    logger = logging.getLogger('web_server')
    logger.setLevel(logging.INFO)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # File handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger

# Create and configure the application
async def create_app():
    app = web.Application()
    
    # Setup CORS
    cors = aiohttp_cors.setup(app, defaults={
        "*": aiohttp_cors.ResourceOptions(
            allow_credentials=True,
            expose_headers="*",
            allow_headers="*",
        )
    })
    
    # Setup routes
    setup_routes(app, cors)
    
    return app

def main():
    logger = setup_logging()
    logger.info(f"Starting server on {HOST}:{PORT}")
    
    app = create_app()
    web.run_app(app, host=HOST, port=PORT)

if __name__ == "__main__":
    main()
