import mediapipe as mp
import cv2
import numpy as np
from mediapipe.tasks import python
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from modules.utils import compute_angle, is_left_side
import typing
from time import sleep

from numpy import ndarray

PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult


class GymBuddy:

    def __init__(
        self,
        source,
        workout_name: str = "Push-ups",
        input_type: str = "Video",
        model_path: str = "models/pose_landmarker_lite.task",
    ):
        # set up the model
        self.input_type = input_type
        self.model_path = model_path
        self.model = self.create_model()

        # set up the camera
        self.cap = cv2.VideoCapture(source)
        assert self.cap.isOpened(), "Error: Could not open the camera."
        self.frame_timestamp = 0
        self.frame_count = 0

        # set up the workout and static parameters
        self.workout_name = workout_name.lower()
        self.workout_type = self.set_workout_type(self.workout_name)
        self.goal_reps = 0

        # set up the workout counter
        self.left_side = False
        self.down = False
        self.POSE_LANDMARK_RESULT = None
        self.count_rep = 0

    def set_workout(self, workout_name: str):
        self.workout_name = workout_name
        print(f"Workout set to: {self.workout_name}")

    def set_reps(self, reps: int):
        self.goal_reps = reps
        print(f"Reps set to: {self.goal_reps}")

    def create_model(self):
        BaseOptions = mp.tasks.BaseOptions
        PoseLandmarker = mp.tasks.vision.PoseLandmarker
        PoseLandmarkerOptions = mp.tasks.vision.PoseLandmarkerOptions
        VisionRunningMode = mp.tasks.vision.RunningMode
        callback = None
        if self.input_type.lower() == "live":
            run_mode = VisionRunningMode.LIVE_STREAM
            callback = self.print_result
        else:
            run_mode = VisionRunningMode.VIDEO
        # Create a pose landmarker instance with the video mode:
        options = PoseLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=self.model_path),
            running_mode=run_mode,
            result_callback=callback,
        )
        PoseLandmarker = PoseLandmarker.create_from_options(options)
        return PoseLandmarker

    def set_workout_type(self, workout_name: str) -> int:
        wourkouts = {"push-ups": 0, "abs": 1, "squats": 2}
        return wourkouts[workout_name]

    def print_result(self, result, output_image: mp.Image, timestamp_ms: int) -> None:
        self.POSE_LANDMARK_RESULT = result

    def draw_landmarks_on_image(self, rgb_image: np.ndarray) -> np.ndarray:
        pose_landmarks_list = self.POSE_LANDMARK_RESULT.pose_landmarks
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

    def count_workout(self) -> int:
        angle: ndarray = np.zeros((0, 1))
        keys = {}
        res = self.POSE_LANDMARK_RESULT.pose_landmarks
        count = 0
        # TODO: Add more restrictions to the specifics of the workout. i.e. hips cannot touch floor in push-ups
        if self.left_side:
            if self.workout_type == 0:  # push-ups from the left
                keys["point1"], keys["point2"], keys["point3"] = 11, 13, 15
            elif self.workout_type == 1:  # abs from the left
                keys["point1"], keys["point2"], keys["point3"] = 25, 23, 11
            else:  # squats from the left
                keys["point1"], keys["point2"], keys["point3"] = 27, 25, 23
        else:
            if self.workout_type == 0:  # push-ups from the right
                keys["point1"], keys["point2"], keys["point3"] = 12, 14, 16
            elif self.workout_type == 1:  # abs from the right
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
                if self.down:
                    pass
                else:
                    self.down = True
            elif angle >= 120:
                if not self.down:
                    pass
                else:
                    self.down = False
                    count = 1
        return count

    def detect(self) -> np.ndarray:
        w, h, fps = (
            int(self.cap.get(x))
            for x in (
                cv2.CAP_PROP_FRAME_WIDTH,
                cv2.CAP_PROP_FRAME_HEIGHT,
                cv2.CAP_PROP_FPS,
            )
        )
        while self.cap.isOpened():
            success, im0 = self.cap.read()
            if not success:
                print(
                    "Video frame is empty or video processing has been successfully completed."
                )
                cv2.destroyAllWindows()
                break
            im0 = cv2.resize(im0, (720, 720))
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=im0)
            # frame_timestamp_ms = int(src.get(cv2.CAP_PROP_POS_MSEC))+1
            self.frame_timestamp += int(
                1000 / fps
            )  # Increment timestamp by frame duration
            # print(" ms: ", self.frame_timestamp)
            type_run = self.model._running_mode.name
            # print("type_run: ", type_run)
            frame = im0
            if type_run == "LIVE_STREAM":
                self.model.detect_async(mp_image, self.frame_timestamp)
            else:
                self.POSE_LANDMARK_RESULT = self.model.detect_for_video(
                    mp_image, self.frame_timestamp
                )
            if type(self.POSE_LANDMARK_RESULT) is not type(None):
                annotated_img = self.draw_landmarks_on_image(im0)
                if len(self.POSE_LANDMARK_RESULT.pose_landmarks) > 0:
                    if self.frame_count == 0:
                        self.left_side = is_left_side(
                            self.POSE_LANDMARK_RESULT.pose_landmarks
                        )
                        # print(f'side: { self.left_side}')
                        # wo_name, wo_type = detect_workout(POSE_LANDMARK_RESULT.pose_landmarks, left=wo_side)
                        # print(f'name: {self.workout_name}, type: {self.workout_type}')
                    self.count_rep += self.count_workout()
                    text_with_var = f"{self.count_rep} {self.workout_name} so far!"
                    # print(text_with_var)
                    # cv2.putText(annotated_img, text_with_var, (100, 180), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 0, 0), 10)
                    self.frame_count += 1
                    # cv2.imshow('frame', annotated_img)
                    # print("annotated_img: ",annotated_img)
                    frame = annotated_img

                if cv2.waitKey(1) & 0xFF == ord("q"):
                    self.cap.release()
                    break
            return frame
