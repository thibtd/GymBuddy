"""Main logic of the app."""

import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import duckdb
from modules.gymBuddy import GymBuddy
import os
from typing import Any
from modules.db_setup import connect_in_memory_db, close_db_connection, save_data_to_db
from modules.feedbackAgent import FeedbackAgent


# Get the absolute path to the current file's directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


app = FastAPI(
    title="GymBuddy API",
    description="AI-Powered Personal Trainer Backend",
    version="1.0.0",
)


# Add CORS middleware for cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Mount static files
app.mount(
    "/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static"
)

# Set up Jinja2 templates
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))


@app.get("/", response_class=HTMLResponse)
async def get(request: Request):
    """get the html request"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.websocket("/ws")
async def camera_feed(websocket: WebSocket):
    """main logic for the app's loop"""
    await websocket.accept()

    print("WebSocket connected successfully")
    start_detection: bool = False
    wo_names: list = []
    wo_reps: list = []
    series_number:int=1
    last_history_sent: str = ""

    # Initialize in-memory DuckDB database
    db_conn: duckdb.DuckDBPyConnection = connect_in_memory_db()
    # Initialize GymBuddy
    buddy: GymBuddy = GymBuddy()
    feedback_agent: FeedbackAgent = FeedbackAgent(db_conn=db_conn)

    # start the loop
    try:
        while True:
            try:
                # Wait for message
                message = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                if "text" in message:
                    data: dict = json.loads(message["text"])
                    print(f"Received text message: {data}")
                    print(f"Data type: {data.get('type')}, Value: {data.get('value')}")
                    if data.get("type") == "workout":
                        workout_name = data.get("value", "push-ups")
                        buddy.set_workout(workout_name)
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "data",
                                    "message": f"Selected {workout_name}. Ready to start!",
                                    "status": "ready",
                                }
                            )
                        )

                    if data.get("type") == "reps":

                        reps = int(data.get("value", 1))
                        print(f"Setting target reps to {reps}")
                        buddy.set_reps(reps)
                        await websocket.send_text(
                            json.dumps(
                                {
                                    "type": "data",
                                    "message": f"Set target: {reps} reps. Ready to start!",
                                    "status": "ready",
                                }
                            )
                        )
                    if data.get("type") == "strictness":
                        strictness = data.get("value", "strict")
                        buddy.set_strictness(strictness)
                    if data.get("type") == "start":
                        buddy.set_series_number(series_number)
                        start_detection = True
                        buddy.count_rep = 0
                        print("Starting detection!")

                elif "bytes" in message:
                    # Process video frame
                    frame_data = message["bytes"]
                    frame = buddy.process_frame_from_bytes(frame_data)

                    if frame is not None and start_detection:
                        # Process the frame for exercise detection
                        analysis_data = await asyncio.to_thread(
                            buddy.detect_from_frame, frame
                        )
                        # Check if workout completed
                        if buddy.count_rep >= buddy.goal_reps and buddy.goal_reps > 0:
                            start_detection = False
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "data",
                                        "message": f"Workout complete! You did {buddy.count_rep} {buddy.workout_name}!",
                                        "status": "completed",
                                    }
                                )
                            )
                            print("Workout complete! Writing data to database...")
                            data_to_save: dict[str, Any] = buddy.get_data_to_save()
                            buddy.reset_data_buffers()  # Reset buffers after saving

                            # Save data to DuckDB
                            saved = save_data_to_db(
                                db_conn,
                                metadata=data_to_save["workout_db_buffer"],
                                analysis_data=data_to_save["wo_analysis_buffer"],
                                raw_landmarks=data_to_save["raw_landmarks_buffer"],
                            )
                            if saved:
                                print("Getting feedback...")
                                try:
                                    # feedback_message = '1234'
                                    feedback = await asyncio.wait_for(
                                        asyncio.to_thread(
                                            feedback_agent.agent_pipeline
                                        ),
                                        timeout=180,
                                    )

                                    feedback_message = feedback["formatted_feedback"]
                                except Exception as e:
                                    print(f"Error getting feedback: {e}")
                                    feedback_message = "Error getting feedback. Please try again later."

                                print(f"Feedback received: {feedback_message}")
                                await websocket.send_text(
                                    json.dumps(
                                        {
                                            "type": "feedback",
                                            "message": feedback_message,
                                        }
                                    )
                                )
                                wo_names.append(buddy.workout_name)
                                wo_reps.append(buddy.count_rep)
                                series_number+=1
                            else:
                                print("Failed to save data to database.")
                                await websocket.send_text(
                                    json.dumps(
                                        {
                                            "type": "error",
                                            "message": "Failed to save workout data. Please try again.",
                                        }
                                    )
                                )
                        else:
                            # Send current rep count and analysis data
                            await websocket.send_text(
                                json.dumps(
                                    {
                                        "type": "data",
                                        "message": f"Current rep count: {buddy.count_rep}",
                                        "status": "In Progress",
                                    }
                                )
                            )
                        # Send analysis data for rendering
                        await websocket.send_text(json.dumps(analysis_data))
            except asyncio.TimeoutError:
                # Send history when idle
                history_message = ""
                for i in range(len(wo_names)):
                    history_message += f"{wo_names[i]}: {wo_reps[i]} reps\n"

                if history_message != last_history_sent:
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "history",
                                "message": history_message.replace("\n", "<br>"),
                            }
                        )
                    )
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
        close_db_connection(conn=db_conn)
        print("WebSocket connection closed")
