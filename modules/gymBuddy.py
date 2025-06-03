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
from modules.workouts.squats import Squats
from modules.db_setup import setup_database
from typing import Dict, Any
import duckdb
import json 
from modules.workouts.workoutParent import Workout 
from modules.feedbackAgent import FeedbackAgent

PoseLandmarkerResult = mp.tasks.vision.PoseLandmarkerResult


class GymBuddy:

    def __init__(
        self,
        source,
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
        #self.cap = cv2.VideoCapture(source)
        #assert self.cap.isOpened(), "Error: Could not open the camera."
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
        self.workout_completed:bool = False
        self.last_status_time:float = 0

        #set time for start of workout
        self.time:datetime = datetime.now()

        # Set up CSV logging
        self._setup_csv_logging()

        # Set up DuckDB
        self._setup_duckdb()

        self.feedback_agent:FeedbackAgent = FeedbackAgent(self.conn) 


    def _setup_csv_logging(self)-> None:
        """Setup CSV file for logging pose landmarks"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Generate filename with timestamp and workout name
        timestamp = self.time.strftime("%Y%m%d_%H%M")
        self.csv_filename = f"logs/pose_data_{self.workout_name}_{timestamp}.csv"
        
        # Create and write header to CSV file
        with open(self.csv_filename, 'w', newline='') as csvfile:
            fieldnames = ['frame', 'timestamp','workout_id']
            # Add fields for all 33 landmarks (x, y, z for each)
            for i in range(33):
                fieldnames.extend([f'landmark{i}_x', f'landmark{i}_y', f'landmark{i}_z'])
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    
    def _save_landmarks_to_csv(self)-> None:
        """Save current landmarks to CSV file"""
        if self.POSE_LANDMARK_RESULT is None or not self.POSE_LANDMARK_RESULT.pose_landmarks:
            return
        
        with open(self.csv_filename, 'a', newline='') as csvfile:
            writer = csv.writer(csvfile)
            time = datetime.now()
            # Start with frame number and timestamp
            row_data = [self.frame_count,time, self._current_workout_db_id]
            
            # For the first detected pose (assuming there's at least one)
            landmarks = self.POSE_LANDMARK_RESULT.pose_landmarks[0]
            
            # Add all landmark coordinates
            for landmark in landmarks:
                row_data.extend([landmark.x, landmark.y, landmark.z])
            
            # Write the row
            writer.writerow(row_data)

    def _setup_duckdb(self)-> None:
        """Setup DuckDB database for the analysed data"""
        # Create a DuckDB database connection
        self.conn = duckdb.connect('data/gymBuddy_db.db')
        #create the tables in the db if they do not exist
        setup_database(self.conn)

    def _close_duckdb(self)->None:
        """close the connection to the DuckDB database"""
        self.conn.close() 

    def _save_data_to_duckdb(self)-> None:
        """Save frame analysis data to a DuckDB database"""
        # if 1st frame, create a new workout entry
        time = datetime.now()
        if self.frame_count == 0:
            try:
                print(f"strict dev: {self.current_workout.get_strictness_deviation()}, strictness: {self.strictness}","workout name:", self.workout_name)
                self.conn.sql("""
                    INSERT INTO workout (workout_name, timestamp_start,rep_goal,
                    strictness_crit,strictness_definition, left_side)
                    VALUES (?,?,?,?,?,?) """,
                    params=[self.workout_name,
                        self.time,
                        self.goal_reps,
                        self.strictness,
                        self.current_workout.get_strictness_deviation(),
                        self.left_side])
                results = self.conn.sql(""" select id from workout where timestamp_start = ? """, params=[self.time]).fetchone()
                if results is not None:
                    self._current_workout_db_id:int = results[0]
                    print(f"New workout entry created with id {self._current_workout_db_id}.")
                else:
                    print("Error: No results found for the current workout.")
                    return 
            except Exception as e:
                print(f"Error inserting new workout: {e}")
                return
            print(self.conn.sql(""" SELECT * FROM workout """))
        #retrieve angles data from the current workout
        angles = self.current_workout.get_display_angles()
        print(f'angles data: {angles}')
        for angle in angles:
            angle['joint_indices'] = list(angle['joint_indices'])
        angles_json = json.dumps(angles)
        print(angles_json)

        #retrieve the landmarks of interest from the current workout
        ldmrks_of_interest = self.current_workout._get_indices()
        print(f"landmarks of interest: {ldmrks_of_interest}")
        ldmrks_keys = list(ldmrks_of_interest.keys())
        ldmrks_values = list(ldmrks_of_interest.values())

        self.conn.sql(""" INSERT INTO workout_analysis (workout_id, frame, timestamp, 
                    rep_count,down, form_issues,angles_data,ldmrks_of_interest)
                    VALUES (?,?,?,?,?,?,?,MAP(?, ?))""",
                    params=[self._current_workout_db_id,
                            self.frame_count,
                            time,
                            self.count_rep,
                            self.current_workout.down,
                            self.current_workout.fix_form,
                            angles_json,
                            ldmrks_keys,
                            ldmrks_values])
        
        print(f"Data saved to DuckDB for frame {self.frame_count}.")
        #print(self.conn.sql(""" SELECT * FROM workout_analysis """))
    
    
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

    def draw_landmarks_on_image(self, rgb_image: np.ndarray) -> np.ndarray:
        annotated_image = np.copy(rgb_image)
        if (self.POSE_LANDMARK_RESULT is None or 
            not hasattr(self.POSE_LANDMARK_RESULT, 'pose_landmarks') or 
            not self.POSE_LANDMARK_RESULT.pose_landmarks):
            return annotated_image 
        
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
            analysis_data["landmarks"] = [{"x": lm.x, "y": lm.y, "z": lm.z} for lm in res[0]]
            # Determine side on the first frame 
            if self.frame_count == 0:
                self.left_side = is_left_side(res)
                print(f"left side: {self.left_side}")
                #set current workout points to left side
                self.current_workout.left_side = self.left_side
                #update the indices of the current workout
                self.current_workout.update_indices()
                print(f'left side curr wo {self.current_workout.left_side}')


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

            '''
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
                    arc_color:tuple = (255, 255, 0) # Cyan
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
            print(f"frame: {self.frame_count}, timestamp: {self.frame_timestamp}, rep count: {self.count_rep}, goal reps: {self.goal_reps}")
            '''
            
            # save analysed data to duckdb 
            self._save_data_to_duckdb()
            # Save landmarks to CSV after each frame
            self._save_landmarks_to_csv()

            #increment frame count
            self.frame_count += 1

        return analysis_data
    
    def give_feedback(self):
        """ call to an Agent that will give feedback on the series that was done"""
        feedback:dict = self.feedback_agent.agent_pipeline()
        return feedback['formatted_feedback']
        
