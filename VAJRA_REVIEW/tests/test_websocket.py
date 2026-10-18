import json
import pytest
from backend.app.services.simulator import sim_manager

def test_websocket_live_stream_and_heartbeat(client):
    # Ensure simulator speed is fast for tests
    sim_manager.set_speed(10.0)

    with client.websocket_connect("/ws/live") as websocket:
        # 1. Handshake message
        init_data = websocket.receive_json()
        assert init_data["type"] == "connection_established"

        # 2. Ping / Pong Heartbeat
        websocket.send_json({"type": "ping"})
        pong_data = websocket.receive_json()
        assert pong_data["type"] == "pong"

        # 3. Read at least one broadcast telemetry reading frame
        # If simulator loop is running, we get a reading frame
        reading_found = False
        for _ in range(5):
            msg = websocket.receive_json()
            if msg.get("type") == "reading":
                assert "data" in msg
                assert "health_snapshot" in msg
                reading_found = True
                break

        assert reading_found is True

def test_websocket_fault_injection_flow(client):
    sim_manager.set_speed(10.0)

    with client.websocket_connect("/ws/live") as websocket:
        # Consume greeting
        websocket.receive_json()

        # Send inject_fault command over WebSocket
        websocket.send_json({
            "type": "inject_fault",
            "engine_id": "ENG-001",
            "fault_type": "vibration_spike",
            "severity": "critical"
        })

        ack = websocket.receive_json()
        assert ack["type"] == "fault_injected_ack"
        assert ack["engine_id"] == "ENG-001"

    sim_manager.stop()
    from backend.scripts.load_data import load_all_data
    load_all_data()
