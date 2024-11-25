import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from fastapi.responses import HTMLResponse
import cv2
from modules.gymBuddy import GymBuddy
import numpy as np 

app = FastAPI()


html = '''
<!DOCTYPE html>
<html>
<head>
    <title>Video Stream</title>
    <style>
        body {
            font-family: Arial, sans-serif;
        }
        .controls {
            margin-bottom: 20px;
        }
        label {
            margin-right: 10px;
        }
        select, input {
            margin-right: 20px;
        }
        #videoCanvas {
            border: 1px solid #ccc;
        }
    </style>
</head>
<body>
    <div class="column">
        <h1>Video Stream</h1>
        
        <div class="controls">
            <!-- Workout Selection Dropdown -->
            <label for="workout-select">Workout:</label>
            <select id="workout-select">
                <option value="push-ups">Push-ups</option>
                <option value="abs">Abs</option>
                <option value="squats">Squats</option>
            </select>
            
            <!-- Reps Number Selector and Go Button -->
            <label for="reps-select">Reps:</label>
            <input type="number" id="reps-select" min="1" value="10">
            <button id="go-button">Go</button>
        </div>
        <div id="status"></div>

        </div>
        <canvas id="videoCanvas" width="720" height="720"></canvas>
    </div>
    <div class="column">
         <div id="status"></div>
         </div>
    </div>
    
    <script>
        const workoutSelect = document.getElementById('workout-select');
        const repsSelect = document.getElementById('reps-select');
        const goButton = document.getElementById('go-button');
        const canvas = document.getElementById('videoCanvas');
        const ctx = canvas.getContext('2d');
        
        const ws = new WebSocket("ws://127.0.0.1:8000/ws");
        ws.binaryType = "arraybuffer";
        
        ws.onopen = () => {
            console.log("WebSocket connected");
            // Send initial workout selection and reps
            ws.send(JSON.stringify({ type: 'workout', value: workoutSelect.value }));
            ws.send(JSON.stringify({ type: 'reps', value: parseInt(repsSelect.value, 10) }));
        };
        
        ws.onmessage = (event) => {
            if (typeof event.data === "string") {
                // Text message received (analysis data)
                const data = JSON.parse(event.data);
                if (data.type === 'data') {
                    // Display the message on the frontend
                    const statusDiv = document.getElementById('status');
                    statusDiv.textContent = data.message;
                }
            } else {
                // Binary data received (video frame)
                const imageBlob = new Blob([event.data], { type: "image/jpeg" });
                const imageURL = URL.createObjectURL(imageBlob);

                const img = new Image();
                img.onload = () => {
                    canvas.width = img.width;
                    canvas.height = img.height;
                    ctx.drawImage(img, 0, 0);
                    URL.revokeObjectURL(imageURL); // Free memory
                };
                img.src = imageURL;
            }
        };
        
        ws.onclose = () => console.log("WebSocket disconnected");
        ws.onerror = (error) => console.error("WebSocket error:", error);
        
        // Send workout selection when changed
        workoutSelect.addEventListener('change', () => {
            const selectedWorkout = workoutSelect.value;
            ws.send(JSON.stringify({ type: 'workout', value: selectedWorkout }));
            console.log("Selected workout:", selectedWorkout);
        });
        
        // Send reps value and start detection when "Go" button is clicked
        goButton.addEventListener('click', () => {
            const selectedReps = parseInt(repsSelect.value, 10);
            if (isNaN(selectedReps) || selectedReps < 1) {
                alert("Please enter a valid number of reps.");
                return;
            }
            // Send reps value
            ws.send(JSON.stringify({ type: 'reps', value: selectedReps }));
            console.log("Selected reps:", selectedReps);

            // Send start message
            ws.send(JSON.stringify({ type: 'start' }));
            console.log("Detection started");
        });
    </script>
</body>
</html>
'''

@app.get("/")
async def get():
    return HTMLResponse(html)


@app.websocket("/ws")
async def camera_feed(websocket: WebSocket):
    await websocket.accept()
    print("WebSocket connected")
    start_detection = False
    wo_names = []
    wo_reps = []
    analysis_data = { 'type': 'data',
                        'message': 'Let\'s get strated with your workout' 
                    }
    remaining_reps = np.infty
    #src = "videos/pushups.MOV"
    src= 0
    buddy = GymBuddy(src)
    if not buddy.cap.isOpened():
        print("Error: Could not open the camera.")
        await websocket.close()
        return

    try:
       
        while True:
            print('start', start_detection)
            print(f'workout names {wo_names}, workouts reps {wo_reps}')
            print(f'remaining reps {remaining_reps}')

            # TODO: Move all the logic to dedicated functions 
            # Handle incoming messages for workout configuration
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.1)
                data = json.loads(message)
                if data.get('type') == 'workout':
                    workout_name = data.get('value', 'push-ups')
                    buddy.set_workout(workout_name)
                elif data.get('type') == 'reps':
                    reps = int(data.get('value', 10))
                    buddy.set_reps(reps)
                elif data.get('type') == 'start':
                    start_detection = True
                    print("Received start command")
            except asyncio.TimeoutError:
                # No message received, continue processing
                pass
            except json.JSONDecodeError:
                print("Received non-JSON message")
            except ValueError:
                print("Invalid value for reps")

            #retrieve and process video
            remaining_reps = buddy.goal_reps - buddy.count_rep
            if start_detection:
                frame = buddy.detect()
                analysis_data = {
                'type': 'data',
                'message': f"Completed {buddy.count_rep} out of {buddy.goal_reps} {buddy.workout_name}, {remaining_reps} to go!"
                }
                if remaining_reps==0:
                    analysis_data = {
                        'type': 'data',
                        'message': f"Reps finished! Congratulations you did {buddy.count_rep} {buddy.workout_name} "
                    }
                    wo_names.append(buddy.workout_name)
                    wo_reps.append(buddy.count_rep)
                    start_detection =False

            else:
                ret, frame = buddy.cap.read()
                frame = cv2.resize(frame, (720, 720))
                if not ret:
                    print("No frame received from GymBuddy")
                    break
            if frame is None:
                print("No frame received from GymBuddy")
                break
            
            
            
            

            await websocket.send_text(json.dumps(analysis_data))
            try:
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
        await websocket.close()
