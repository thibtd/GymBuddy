import mediapipe as mp
import cv2
import csv 
import os
from datetime import datetime
import numpy as np
from modules.utils import is_left_side
from modules.workouts.pushups import PushUps
from modules.workouts.squats import Squats
from modules.db_setup import setup_database
from typing import Dict, Any
import duckdb
import json 
from modules.workouts.workoutParent import Workout 
from modules.feedbackAgent import FeedbackAgent
import pandas as pd

PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult


class GymBuddy:

    def __init__(
        self,
        workout_name: str = "Push-ups",
        strictness_crit: str = "loose",
        input_type: str = "Video",
        model_path: str = "models/pose_landmarker_full.task",

    ):
        # set up the model
        self.input_type:str = input_type
        self.model_path:str = model_path
        self.model = self.create_model()

        # set up the camera
        self.frame_timestamp:float = 0
        self.frame_count:int = 0

        # set up the workout and static parameters
        self.workout_name:str = workout_name.lower()
        self.goal_reps:int = 0
        self.strictness:str = strictness_crit.lower()

        # set up the workout counter
        self.left_side:bool = False
        self.POSE_LANDMARK_RESULT = None
        self.count_rep:int = 0

        # set current workout
        self.current_workout:Workout = self.create_workout(self.workout_name)
        

        #set time for start of workout
        self.time:datetime = datetime.now()

        # Initialize buffers for logging and database
        self.workout_db_buffer:Dict[str, Any] = {}
        self.wo_analysis_buffer:list[Dict[str, Any]] = []
        self.raw_landmarks_buffer:list[Dict[str, Any]] = []

         
    def create_workout(self, workout_name: str) -> Workout:
        workouts = {"push-ups": PushUps, "abs": None, "squats": Squats}
        return workouts[workout_name](
            goal_reps=self.goal_reps,
            ldmrk_res=self.POSE_LANDMARK_RESULT,
            left_side=self.left_side,
            strictness_crit=self.strictness
        )

    def set_workout(self, workout_name: str):
        self.workout_name = workout_name
        print(f"Workout set to: {self.workout_name}")
        self.current_workout = self.create_workout(self.workout_name)
        print(f"Current workout: {self.current_workout}")

    def set_reps(self, reps: int):
        self.goal_reps = reps
        print(f"Reps set to: {self.goal_reps}")

    def set_strictness(self, strictness: str)->None:
        self.strictness = strictness.lower()

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


    def print_result(self, result) -> None:
        self.POSE_LANDMARK_RESULT = result


    def process_frame_from_bytes(self, frame_bytes):
        """Process frame data received from frontend"""
        try:
            # Convert bytes to numpy array
            nparr = np.frombuffer(frame_bytes, np.uint8)
            # Decode image
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            return frame
        except Exception as e:
            print(f"Error processing frame from bytes: {e}")
            return None
    
    def detect_from_frame(self, frame) -> dict:
        """Process a single frame for exercise detection"""
        if frame is None:
            return {}
        print(f'workout name: {self.workout_name}')
        print(f'current workout: {self.current_workout}')
        print(f'strictness: {self.strictness}')
        fps =30
    
        frame = frame.copy()
        height, width, _ = frame.shape
        frame = cv2.resize(frame, (720, int(720 * height / width))) # Maintain aspect ratio
        
        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=frame)

        self.frame_timestamp += int(1000 / fps)  # Increment timestamp by frame duration
        
        # Process the image with the model and detect landmarks
        if self.input_type.lower() == "live":
            self.model.detect_async(mp_image, self.frame_timestamp)
        else:
            self.POSE_LANDMARK_RESULT = self.model.detect_for_video(
                mp_image, self.frame_timestamp
            )

        # process the results
        #annotated_img = frame
        analysis_data = {
            "landmarks": [],
            "rep_count": self.count_rep,
            "form_ok": True,
            "form_message": "Initializing...",
            "display_angles": [],
            "is_down_phase": self.current_workout.down,
        }


        if self.POSE_LANDMARK_RESULT and self.POSE_LANDMARK_RESULT.pose_landmarks:

            #annotated_img = self.draw_landmarks_on_image(annotated_img)

            
            res = self.POSE_LANDMARK_RESULT.pose_landmarks
            analysis_data["landmarks"] = [{"x": lm.x, "y": lm.y} for lm in res[0]]
            
            # Determine side on the first frame 
            if self.frame_count == 0:
                self.left_side = is_left_side(res)
                print(f"left side: {self.left_side}")
                #set current workout points to left side
                self.current_workout.left_side = self.left_side
                #update the indices of the current workout
                self.current_workout.update_indices()
                print(f'left side curr wo {self.current_workout.left_side}')
                 #retrieve the landmarks of interest from the current workout
                ldmrks_of_interest = self.current_workout._get_indices()
                print(f"landmarks of interest: {ldmrks_of_interest}")
                ldmrks_keys = list(ldmrks_of_interest.keys())
                ldmrks_values = list(ldmrks_of_interest.values())
                # save the workout data to the buffer 
                self.workout_db_buffer = {
                    "workout_name": self.workout_name,
                    "timestamp_start": self.time,
                    "rep_goal": self.goal_reps,
                    "strictness_crit": self.strictness,
                    "strictness_definition": self.current_workout.get_strictness_deviation(),
                    "left_side": self.left_side,
                    "ldmrks_keys": ldmrks_keys,
                    "ldmrks_values": ldmrks_values
                }


            # Count reps
            self.current_workout.set_res(res)
            self.count_rep += self.current_workout.count_reps()

            # Form check
            self.current_workout.form = self.current_workout.get_form()
            print(f'down: {self.current_workout.down}')
            print(f"form: {self.current_workout.form}")
            print(f"fix form: {self.current_workout.fix_form}")

            # update analysis data
            analysis_data["rep_count"] = self.count_rep
            analysis_data["form_ok"] = self.current_workout.form
            analysis_data["form_message"] = self.current_workout.fix_form
            analysis_data["display_angles"] = self.current_workout.get_display_angles()
            analysis_data["is_down_phase"] = self.current_workout.down

            # add the analysis data to the buffer
            #retrieve angles data from the current workout
            angles = analysis_data["display_angles"].copy()
            print(f'angles data: {angles}')
            for angle in angles:
                angle['joint_indices'] = list(angle['joint_indices'])
            angles_json = json.dumps(angles)
            print(angles_json)

           

            data_to_buffer = {
                "frame": self.frame_count,
                "timestamp": datetime.now(),
                "rep_count": self.count_rep,
                "down": self.current_workout.down,
                "form_issues": self.current_workout.fix_form,
                "angles_data": angles_json
            }
            self.wo_analysis_buffer.append(data_to_buffer)

            # add landmarks to the landmarks buffer
            raw_landmarks = {
                "frame": self.frame_count,
                "timestamp": datetime.now(),
                "landmarks": analysis_data["landmarks"],
            }
            self.raw_landmarks_buffer.append(raw_landmarks)
           

            #increment frame count
            self.frame_count += 1

        return analysis_data
    
    '''def give_feedback(self):
        """ call to an Agent that will give feedback on the series that was done"""
        feedback:dict = self.feedback_agent.agent_pipeline()
        return feedback['formatted_feedback']'''

    def get_data_to_save(self) -> Dict[str, Any]:
        """Get the data to save to the database"""
        data_to_save = {
            "workout_db_buffer": self.workout_db_buffer.copy(),
            "wo_analysis_buffer": self.wo_analysis_buffer.copy(),
            "raw_landmarks_buffer": self.raw_landmarks_buffer.copy()
        }
        return data_to_save

    def reset_data_buffers(self) -> None:
        """Reset the data buffers after saving"""
        self.workout_db_buffer.clear()
        self.wo_analysis_buffer.clear()
        self.raw_landmarks_buffer.clear()
        self.frame_count = 0
        print("Data buffers reset.")
