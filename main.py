import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import cv2
from modules.gymBuddy import GymBuddy
import numpy as np
import os
import time
from apis.mobile_api import mobile_router

# Get the absolute path to the current file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title="GymBuddy API",
    description="AI-Powered Personal Trainer Backend",
    version="1.0.0"
)

# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include mobile API router
app.include_router(mobile_router)

# Mount static files
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/")
async def get(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def camera_feed(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected successfully")
    
    start_detection = False
    wo_names = []
    wo_reps = []
    last_history_sent = ""
    remaining_reps = np.infty
    
    # Initialize GymBuddy
    buddy = GymBuddy(None)
    
    try:
        while True:
            try:

                # Wait for message
                message = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                if 'text' in message:
                    
                    data = json.loads(message['text'])
    
                    print(f"Received text message: {data}")
                    print(f"Data type: {data.get('type')}, Value: {data.get('value')}")
                    if data.get("type") == "workout":
                        workout_name = data.get("value", "push-ups")
                        buddy.set_workout(workout_name)
                        await websocket.send_text(json.dumps({
                            "type": "data",
                            "message": f"Selected {workout_name}. Ready to start!",
                            "status": "ready"
                        }))
                        
                    if data.get("type") == "reps":
                        reps = int(data.get("value", 1))
                        print(f"Setting target reps to {reps}")
                        buddy.set_reps(reps)
                        await websocket.send_text(json.dumps({
                            "type": "data",
                            "message": f"Set target: {reps} reps. Ready to start!",
                            "status": "ready"
                        }))
                        
                    if data.get("type") == "strictness":
                        strictness = data.get("value", "strict")
                        buddy.set_strictness(strictness)
                        
                    if data.get("type") == "start":
                        start_detection = True
                        buddy.count_rep = 0
                        buddy.workout_completed = False  # Reset workout completion statu
                        print("Starting detection!")
                        
                
                elif 'bytes' in message:
                    
                    # Process video frame
                    frame_data = message['bytes']
                    frame = buddy.process_frame_from_bytes(frame_data)
                    
                    if frame is not None and start_detection:
                            # Process the frame for exercise detection
                            analysis_data = await asyncio.to_thread(buddy.detect_from_frame,frame)
                            
                           
                            # Check if workout completed 
                            if buddy.count_rep >= buddy.goal_reps and buddy.goal_reps>0:
                                buddy.workout_completed = True  # Flag to prevent multiple completions
                                await websocket.send_text(json.dumps({
                                    "type": "data",
                                    "message": f"Workout complete! You did {buddy.count_rep} {buddy.workout_name}!",
                                    "status": "completed"
                                }))
                                
                                print("Getting feedback from Ollama...")
                                feedback_message = '1234'
                                #feedback_message = await asyncio.to_thread(buddy.give_feedback)

                                print(f"Feedback received: {feedback_message}")
                                await websocket.send_text(json.dumps({
                                    "type": "feedback",
                                    "message": feedback_message,
                                }))
                                wo_names.append(buddy.workout_name)
                                wo_reps.append(buddy.count_rep)
                                start_detection = False
                            else:
                                # Send current rep count and analysis data
                                await websocket.send_text(json.dumps({
                                    "type": "data",
                                    "message": f"Current rep count: {buddy.count_rep}",
                                    "status": "In Progress",
                                }))
                            # Send analysis data for rendering
                            await websocket.send_text(json.dumps(analysis_data))   
                            
                            
            except asyncio.TimeoutError:
                # Send history when idle
                history_message = ""
                for i in range(len(wo_names)):
                    history_message += f"{wo_names[i]}: {wo_reps[i]} reps\n"

                if history_message != last_history_sent:
                    await websocket.send_text(json.dumps({
                        "type": "history",
                        "message": history_message.replace("\n", "<br>")
                    }))
                    last_history_sent = history_message
                        
            except json.JSONDecodeError as e:
                print(f"JSON decode error: {e}")
            except ValueError as e:
                print(f"Value error: {e}")
            
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        print("WebSocket connection closed")
