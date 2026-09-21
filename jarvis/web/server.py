import asyncio
import json
import threading
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from jarvis.config import config, SCREENSHOTS_DIR, BASE_DIR
from jarvis.actions.telemetry import telemetry
from jarvis.actions.notes_manager import notes_manager
from jarvis.actions.system_control import system_controller
from jarvis.brain.intent_router import intent_router
from jarvis.voice.speaker import speaker
from jarvis.voice.listener import listener

app = FastAPI(title="J.A.R.V.I.S. Core Interface", version="1.0.0")

FRONTEND_DIR = BASE_DIR / "frontend"

# Active WebSocket connections
active_connections: list[WebSocket] = []
connections_lock = threading.Lock()
loop: asyncio.AbstractEventLoop | None = None

async def broadcast_json(data: dict):
    """Send JSON payload to all connected frontend clients."""
    with connections_lock:
        clients = list(active_connections)
    
    dead_clients = []
    for ws in clients:
        try:
            await ws.send_text(json.dumps(data))
        except Exception:
            dead_clients.append(ws)
            
    with connections_lock:
        for ws in dead_clients:
            if ws in active_connections:
                active_connections.remove(ws)

def sync_broadcast(data: dict):
    """Thread-safe bridge to broadcast from synchronous threads."""
    global loop
    if loop and loop.is_running():
        asyncio.run_coroutine_threadsafe(broadcast_json(data), loop)

# Connect speaker callbacks to broadcast audio RMS & speech events
speaker.register_callback(
    on_start=lambda txt: sync_broadcast({"type": "speech_start", "text": txt}),
    on_stop=lambda: sync_broadcast({"type": "speech_stop"}),
    on_chunk=lambda rms: sync_broadcast({"type": "audio_amplitude", "rms": rms})
)

# Connect listener state changes to HUD
listener.register_callback(
    on_state_change=lambda st: sync_broadcast({"type": "status_change", "status": st}),
    on_wake=lambda phrase: sync_broadcast({"type": "wake_detected", "phrase": phrase}),
    on_sound_level=lambda rms: sync_broadcast({"type": "mic_level", "rms": rms})
)

class ChatRequest(BaseModel):
    query: str

@app.get("/api/status")
async def get_status():
    return {
        "name": config.ASSISTANT_NAME,
        "voice": config.VOICE,
        "state": listener.state,
        "is_speaking": speaker.is_speaking
    }

@app.get("/api/telemetry")
async def get_telemetry():
    return telemetry.get_stats()

@app.get("/api/notes")
async def get_notes():
    return notes_manager.list_notes()

@app.post("/api/chat")
async def post_chat(req: ChatRequest):
    result = intent_router.process(req.query)
    # Speak in background thread
    speaker.speak(result["response"], block=False)
    return result

# Screenshots static serving
app.mount("/screenshots", StaticFiles(directory=str(SCREENSHOTS_DIR)), name="screenshots")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    global loop
    loop = asyncio.get_running_loop()
    await websocket.accept()
    with connections_lock:
        active_connections.append(websocket)
        
    # Send initial greeting & state
    await websocket.send_text(json.dumps({
        "type": "init",
        "name": config.ASSISTANT_NAME,
        "status": listener.state,
        "telemetry": telemetry.get_stats(),
        "notes": notes_manager.list_notes()
    }))

    try:
        while True:
            raw_msg = await websocket.receive_text()
            data = json.loads(raw_msg)
            msg_type = data.get("type")

            if msg_type == "user_input":
                query_text = data.get("text", "").strip()
                if query_text:
                    await broadcast_json({"type": "user_message", "text": query_text})
                    # Process intent
                    result = intent_router.process(query_text)
                    await broadcast_json({
                        "type": "assistant_response",
                        "query": query_text,
                        "response": result["response"],
                        "action": result["action"],
                        "data": result.get("data")
                    })
                    # Speak response
                    speaker.speak(result["response"], block=False)

            elif msg_type == "trigger_mic":
                # Manual trigger of active listening
                def _trigger():
                    listener._set_state("LISTENING")
                    cmd = listener.listen_and_transcribe_command()
                    if cmd:
                        sync_broadcast({"type": "user_message", "text": cmd})
                        res = intent_router.process(cmd)
                        sync_broadcast({
                            "type": "assistant_response",
                            "query": cmd,
                            "response": res["response"],
                            "action": res["action"],
                            "data": res.get("data")
                        })
                        speaker.speak(res["response"], block=False)
                    else:
                        listener._set_state("STANDBY")
                threading.Thread(target=_trigger, daemon=True).start()

            elif msg_type == "quick_action":
                action = data.get("action")
                if action == "telemetry":
                    stats = telemetry.get_stats()
                    voice = telemetry.get_voice_summary()
                    await broadcast_json({
                        "type": "assistant_response",
                        "query": "System Diagnostics",
                        "response": voice,
                        "action": "telemetry",
                        "data": stats
                    })
                    speaker.speak(voice, block=False)
                elif action == "screenshot":
                    filepath, voice = system_controller.take_screenshot()
                    await broadcast_json({
                        "type": "assistant_response",
                        "query": "Take Screenshot",
                        "response": voice,
                        "action": "screenshot",
                        "data": {"filepath": filepath, "filename": Path(filepath).name}
                    })
                    speaker.speak(voice, block=False)
                elif action == "mute":
                    voice = system_controller.control_volume("mute")
                    await broadcast_json({
                        "type": "assistant_response",
                        "query": "Toggle Mute",
                        "response": voice,
                        "action": "volume"
                    })
                    speaker.speak(voice, block=False)
                elif action == "lock":
                    voice = system_controller.lock_workstation()
                    await broadcast_json({
                        "type": "assistant_response",
                        "query": "Lock Workstation",
                        "response": voice,
                        "action": "lock"
                    })
                elif action == "notes":
                    notes = notes_manager.list_notes()
                    voice = notes_manager.get_voice_summary()
                    await broadcast_json({
                        "type": "assistant_response",
                        "query": "Notes Summary",
                        "response": voice,
                        "action": "note_list",
                        "data": notes
                    })
                    speaker.speak(voice, block=False)

    except WebSocketDisconnect:
        with connections_lock:
            if websocket in active_connections:
                active_connections.remove(websocket)
    except Exception as e:
        with connections_lock:
            if websocket in active_connections:
                active_connections.remove(websocket)

async def telemetry_publisher():
    """Publish telemetry every 2 seconds to all active sockets."""
    while True:
        try:
            if active_connections:
                stats = telemetry.get_stats()
                await broadcast_json({"type": "telemetry_update", "telemetry": stats})
        except Exception:
            pass
        await asyncio.sleep(2.0)

@app.on_event("startup")
async def startup_event():
    global loop
    loop = asyncio.get_running_loop()
    asyncio.create_task(telemetry_publisher())

# Serve static frontend files
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=str(FRONTEND_DIR), html=True), name="frontend")
