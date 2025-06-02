import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import cv2
from modules.gymBuddy import GymBuddy
import numpy as np
import os
from apis.mobile_api import mobile_router

# Get the absolute path to the current file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

app = FastAPI(
    title="GymBuddy API",
    description="AI-Powered Personal Trainer Backend",
    version="1.0.0"
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
    print("WebSocket connection attempt received")
    await websocket.accept()
    print("WebSocket connected successfully")
    print(f"Client address: {websocket.client}")
    print(f"WebSocket headers: {websocket.headers}")
    start_detection:bool = False
    wo_names:list = []
    wo_reps:list = []
    analysis_data:dict = {"type": "data", "message": "Let's get started with your workout"}
    remaining_reps:int = 0
    reps_finished:bool = False
    feedback_data:dict = {"type": 'feedback', "message": ""} # Empty string to trigger placeholder
    #src:str = "videos/puFullBody.MOV"
    #src = "videos/papa_squat.mp4"
    #src = 'videos/pu_long_multi_cam_knees.MOV'
    #src = 'videos/matis_pu_cul.mp4'
    #src = 'videos/matis_pu.mov'
    #src = 'videos/squats_karo_landscape.MOV'
    src = 0 
    
    buddy = GymBuddy(src)
    if not buddy.cap.isOpened():
        print("Error: Could not open the camera.")
        await websocket.close()
        return

    try:

        while True:
            print("start", start_detection)
            print(f"workout names {wo_names}, workouts reps {wo_reps}")
            print(f"remaining reps {remaining_reps}")

            # TODO: Move all the logic to dedicated functions
            # Handle incoming messages for workout configuration
            history_message = ""
            for i in range(len(wo_names)):
                history_message += f"{wo_names[i]}: {wo_reps[i]} reps\n"

            history_data = {
                "type": "history",
                "message": history_message.replace("\n", "<br>"),
            }
            await websocket.send_text(json.dumps(history_data))

            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                data = json.loads(message)
                if data.get("type") == "workout":
                    workout_name = data.get("value", "push-ups")
                    print(f"Received workout command, {workout_name}")
                    start_detection = False
                    buddy.set_workout(workout_name)
                elif data.get("type") == "reps":
                    reps = int(data.get("value", 10))
                    buddy.set_reps(reps)
                    start_detection = False
                elif data.get("type") == "strictness":
                    print(f"Received strictness command, {data.get('value', 'strict')}")
                    strictness = data.get("value", "strict")
                    buddy.set_strictness(strictness)
                    start_detection = False
                elif data.get("type") == "start":
                    start_detection = True
                    
                    print("Received start command")
            except asyncio.TimeoutError:
                # No message received, continue processing
                pass
            except json.JSONDecodeError:
                print("Received non-JSON message")
            except ValueError:
                print("Invalid value for reps")

            # retrieve and process video
            remaining_reps = buddy.goal_reps - buddy.count_rep
            
            if start_detection:
                frame = buddy.detect()
                reps_finished= False
                

                analysis_data = {
                    "type": "data",
                    "message": f"Completed {buddy.count_rep} out of {buddy.goal_reps} {buddy.workout_name}, {remaining_reps} to go!",
                    "status": "in_progress"
                }
                if remaining_reps == 0:
                    analysis_data = {
                        "type": "data",
                        "message": f"Reps finished! Congratulations you did {buddy.count_rep} {buddy.workout_name} ",
                        "status": "completed"
                    }
                    wo_names.append(buddy.workout_name)
                    wo_reps.append(buddy.count_rep)
                    buddy.count_rep = 0
                    start_detection = False
                    reps_finished = True
                    print(f"reps_finished: {reps_finished}")
            else:
                print("start false")
                if reps_finished:
                    print("reps finished")
                    #feedback = buddy.give_feedback()
                    feedback='1234 feedback'
                    # Send the feedback to the client
                    feedback_data = {
                        "type": 'feedback',
                        "message": feedback,
                    }
                    print(f"Feedback: {feedback}")
                    reps_finished = False
                    
                    
                ret, frame = buddy.cap.read()
                #frame = cv2.resize(frame, (720, 720))
                if not ret:
                    print("No frame received from GymBuddy")
                    break

            if frame is None:
                print("No frame received from GymBuddy")
                break
            
            await websocket.send_text(json.dumps(analysis_data))
            await websocket.send_text(json.dumps(feedback_data))
            
            try:
                frame = cv2.resize(frame, (1080, 720))
                _, encoded_frame = cv2.imencode(".jpg", frame)
                await websocket.send_bytes(encoded_frame.tobytes())
            except Exception as e:
                print(f"Error encoding/sending frame: {e}")
                break
            await asyncio.sleep(0.03)  # ~30 FPS
    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        buddy.cap.release()
        print("WebSocket disconnected")
        # Don't call websocket.close() here as it may already be closed
