import mediapipe as mp
import cv2
import numpy as np
from mediapipe.tasks import python
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
import typing
from time import sleep

from numpy import ndarray

PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult

DOWN = False
POSE_LANDMARK_RESULT = None


def print_result(result, output_image: mp.Image, timestamp_ms: int):
    global POSE_LANDMARK_RESULT
    POSE_LANDMARK_RESULT = result


def draw_landmarks_on_image(rgb_image, detection_result):
    pose_landmarks_list = detection_result.pose_landmarks
    annotated_image = np.copy(rgb_image)

    # Loop through the detected poses to visualize.
    for idx in range(len(pose_landmarks_list)):
        pose_landmarks = pose_landmarks_list[idx]

        # Draw the pose landmarks.
        pose_landmarks_proto = landmark_pb2.NormalizedLandmarkList()
        pose_landmarks_proto.landmark.extend(
            [
                landmark_pb2.NormalizedLandmark(
                    x=landmark.x, y=landmark.y, z=landmark.z
                )
                for landmark in pose_landmarks
            ]
        )
        solutions.drawing_utils.draw_landmarks(
            annotated_image,
            pose_landmarks_proto,
            solutions.pose.POSE_CONNECTIONS,
            solutions.drawing_styles.get_default_pose_landmarks_style(),
        )
    return annotated_image


def compute_angle(point1, point2, point3) -> ndarray:
    vec1 = np.array([point1.x, point1.y]) - np.array([point2.x, point2.y])
    vec2 = np.array([point3.x, point3.y]) - np.array([point2.x, point2.y])

    # Dot product
    dot_product = np.dot(vec1, vec2)

    # Magnitude of vectors
    mag_vec1 = np.sqrt(np.dot(vec1, vec1))
    mag_vec2 = np.sqrt(np.dot(vec2, vec2))

    # Cosine of angle
    cos_angle = dot_product / (mag_vec1 * mag_vec2)

    # Angle in radians
    angle_rad = np.arccos(cos_angle)

    # Convert to degrees if needed
    angle_deg = np.degrees(angle_rad)

    return angle_deg


def count_workout(res: list, workout_type: int, left_side: bool) -> int:
    global DOWN
    count = 0
    angle: ndarray = np.zeros((0, 1))
    keys = {}
    # TODO: Add more restrictions to the specifics of the workout. i.e. hips cannot touch floor in push-ups
    if left_side:
        if workout_type == 0:  # push-ups from the left
            keys["point1"], keys["point2"], keys["point3"] = 11, 13, 15
        elif workout_type == 1:  # abs from the left
            keys["point1"], keys["point2"], keys["point3"] = 25, 23, 11
        else:  # squats from the left
            keys["point1"], keys["point2"], keys["point3"] = 27, 25, 23
    else:
        if workout_type == 0:  # push-ups from the right
            keys["point1"], keys["point2"], keys["point3"] = 12, 14, 16
        elif workout_type == 1:  # abs from the right
            keys["point1"], keys["point2"], keys["point3"] = 26, 24, 12
        else:  # squats from the right
            keys["point1"], keys["point2"], keys["point3"] = 28, 26, 24
    for idx in range(len(res)):
        pose_landmarks = res[idx]
        point1, point2, point3 = (
            pose_landmarks[keys["point1"]],
            pose_landmarks[keys["point2"]],
            pose_landmarks[keys["point3"]],
        )
        angle = compute_angle(point1, point2, point3)
    if angle.size > 0:
        if angle <= 90:
            if DOWN:
                pass
            else:
                DOWN = True
        elif angle >= 120:
            if not DOWN:
                pass
            else:
                DOWN = False
                count = 1
    return count


def create_model(
    input_type: str = "Video", model_path: str = "models/pose_landmarker_lite.task"
):
    BaseOptions = mp.tasks.BaseOptions
    PoseLandmarker = mp.tasks.vision.PoseLandmarker
    PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode
    callback = None
    if input_type.lower() == "live":
        run_mode = VisionRunningMode.LIVE_STREAM
        callback = print_result
    else:
        run_mode = VisionRunningMode.VIDEO
    # Create a pose landmarker instance with the video mode:
    options = PoseLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=model_path),
        running_mode=run_mode,
        result_callback=callback,
    )
    PoseLandmarker = PoseLandmarker.create_from_options(options)
    return PoseLandmarker


