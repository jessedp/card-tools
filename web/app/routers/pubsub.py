from fastapi import APIRouter, WebSocket
from pydantic import BaseModel
from typing import Dict, Any
import uuid

from web.app.logger import setup_logger

router = APIRouter(
    prefix="/ps"
)

logger = setup_logger()

# Store active connections
active_connections: Dict[str, WebSocket] = {}

class DataPayload(BaseModel):
    client_id: str
    data: Any

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()

    # Generate a unique client ID
    client_id = str(uuid.uuid4())
    active_connections[client_id] = websocket

    try:
        # Send the client ID back to the client
        await websocket.send_json({"client_id": client_id})

        # Keep the connection open for receiving messages
        while True:
            await websocket.receive_text()  # Just keep the connection alive

    except Exception as e:
        print(f"WebSocket connection closed: {e}")
    finally:
        # Clean up when connection is closed
        if client_id in active_connections:
            del active_connections[client_id]

@router.post("/publish")
async def publish_data(payload: DataPayload):
    client_id = payload.client_id

    # if client_id not in active_connections:
    #     return {"status": "error", "message": "Client not found"}

    # Send data to the specific client
    logger.info("Publish......")
    try:
        for i in active_connections:
            logger.info(f"Sent to: {i}")
            await active_connections[i].send_json({"data": payload.data})
            # await conn.send_json({"data": payload.data})

    except Exception as e:
        if client_id in active_connections:
            del active_connections[client_id]
        return {"status": "error", "message": str(e)}

    return {"status": "success", "message": "Data sent successfully"}
# Optional endpoint to get all active client IDs
@router.get("/clients")
async def get_clients():
    return {"active_clients": list(active_connections.keys())}
