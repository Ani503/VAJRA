import json
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.services.simulator import sim_manager

logger = logging.getLogger("websocket")
router = APIRouter(tags=["Live Telemetry WebSocket"])

@router.websocket("/ws/live")
async def websocket_live_endpoint(websocket: WebSocket):
    await sim_manager.connect(websocket)

    # Automatically ensure simulation loop is active
    if not sim_manager.is_running:
        sim_manager.start()

    try:
        # Initial greeting / connection handshake
        await websocket.send_text(json.dumps({
            "type": "connection_established",
            "message": "Connected to VAJRA Real-Time Telemetry Stream",
            "speed": sim_manager.speed,
            "is_running": sim_manager.is_running,
        }))

        while True:
            # Listen for client heartbeat/control messages
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                msg_type = msg.get("type")
                if msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong"}))
                elif msg_type == "inject_fault":
                    sim_manager.inject_fault(
                        engine_id=msg.get("engine_id", "ENG-001"),
                        fault_type=msg.get("fault_type", "vibration_spike"),
                        severity=msg.get("severity", "critical"),
                    )
                    await websocket.send_text(json.dumps({
                        "type": "fault_injected_ack",
                        "engine_id": msg.get("engine_id"),
                        "fault_type": msg.get("fault_type"),
                    }))
            except json.JSONDecodeError:
                pass

    except WebSocketDisconnect:
        sim_manager.disconnect(websocket)
        logger.info("Client cleanly disconnected from /ws/live")
    except Exception as e:
        sim_manager.disconnect(websocket)
        logger.error(f"WebSocket error: {e}")
