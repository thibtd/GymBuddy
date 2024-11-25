import uvicorn
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from archives.live_mediapipe import run_live_cam
import cv2

app = FastAPI()


# vid = camera_setup


@app.get("/")
async def welcome():
    return "Hello There, Welcome"


@app.get("/video")
async def video_feed():  # vid = Depends(vid)
    cap = cv2.VideoCapture(0)
    assert cap.isOpened(), "Error camera"
    return StreamingResponse(
        run_live_cam(cap), media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/data")
async def getdata():
    # cam.kill_cam()
    # return cam.process_data()
    pass


if __name__ == "__main__":
    uvicorn.run("main:app", reload=True)
