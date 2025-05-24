# import ssl
import os
import uvicorn
from dotenv import load_dotenv

load_dotenv()

# ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
# ssl_context.load_cert_chain('cert.pem', keyfile='key.pem')

if __name__ == "__main__":
    uvicorn.run("web.app.main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8050)), ssl_keyfile='key.pem', ssl_certfile='cert.pem')
