import mediapipe as mp
import cv2
import numpy as np
from archives.mediapipeGym import draw_landmarks_on_image

PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult

RESULT = None


# Define the result callback function
def print_result(result: PoseLandmarkerResult, output_image: mp.Image, timestamp_ms: int):  # type: ignore
    global RESULT
    RESULT = result
    pass


def run_live_cam(src):
    global RESULT
    print("Running Live Cam")
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions

    VisionRunningMode = mp.tasks.vision.RunningMode
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path="models/pose_landmarker_lite.task"),
        running_mode=VisionRunningMode.LIVE_STREAM,
        result_callback=print_result,
    )

    PoseLandmarker = PoseLandmarker.create_from_options(options)

    w, h, fps = (
        int(src.get(x))
        for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS)
    )
    frame_timestamp_ms = 0
    while src.isOpened():
        success, im0 = src.read()
        if not success:
            print(
                "Video frame is empty or video processing has been successfully completed."
            )
            cv2.destroyAllWindows()
            break
        # print("im0: ", im0)
        im0 = cv2.resize(im0, (720, 720))
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=im0)
        frame_timestamp_ms += int(1000 / fps)  # Increment timestamp by frame duration
        print(" ms: ", frame_timestamp_ms)
        PoseLandmarker.detect_async(mp_image, frame_timestamp_ms)
        img = im0
        if type(RESULT) is not type(None):
            print(RESULT)
            annotated_img = draw_landmarks_on_image(im0, RESULT)
            img = annotated_img
            frame = cv2.imencode(".jpg", annotated_img)[1].tobytes()
            print(type(frame))
            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        # cv2.imshow('frame',img)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            src.release()
            break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    cap = cv2.VideoCapture(0)
    assert cap.isOpened(), "Error reading video file"
    print("run")
    run_live_cam(cap)
    print("ran")
