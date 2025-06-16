import duckdb
import json 
import langchain
import os
import pandas as pd 
import numpy as np
from scipy import signal 
from datetime import datetime
from typing import Dict, Any, List, Optional, Union, cast
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

class FeedbackAgent:
    def __init__(self, db_conn:duckdb.DuckDBPyConnection,model:str='gemini-2.0-flash',
                 landmarks_details_loc:str='data/landmarks_details.csv'):
        
        self.model:str = model
        self.db_conn:duckdb.DuckDBPyConnection = db_conn
        self.landmarks_details_loc:str = landmarks_details_loc

        # dataset
        self.workout_metadata:pd.DataFrame = pd.DataFrame()
        self.workout_analysis:pd.DataFrame = pd.DataFrame()
        self.landmarks:pd.DataFrame = pd.DataFrame()
        self.landmarks_details:pd.DataFrame = pd.DataFrame()

        # Initialize the LLM model
        
        google_key = os.environ.get("GOOGLE_API_KEY")
        
        self.llm = ChatGoogleGenerativeAI(model=self.model,google_api_key=google_key)

            
    def load_workout_data(self):
        """Load workout data from the database, landmarks details and tracking data.
        """
        print(self.db_conn.sql("SHOW ALL TABLES"))
        # Load the data from the database 
        try:
            self.workout_metadata = self.db_conn.sql(""" select * from workout """).df()
            self.workout_analysis = self.db_conn.sql(""" select * from workout_analysis """).df()
            self.landmarks_details = self.db_conn.sql(""" select * from raw_landmarks """).df()
        except Exception as e:
            print(f"Error loading workout data: {e}")
            raise e
        #last workout id 
        last_workout_id = self.workout_metadata['ID'].max()

        # keep only the last workout
        self.workout_metadata = self.workout_metadata.loc[self.workout_metadata['ID'] == last_workout_id]
        self.workout_analysis = self.workout_analysis.loc[self.workout_analysis['workout_id'] == last_workout_id]
        self.landmarks_details = self.landmarks_details.loc[self.landmarks_details['workout_id'] == last_workout_id]
        

    def extract_workout_data(self)->Dict[str, Any]:
        """Extract detailed metrics from the combined data"""

        # Check if we have workout data
        if self.workout_metadata.empty or self.workout_analysis.empty:
            raise ValueError("No workout data available. Please load workout data first.")

        # Time variables
        if not self.workout_analysis.empty and 'timestamp' in self.workout_analysis.columns:
            start_time = pd.to_datetime(self.workout_analysis['timestamp'].iloc[0])
            end_time = pd.to_datetime(self.workout_analysis['timestamp'].iloc[-1])
            total_time = (end_time - start_time).total_seconds()
        else:
            total_time = 0

        # Get reps completed safely
        reps_completed = 0
        if not self.workout_analysis.empty and 'rep_count' in self.workout_analysis.columns:
            reps_completed = int(self.workout_analysis['rep_count'].max())

        # Get rep goal safely
        rep_goal = "Unknown"
        if not self.workout_metadata.empty and 'rep_goal' in self.workout_metadata.columns:
            rep_goal = self.workout_metadata['rep_goal'].iloc[0]
            
        # Get strictness criteria safely
        strictness_crit = "Unknown"
        if not self.workout_metadata.empty and 'strictness_crit' in self.workout_metadata.columns:
            strictness_crit = self.workout_metadata['strictness_crit'].iloc[0]
            
        # Get strictness definition safely
        strictness_definition = "Unknown"
        if not self.workout_metadata.empty and 'strictness_definition' in self.workout_metadata.columns:
            strictness_definition = self.workout_metadata['strictness_definition'].iloc[0]
            
        # Get landmarks of interest safely
        ldmrks_interest = []
        if not self.workout_analysis.empty and 'ldmrks_of_interest' in self.workout_analysis.columns:
            ldmrks_raw = self.workout_analysis['ldmrks_of_interest'].iloc[0]
            if ldmrks_raw is not None:
                if isinstance(ldmrks_raw, list):
                    ldmrks_interest = ldmrks_raw
                elif isinstance(ldmrks_raw, str):
                    try:
                        ldmrks_interest = json.loads(ldmrks_raw)
                    except json.JSONDecodeError:
                        ldmrks_interest = [ldmrks_raw]
                        
        # Get side shown safely
        side_shown = 'unknown'
        if not self.workout_metadata.empty and 'left_side' in self.workout_metadata.columns:
            side_shown = 'left' if self.workout_metadata['left_side'].iloc[0] else 'right'

        # Basic metrics
        metrics = {
            'workout_name': self.workout_metadata['workout_name'].iloc[0] if not self.workout_metadata.empty and 'workout_name' in self.workout_metadata.columns else "Unknown",
            'timestamp': self.workout_metadata['timestamp_start'].iloc[0] if not self.workout_metadata.empty and 'timestamp_start' in self.workout_metadata.columns else "Unknown",
            'total_frames': len(self.workout_analysis),
            'duration_seconds': int(np.round(total_time, 0)),
            'reps_completed': reps_completed,
            'reps_goal': rep_goal,
            'strictness_crit': strictness_crit,
            'strictness_definition': strictness_definition,
            'ldmrks_interest': ldmrks_interest,
            'side_shown': side_shown,
        }
        # Extract angle data
        angle_data: pd.DataFrame = pd.DataFrame()
        for idx, row in self.workout_analysis.iterrows():
            # Parse angles from JSON if it's stored that way
            try:
                if 'angles_data' not in row or row['angles_data'] is None:
                    continue
                    
                angles = row['angles_data']
                if isinstance(angles, str):
                    angles = json.loads(angles)
                    
                # Handle both array of objects and dictionary formats
                if isinstance(angles, list):
                    for angle_obj in angles:
                        if isinstance(angle_obj, dict) and 'name' in angle_obj and 'value' in angle_obj:
                            angle_data.at[idx, angle_obj['name']] = angle_obj['value']
                elif isinstance(angles, dict):
                    for angle_name, value in angles.items():
                        angle_data.at[idx, angle_name] = value
            except (AttributeError, KeyError, json.JSONDecodeError, TypeError) as e:
                print(f"Error processing angles for frame {idx}: {e}")
        # Calculate detailed angle statistics
        angle_stats = {}
        for column in angle_data.columns:
            angle_stats[column] = {
                'min': angle_data[column].min(),
                'max': angle_data[column].max(),
                'mean': angle_data[column].mean(),
                'median': angle_data[column].median(),
                'std': angle_data[column].std(),
                'range': angle_data[column].max() - angle_data[column].min(),
                # Add percentiles to better understand distribution
                'p25': angle_data[column].quantile(0.25),
                'p75': angle_data[column].quantile(0.75)
            }
        
        # Analyze form issues
        form_issues = []
        if 'form_issues' in self.workout_analysis.columns:
            form_issues = self.workout_analysis['form_issues'].unique().tolist()
            form_issues = [issue for issue in form_issues if issue and isinstance(issue, str) and issue != "Checking form..."]
        
        # Count frequency of each form issue
        issue_counts = {}
        for issue in form_issues:
            issue_counts[issue] = sum(self.workout_analysis['form_issues'].astype(str).str.contains(issue, regex=False, na=False))
        
        # Analyze landmarks if available
        landmark_metrics = {}
        if not self.landmarks.empty:
            # Calculate movement range for key points
            for i in range(33):  # Assuming 33 landmarks
                try:
                    # Find landmark name in reference dataframe
                    if not self.landmarks_details.empty and 'index' in self.landmarks_details.columns and i in self.landmarks_details['index'].values:
                        landmark_idx_rows = self.landmarks_details[self.landmarks_details['index'] == i]
                        if not landmark_idx_rows.empty and 'name' in landmark_idx_rows.columns:
                            landmark_name = landmark_idx_rows['name'].iloc[0]
                            
                            # Check if the columns exist before calculating ranges
                            x_col = f'landmark{i}_x'
                            y_col = f'landmark{i}_y'
                            z_col = f'landmark{i}_z'
                            
                            # Only calculate if columns exist
                            if all(col in self.landmarks.columns for col in [x_col, y_col, z_col]):
                                x_range = self.landmarks[x_col].max() - self.landmarks[x_col].min()
                                y_range = self.landmarks[y_col].max() - self.landmarks[y_col].min()
                                z_range = self.landmarks[z_col].max() - self.landmarks[z_col].min()
                                
                                landmark_metrics[landmark_name] = {
                                    'x_range': x_range,
                                    'y_range': y_range,
                                    'z_range': z_range,
                                    'total_movement': (x_range**2 + y_range**2 + z_range**2)**0.5
                                }
                except (KeyError, IndexError) as e:
                    print(f"Error processing landmark {i}: {e}")
        
        # Detect repetition consistency
        rep_consistency = {'note': 'Not enough data to calculate repetition consistency'}
        if not angle_data.empty and 'elbow' in angle_data.columns:
            # Use elbow angle to detect repetition consistency
            try:
                elbow_angles = angle_data['elbow']
                
                # Find local minima (bottom of push-up)
                bottom_indices, _ = signal.find_peaks(-elbow_angles, distance=15)  # Adjust distance based on your data
                if len(bottom_indices) > 0:
                    bottom_angles = elbow_angles.iloc[bottom_indices]
                    
                    if len(bottom_angles) > 0:
                        rep_consistency = {
                            'bottom_angles_mean': bottom_angles.mean(),
                            'bottom_angles_std': bottom_angles.std(),
                            'rep_regularity': bottom_angles.std() / bottom_angles.mean() if bottom_angles.mean() != 0 else None
                        }
            except Exception as e:
                print(f"Error calculating repetition consistency: {e}")
        
        # Combine all metrics
        return {
            'basic': metrics,
            'angle_stats': angle_stats,
            'form_issues': form_issues,
            'issue_counts': issue_counts,
            'landmarks': landmark_metrics,
            'rep_consistency': rep_consistency,
            'has_landmarks': not self.landmarks.empty,
            'angle_data': angle_data  # Include processed angle data
        }

    def generate_feedback(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Generate feedback based on the extracted workout data"""
        """Use an LLM to generate detailed feedback on the workout performance"""
    
        # Check if we have the necessary metrics
        if not metrics or 'basic' not in metrics:
            raise ValueError("Invalid metrics data provided")
            
        # Access basic metrics safely
        basic_metrics = metrics.get('basic', {})
        workout_name = basic_metrics.get('workout_name', 'Unknown workout')
        reps_completed = basic_metrics.get('reps_completed', 0)
        reps_goal = basic_metrics.get('reps_goal', 'Unknown')
        duration_seconds = basic_metrics.get('duration_seconds', 0)
        strictness_crit = basic_metrics.get('strictness_crit', 'Unknown')
        strictness_definition = basic_metrics.get('strictness_definition', 'Unknown')
        side_shown = basic_metrics.get('side_shown', 'Unknown')
        ldmrks_interest = basic_metrics.get('ldmrks_interest', [])
        
        # Create a prompt for the LLM based on metrics
        prompt = f"""
        Analyze this {workout_name} workout performance and provide concise feedback.
        
        WORKOUT DATA:
        - Completed {reps_completed} out of {reps_goal} repetitions
        - Workout strictness: {strictness_crit} with a leeway of {strictness_definition} degrees deviation from a flat (180 degree) body angle
        to be considered good.
        - Workout duration: {duration_seconds} seconds

        BODY SIDE SHOWN: 
        {side_shown}
        
        FORM ISSUES:
        {chr(10).join([f"- {issue}" for issue in metrics.get('form_issues', ['No issues detected'])])}. All the issues except the ones containing "Good form!..." are negative.
        
        KEY ANGLE MEASUREMENTS:
        {"".join([f"- {angle}: min={stats['min']:.1f}°, max={stats['max']:.1f}°, range={stats['range']:.1f}° \n" for angle, stats in metrics.get('angle_stats', {}).items()])}

        BODY MOVEMENT:
        {chr(10).join([f"- {landmark}: x={data['x_range']:.1f}, y={data['y_range']:.1f}, z={data['z_range']:.1f}" for landmark, data in metrics.get('landmarks', {}).items()])}

        BODY PARTS OF INTEREST:
        {chr(10).join([f"{i}: {landmark}" for i, landmark in enumerate(ldmrks_interest)])}

        YOUR OUTPUT MUST FOLLOW THE FOLLWOING RULES and FORMAT:
        RULES:
        1. Include exactly these three sections with exactly these emoji and headings
        2. Use bullet points for each feedback item
        3. Keep each bullet to 3-4 sentences maximum
        4. Do not include any text before or after these three sections
        5. Give meaning to the feedback, do not just repeat the data.
        6. Give meaning to the numbers, anchoring them to the workout goal and their real life meaning.
        7. You can only suggest one or two things to improve at a time, not more.
        8. Suggest only the following workouts: Push-ups, Squats. 
        
        FORMAT:
        💪 **POSITIVES**

        🔍 **IMPROVEMENT AREAS**
        
        🏋️‍♂️ **ACTIONABLE TIPS**
        """
        try:
            # Call the LLM using LangChain
            messages = [
                SystemMessage(content="You are a professional fitness coach specializing in calisthenics and bodyweight exercises."),
                HumanMessage(content=prompt),
            ]
            response = self.llm.invoke(messages)

            # Extract the response content
            feedback_text = response.content

            # ... (rest of your existing code to structure and return the feedback) ...
            feedback_dict = {
                'workout_name': workout_name,
                'reps_completed': reps_completed,
                'reps_goal': reps_goal,
                'duration': duration_seconds,
                'strictness': strictness_crit,
                'detailed_feedback': feedback_text,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            return feedback_dict
            
        except Exception as e:
            # Fallback to template-based feedback if LLM fails
            return {
                'workout_name': workout_name,
                'reps_completed': reps_completed,
                'reps_goal': reps_goal,
                'duration': duration_seconds,
                'strictness': strictness_crit,
                'detailed_feedback': f"Error getting LLM feedback: {str(e)}. Falling back to template feedback.",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        

    def format_feedback(self, feedback_dict: Dict[str, Any]) -> str:
        """Format the feedback into a structured HTML template for direct frontend rendering"""

        # Get feedback values safely with defaults
        workout_name = feedback_dict.get('workout_name', 'N/A')
        reps_completed = feedback_dict.get('reps_completed', 'N/A')
        reps_goal = feedback_dict.get('reps_goal', 'N/A')
        duration = feedback_dict.get('duration', 'N/A')
        strictness = feedback_dict.get('strictness', 'N/A')
        timestamp = feedback_dict.get('timestamp', 'N/A')
        detailed_feedback = feedback_dict.get('detailed_feedback', '')

        # Convert markdown feedback to HTML using Python's markdown lib
        try:
            import markdown
            # Remove leading/trailing whitespace and ensure consistent newlines
            feedback_html = markdown.markdown(detailed_feedback.strip(), extensions=['extra'])
        except ImportError:
            # Fallback: wrap in <pre> if markdown is not available
            feedback_html = f"<pre>{detailed_feedback}</pre>"

        template = f"""
            <div class=\"feedback-details\">
                {feedback_html}
            </div>
            <hr>
            <div class=\"feedback-disclaimer\">
                <em>Analysis generated on {timestamp}. This analysis was generated using artificial intelligence and should be considered as general guidance rather than professional fitness advice. Always consult with a certified trainer for personalized recommendations.</em>
            </div>
        </section>
        """
        return template

    def agent_pipeline(self)->Dict[str,Any]:
        """Main pipeline to extract data, generate feedback and format it"""

        # load the workout data
        self.load_workout_data()
        
        print(self.workout_metadata)
        print(self.workout_analysis)
        # Check if we have workout data
        if self.workout_metadata.empty or self.workout_analysis.empty:
            print("No workout data available.")
            raise ValueError("No workout data available. Please load workout data first.")
            
        try:
            # extract the workout data
            metrics = self.extract_workout_data()
            # generate the feedback
            print("Generating feedback...")
            feedback = self.generate_feedback(metrics)
            # format the feedback
            formatted_feedback = self.format_feedback(feedback)

            return {
                'formatted_feedback': formatted_feedback,
                'metrics': metrics,
                'feedback': feedback
            }
        except Exception as e:
            print(f"Error in agent pipeline: {e}")
            raise e



if __name__ == "__main__":
    conn = duckdb.connect("data/gymBuddy_db.db")
    model = 'gemini-2.5-flash'  # or any other model you want to use
    feedback_agent = FeedbackAgent(conn)
    
    
    try:
        feedback = feedback_agent.agent_pipeline()
        
        if feedback:
            print(feedback['formatted_feedback'])
        else:
            print("No feedback was generated.")
    except Exception as e:
        print(f"Error generating feedback: {e}")
    finally:
        # Close the database connection
        if conn is not None:
            conn.close()