def detect_workout(res: list, left: bool) -> tuple:
    print("res:", res)
    print("left:", left)
    keys = {}
    if left:
        keys["hands"] = 17
        keys["feet"] = 31
        keys["hips"] = 23
        keys["shoulders"] = 11
        keys["knees"] = 25
    else:
        keys["hands"] = 18
        keys["feet"] = 32
        keys["hips"] = 24
        keys["shoulders"] = 12
        keys["knees"] = 26

    for idx in range(len(res)):
        pose_landmarks = res[idx]
        print("pose_landmarks:", pose_landmarks)
        print(
            "pose_landmarks shoulders:", round(pose_landmarks[keys["shoulders"]].y, 1)
        )
        print("pose_landmarks hips:", round(pose_landmarks[keys["hips"]].y, 1))
        print("pose_landmarks hands:", round(pose_landmarks[keys["hands"]].y, 1))
        print(
            "pose_landmarks feet:",
            round(pose_landmarks[keys["feet"]].y, 1),
            round(pose_landmarks[keys["feet"]].x, 1),
        )
        print(
            "pose_landmarks knees:",
            round(pose_landmarks[keys["knees"]].y, 1),
            round(pose_landmarks[keys["knees"]].x, 1),
        )
        if (
            round(pose_landmarks[keys["shoulders"]].y, 1)
            == round(pose_landmarks[keys["hips"]].y, 1)
            and pose_landmarks[keys["shoulders"]].y < pose_landmarks[keys["hands"]].y
        ):
            return "push-ups", 0
        elif pose_landmarks[keys["knees"]].y < pose_landmarks[keys["hips"]].y and round(
            pose_landmarks[keys["shoulders"]].y, 1
        ) == round(pose_landmarks[keys["hips"]].y, 1):
            return "abs", 1
        elif (
            pose_landmarks[keys["feet"]].y > pose_landmarks[keys["knees"]].y
            and pose_landmarks[keys["feet"]].y > pose_landmarks[keys["hips"]].y
        ):
            return "squats", 2
        else:
            raise ValueError("no workout detected")


def is_left_side(res: list) -> bool:
    for idx in range(len(res)):
        pose_landmarks = res[idx]
        left_elbow = pose_landmarks[13]
        right_elbow = pose_landmarks[14]
        if left_elbow.visibility > right_elbow.visibility:
            print("left", left_elbow)
            print("right", right_elbow)
            return True
        else:
            print("left", left_elbow)
            print("right", right_elbow)
            return False


def gymDetection(src, model: PoseLandmarkerResult, workout_name: str, frame_timestamp: int):  # type: ignore
    global POSE_LANDMARK_RESULT
    wourkouts = {"push-ups": 0, "abs": 1, "squats": 2}
    workout_name = workout_name.lower()
    w, h, fps = (
        int(src.get(x))
        for x in (cv2.CAP_PROP_FRAME_WIDTH, cv2.CAP_PROP_FRAME_HEIGHT, cv2.CAP_PROP_FPS)
    )
    frame_count = 0
    count = 0
    frame_timestamp_ms = frame_timestamp
    while src.isOpened():
        success, im0 = src.read()
        if not success:
            print(
                "Video frame is empty or video processing has been successfully completed."
            )
            cv2.destroyAllWindows()
            break
        im0 = cv2.resize(im0, (720, 720))
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=im0)
        # frame_timestamp_ms = int(src.get(cv2.CAP_PROP_POS_MSEC))+1
        frame_timestamp_ms += int(1000 / fps)  # Increment timestamp by frame duration
        print(" ms: ", frame_timestamp_ms)
        type_run = model._running_mode.name
        print("type_run: ", type_run)
        frame = im0
        if type_run == "LIVE_STREAM":
            model.detect_async(mp_image, frame_timestamp_ms)
        else:
            POSE_LANDMARK_RESULT = model.detect_for_video(mp_image, frame_timestamp_ms)
        if type(POSE_LANDMARK_RESULT) is not type(None):
            annotated_img = draw_landmarks_on_image(im0, POSE_LANDMARK_RESULT)
            if len(POSE_LANDMARK_RESULT.pose_landmarks) > 0:
                if frame_count == 0:
                    wo_side = is_left_side(POSE_LANDMARK_RESULT.pose_landmarks)
                    print(f"side: {wo_side}")
                    # wo_name, wo_type = detect_workout(POSE_LANDMARK_RESULT.pose_landmarks, left=wo_side)
                    print(f"name: {workout_name}, type: {wourkouts[workout_name]}")
                count += count_workout(
                    POSE_LANDMARK_RESULT.pose_landmarks,
                    workout_type=wourkouts[workout_name],
                    left_side=wo_side,
                )
                text_with_var = f"{count} {workout_name} so far!"
                # print(text_with_var)
                cv2.putText(
                    annotated_img,
                    text_with_var,
                    (100, 180),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    3,
                    (255, 0, 0),
                    10,
                )
                frame_count += 1
                # cv2.imshow('frame', annotated_img)
                # print("annotated_img: ",annotated_img)
                frame = annotated_img
                # frame = cv2.imencode('.jpg', annotated_img[0]).tobytes()
                # print(type(frame))
                # print("frame: ",frame)
                # yield (frame)

            if cv2.waitKey(1) & 0xFF == ord("q"):
                src.release()
                break
        return frame, frame_timestamp_ms

    cv2.destroyAllWindows()


def main(vid=None, workout_input="Push-ups"):
    model_type = ""
    src = "videos/pushups.MOV"
    workout_input = workout_input.lower()
    if vid == "s":
        src = "videos/squats.MOV"
    elif vid == "a":
        src = "videos/abs.MOV"
    elif vid == "c":
        src = 0
    Landmarker = create_model(input_type=model_type)

    cap = cv2.VideoCapture(src)
    assert cap.isOpened(), "Error reading video file"
    gymDetection(cap, Landmarker, workout_input)


if __name__ == "__main__":
    main("c", "push-ups")
