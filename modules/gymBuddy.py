import mediapipe as mp
import cv2
import csv 
import os
from datetime import datetime
import numpy as np
from mediapipe import solutions
from mediapipe.framework.formats import landmark_pb2
from modules.utils import is_left_side,draw_angle_arc
from modules.workouts.pushups import PushUps

PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult


class GymBuddy:

    def __init__(
        self,
        source,
        workout_name: str = "Push-ups",
        strictness_crit: str = "loose",
        input_type: str = "Video",
        model_path: str = "models/pose_landmarker_heavy.task",

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
        self.strictness_crit = strictness_crit

        # set up the workout counter
        self.left_side = False
        self.POSE_LANDMARK_RESULT = None
        self.count_rep = 0

        # set current workout
        self.current_workout = self.create_workout(self.workout_name)

        # Set up CSV logging
        self._setup_csv_logging()

    def _setup_csv_logging(self):
        """Setup CSV file for logging pose landmarks"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Generate filename with timestamp and workout name
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = f"logs/pose_data_{self.workout_name}_{timestamp}.csv"
        
        # Create and write header to CSV file
        with open(self.csv_filename, 'w', newline='') as csvfile:
            fieldnames = ['frame', 'timestamp']
            # Add fields for all 33 landmarks (x, y, z for each)
            for i in range(33):
                fieldnames.extend([f'landmark{i}_x', f'landmark{i}_y', f'landmark{i}_z'])
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    
    def _save_landmarks_to_csv(self):
        """Save current landmarks to CSV file"""
        if self.POSE_LANDMARK_RESULT is None or not self.POSE_LANDMARK_RESULT.pose_landmarks:
            return
        
        with open(self.csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            
            # Start with frame number and timestamp
            row_data = [self.frame_count, self.frame_timestamp]
            
            # For the first detected pose (assuming there's at least one)
            landmarks = self.POSE_LANDMARK_RESULT.pose_landmarks[0]
            
            # Add all landmark coordinates
            for landmark in landmarks:
                row_data.extend([landmark.x, landmark.y, landmark.z])
            
            # Write the row
            writer.writerow(row_data)
    
    
    def create_workout(self, workout_name: str) -> object:
        workouts = {"push-ups": PushUps}
        return workouts[workout_name](
            goal_reps=self.goal_reps,
            ldmrk_res=self.POSE_LANDMARK_RESULT,
            left_side=self.left_side,
            strictness_crit=self.strictness_crit
        )

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
            output_segmentation_masks=True,
            result_callback=callback,
        )
        PoseLandmarker = PoseLandmarker.create_from_options(options)
        return PoseLandmarker

    def set_workout_type(self, workout_name: str) -> int:
        wourkouts = {"push-ups": 0, "abs": 1, "squats": 2}
        return wourkouts[workout_name]

    def print_result(self, result) -> None:
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

    def detect(self) -> np.ndarray:
        """Processes video frames, performs detection, and returns annotated frame."""
        fps =int(self.cap.get(cv2.CAP_PROP_FPS))
        
        #while self.cap.isOpened():
        #grab the frame
        success, im0 = self.cap.read()
        if not success:
            print(
                "Video frame is empty or video processing has been successfully completed."
            )
            if self.input_type.lower() != "live":
                self.cap.release() # Release video file
            return None

        frame = im0.copy()
        height, width, _ = frame.shape
        frame = cv2.resize(frame, (720, int(720 * height / width))) # Maintain aspect ratio
        h, w, _ = frame.shape # Get new dimensions for coordinate conversion
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)

        self.frame_timestamp += int(1000 / fps)  # Increment timestamp by frame duration
        
        # Process the image with the model and detect landmarks
        if self.input_type.lower() == "live":
            self.model.detect_async(mp_image, self.frame_timestamp)
        else:
            self.POSE_LANDMARK_RESULT = self.model.detect_for_video(
                mp_image, self.frame_timestamp
            )

        # Process the results

        annotated_img = frame

        if self.POSE_LANDMARK_RESULT and self.POSE_LANDMARK_RESULT.pose_landmarks:
            # Save landmarks to CSV after each frame
            self._save_landmarks_to_csv()

            annotated_img = self.draw_landmarks_on_image(annotated_img)

            
            res = self.POSE_LANDMARK_RESULT.pose_landmarks

            # Determine side on the first frame 
            if self.frame_count == 0:
                self.left_side = is_left_side(res)
                print(f"left side: {self.left_side}")
                #set current workout points to left side
                self.current_workout.left_side = self.left_side
                #update the indices of the current workout
                self.current_workout.update_indices()
                print(f'left side curr wo {self.current_workout.left_side}')
                self.current_workout.set_res(res)


            # Count reps
            self.current_workout.set_res(res)
            self.count_rep += self.current_workout.count_reps()

            # Form check
            self.current_workout.form = self.current_workout.get_form()
            print(f"form: {self.current_workout.form}")
            print(f"fix form: {self.current_workout.fix_form}")
            print(f"form: {self.current_workout.form}")


            
            


            # display form status
            form_color = (0, 255, 0) if self.current_workout.form else (0, 0, 255)
            cv2.putText(annotated_img,self.current_workout.fix_form, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, form_color, 2)


            #display angles
            display_angles = self.current_workout.get_display_angles()
            y_offset = 60
            landmarks_pixels = [(int(lm.x * w), int(lm.y * h)) for lm in res[0]] # Convert normalized to pixels
            print(f'display_angles {display_angles}')
            for angle_info in display_angles:
                name = angle_info["name"]
                value = angle_info["value"]
                indices = angle_info["joint_indices"]
                
                # Display Text
                angle_text = f"{name}: {value:.0f}"
                cv2.putText(annotated_img, angle_text, (20, y_offset), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
                y_offset += 30 # Move down for next angle text

                # Draw Arc
                try:
                    pt1_coords = landmarks_pixels[indices[0]]
                    pt2_coords = landmarks_pixels[indices[1]] # The joint where the arc is centered
                    pt3_coords = landmarks_pixels[indices[2]]
                    print(f"pt1: {pt1_coords}, pt2: {pt2_coords}, pt3: {pt3_coords}")
                    # Draw the arc
                    arc_color = (255, 255, 0) # Cyan
                    draw_angle_arc(annotated_img, pt1_coords, pt2_coords, pt3_coords, value, arc_color, 2)
                except IndexError:
                    print(f"Warning: Landmark index out of bounds for drawing angle '{name}'.")
                except Exception as e:
                     print(f"Error drawing arc for {name}: {e}")

            # add overlay of segmentation mask with color representing the form bool
            segmentation_mask = self.POSE_LANDMARK_RESULT.segmentation_masks[0].numpy_view()
            visualized_mask_colored = np.zeros_like(annotated_img, dtype=np.uint8)
            mask_color = (0, 255, 0) if self.current_workout.form else (0, 0, 255)
            bool_mask = segmentation_mask > 0.5
            visualized_mask_colored[bool_mask] = mask_color
            alpha = 0.1
            
            annotated_img[bool_mask] = cv2.addWeighted(
                annotated_img[bool_mask], 1.0 - alpha,
                visualized_mask_colored[bool_mask], alpha,
                0
            )


            #inctrement frame count
            self.frame_count += 1

        return annotated_img
