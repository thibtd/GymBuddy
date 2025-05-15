import duckdb
import json 
import ollama 
import pandas as pd 
import numpy as np
from scipy import signal 
from datetime import datetime
import subprocess
from typing import Dict, Any


class FeedbackAgent:
    def __init__(self, db_conn:duckdb.DuckDBPyConnection,model:str='gemma3:1b',landmarks_folder:str = 'logs/',
                 landmarks_details_loc:str='data/landmarks_details.csv'):
        self.model:str = model
        self.db_conn:duckdb.DuckDBPyConnection = db_conn
        self.landmarks_folder:str = landmarks_folder
        self.landmarks_details_loc:str = landmarks_details_loc

        # dataset
        self.workout_metadata:pd.DataFrame = pd.DataFrame()
        self.workout_analysis:pd.DataFrame = pd.DataFrame()
        self.landmarks:pd.DataFrame = pd.DataFrame()
        self.landmarks_details:pd.DataFrame = pd.DataFrame()



    def model_available(self)->bool:
        # check if the model is already loaded 
        model_list = ollama.list()
        available_models = [model['model']  for model in model_list.get('models', [])]
        if self.model in available_models:
            print(f"Model {self.model} is already loaded.")
            return True
        else:
            print(f"Loading model {self.model}...")
            # Load the model
            try:
                ollama.pull(self.model)
                print(f"Model {self.model} loaded successfully.")
                return True
            except Exception as e:
                print(f"Error loading model {self.model}: {e}")
                return False
            
    def load_workout_data(self):
        """Load workout data from the database, landmarks details and tracking data.
        """
        print(self.db_conn.sql("SHOW ALL TABLES"))
        # Load the datat from the database 
        self.workout_metadata = self.db_conn.sql(""" select * from workout """).df()
        self.workout_analysis = self.db_conn.sql(""" select * from workout_analysis """).df()
        # load landmarks details
        self.landmarks_details = pd.read_csv(self.landmarks_details_loc)
        
        #last workout id 
        last_workout_id = self.workout_metadata['ID'].max()

        # keep only the last workout
        self.workout_metadata = self.workout_metadata.loc[self.workout_metadata['ID'] == last_workout_id]
        self.workout_analysis = self.workout_analysis.loc[self.workout_analysis['workout_id'] == last_workout_id]

        # load landmarks logs, i.e. the tracking data
        time_start = pd.Timestamp(self.workout_metadata.loc[self.workout_metadata['ID'] == last_workout_id, 'timestamp_start'].values[0]).strftime('%Y%m%d_%H%M')
        #print("Last workout time: ", time_start)
        workout_name = self.workout_metadata.loc[self.workout_metadata['ID'] == last_workout_id, 'workout_name'].values[0]
        #print("Last workout name: ", workout_name)
        landmarks_file = f"{self.landmarks_folder}pose_data_{workout_name}_{time_start}.csv"
        #print(f"Landmarks file: {landmarks_file}")
        try:
            self.landmarks = pd.read_csv(landmarks_file)
            print(f"Landmarks data loaded from {landmarks_file}.")
        except FileNotFoundError:
            print(f"Landmarks file {landmarks_file} not found.")
            self.landmarks = None
    
        


        
    def extract_workout_data(self)->Dict[str, Any]:
        """Extract detailed metrics from the combined data"""

        #time variables
        start_time:datetime = pd.to_datetime(self.workout_analysis['timestamp'].iloc[0])
        end_time:datetime = pd.to_datetime(self.workout_analysis['timestamp'].iloc[-1])
        total_time:float = (end_time - start_time).total_seconds()

        # Basic metrics
        metrics:dict[str,Any] = {
            'workout_name': self.workout_metadata['workout_name'],
            'timestamp': self.workout_metadata['timestamp_start'],
            'total_frames': len(self.workout_analysis),
            'duration_seconds': int(np.round(total_time,0)),
            'reps_completed': self.workout_analysis['rep_count'].max() if not self.workout_analysis.empty else 0,
            'reps_goal': self.workout_metadata['rep_goal'] if 'rep_goal' in self.workout_metadata else "Unknown",
            'strictness_crit': self.workout_metadata['strictness_crit'] if 'strictness_crit' in self.workout_metadata else "Unknown",
            'strictness_definition' : self.workout_metadata['strictness_definition'] if 'strictness_definition' in self.workout_metadata else 'Unknown',
            'ldmrks_interest': self.workout_analysis['ldmrks_of_interest'].iloc[0] if 'ldmrks_of_interest' in self.workout_analysis.columns else [],
            'side_shown': 'left' if self.workout_metadata['left_side'].iloc[0] else 'right',
        }
        # Extract angle data
        angle_data:pd.DataFrame = pd.DataFrame()
        for idx, row in self.workout_analysis.iterrows():
            # Parse angles from JSON if it's stored that way
            try:
                angles = list(row['angles_data'])
                if isinstance(angles, str):
                    angles = json.loads(angles)
                    
                    
                # Handle both array of objects and dictionary formats
                if isinstance(angles, list):
                    for angle_obj in angles:
                        angle_data.loc[idx, angle_obj['name']] = angle_obj['value']
                elif isinstance(angles, dict):
                    for angle_name, value in angles.items():
                        angle_data.loc[idx, angle_name] = value
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
                    if i in self.landmarks_details['index'].values:
                        landmark_name = self.landmarks_details.loc[self.landmarks_details['index'] == i, 'name'].values[0]
                        
                        # Check if the columns exist before calculating ranges
                        x_col = f'landmark{i}_x'
                        y_col = f'landmark{i}_y'
                        z_col = f'landmark{i}_z'
                        
                        # Only calculate if columns exist
                        if x_col in self.landmarks.columns and y_col in self.landmarks.columns and z_col in self.landmarks.columns:
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
        if len(angle_data) > 0 and 'elbow' in angle_data.columns:
            # Use elbow angle to detect repetition consistency
            elbow_angles = angle_data['elbow']
            
            # Find local minima (bottom of push-up)
            try:
                bottom_indices, _ = signal.find_peaks(-elbow_angles, distance=15)  # Adjust distance based on your data
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

    def generate_feedback(self, metrics:Dict[str, Any])->Dict[str, Any]:
        """Generate feedback based on the extracted workout data"""
        """Use an LLM to generate detailed feedback on the workout performance"""
    
        # Create a prompt for the LLM based on metrics
        prompt = f"""
        Analyze this {metrics['basic']['workout_name']} workout performance and provide concise feedback.
        
        WORKOUT DATA:
        - Completed {metrics['basic']['reps_completed']} out of {metrics['basic']['reps_goal']} repetitions
        - Workout strictness: {metrics['basic']['strictness_crit']} with a leeway of {metrics['basic']['strictness_definition']} degrees deviation from a flat (180 degree) body angle
        to be considered good.
        - Workout duration: {metrics['basic']['duration_seconds']} seconds

        BODY SIDE SHOWN: 
        {metrics['basic']['side_shown']}
        
        FORM ISSUES:
        {chr(10).join([f"- {issue}" for issue in metrics.get('form_issues', ['No issues detected'])])}. All the issues except the ones containing "Good form!..." are negative.
        
        KEY ANGLE MEASUREMENTS:
        {"".join([f"- {angle}: min={stats['min']:.1f}°, max={stats['max']:.1f}°, range={stats['range']:.1f}° \n" for angle, stats in metrics.get('angle_stats', {}).items()])}

        BODY MOVEMENT:
        {chr(10).join([f"- {landmark}: x={metrics['landmarks'][landmark]['x_range']:.1f}, y={metrics['landmarks'][landmark]['y_range']:.1f}, z={metrics['landmarks'][landmark]['z_range']:.1f}" for landmark in metrics.get('landmarks', {}).keys()])}

        BODY PARTS OF INTEREST:
        {chr(10).join([f"{i}: {landmark}" for i, landmark in enumerate(metrics['basic']['ldmrks_interest'])])}

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
        🏋️‍♂️**ACTIONABLE TIPS**
    
        """
        
        try:
            # 
            self.model_available()
            # Call the LLM
            response = ollama.chat(
                model='gemma3:1b',
                messages=[
                    {
                        'role': 'system',
                        'content': 'You are a professional fitness coach specializing in calisthenics and bodyweight exercises.'
                    },
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ]
            )
            
            # Extract the response content and standardize formatting
            feedback_text = response['message']['content']
            
            
            # Create structured feedback dictionary
            feedback_dict = {
                'workout_name': metrics['basic']['workout_name'],
                'reps_completed': metrics['basic']['reps_completed'],
                'reps_goal': metrics['basic']['reps_goal'],
                'duration': metrics['basic']['duration_seconds'],
                'strictness': metrics['basic']['strictness_crit'],
                'detailed_feedback': feedback_text,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Return the structured feedback
            return feedback_dict
            
        except Exception as e:
            # Fallback to template-based feedback if LLM fails
            return {
                'workout_name': metrics['basic']['workout_name'],
                'reps_completed': metrics['basic']['reps_completed'],
                'reps_goal': metrics['basic']['reps_goal'],
                'duration': metrics['basic']['duration_seconds'],
                'strictness': metrics['basic']['strictness_crit'],
                'detailed_feedback': f"Error getting LLM feedback: {str(e)}. Falling back to template feedback.",
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        

    def format_feedback(self, feedback_dict:dict)->str:
        """Convert feedback dictionary to standardized HTML format"""
        
        # Helper function to convert markdown-like LLM output to HTML
        def format_llm_details_to_html(details_text: str) -> str:
            if not details_text or not isinstance(details_text, str):
                return "<p>No detailed feedback available.</p>"

            html_output = []
            
            # Replace markdown headers with HTML headers
            details_text = details_text.replace("💪 **POSITIVES**", "<h4>💪 POSITIVES</h4>")
            details_text = details_text.replace("🔍 **IMPROVEMENT AREAS**", "<h4>🔍 IMPROVEMENT AREAS</h4>")
            details_text = details_text.replace("🏋️‍♂️**ACTIONABLE TIPS**", "<h4>🏋️‍♂️ ACTIONABLE TIPS</h4>") # Adjusted emoji to match prompt
            details_text = details_text.replace("💡 **ACTIONABLE TIPS**", "<h4>💡 ACTIONABLE TIPS</h4>") # Keep if this variant is also possible


            lines = details_text.split('\n')
            in_list = False
            for line in lines:
                line = line.strip()
                if not line:
                    if in_list:
                        html_output.append("</ul>")
                        in_list = False
                    continue

                if line.startswith("<h4>"):
                    if in_list:
                        html_output.append("</ul>")
                        in_list = False
                    html_output.append(line)
                elif line.startswith("- "):
                    if not in_list:
                        html_output.append("<ul>")
                        in_list = True
                    html_output.append(f"<li>{line[2:].strip()}</li>")
                elif line: # Handle lines that are not headers or list items (e.g. if LLM adds extra text)
                    if in_list:
                        html_output.append("</ul>")
                        in_list = False
                    html_output.append(f"<p>{line}</p>")


            if in_list:
                html_output.append("</ul>")
            
            return "\n".join(html_output)

        detailed_feedback_html = format_llm_details_to_html(feedback_dict.get('detailed_feedback', ''))

        template = f"""
        <div class="workout-feedback">
            <h1>Workout Analysis: {feedback_dict.get('workout_name', 'N/A')}</h1>
            <h3>Session Overview</h3>
            <ul>
                <li><strong>Reps Completed:</strong> {feedback_dict.get('reps_completed', 'N/A')}/{feedback_dict.get('reps_goal', 'N/A')}</li>
                <li><strong>Duration:</strong> {feedback_dict.get('duration', 'N/A')} seconds</li>
                <li><strong>Strictness Level:</strong> {feedback_dict.get('strictness', 'N/A')}</li>
            </ul>

            <h3>Feedback</h3>
            <div class="detailed-feedback-content">
                {detailed_feedback_html}
            </div>
            
            <hr>
            <p><em>Analysis generated on {feedback_dict.get('timestamp', 'N/A')}</em></p>
        </div>
        """
        return template

    def agent_pipeline(self):
        """Main pipeline to extract data, generate feedback and format it"""
        # make sure the model is available
        if not self.model_available():
            print("Model is not available.")
            return
        else:
            print("Model is available.")
            # load the workout data
            self.load_workout_data()
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



if __name__ == "__main__":
    conn = duckdb.connect("data/gymBuddy_db.db")
    model = 'gemma3:1b'
    feedback_agent = FeedbackAgent(conn)
    #feedback_agent.model_available()
    #feedback_agent.load_workout_data()
    #print(f"""workout_metadata: {feedback_agent.workout_metadata}""")
    #print(f"""workout_analysis: {feedback_agent.workout_analysis}""")
    #print(f"""landmarks: {feedback_agent.landmarks}""")
    #print(f"""landmarks_details: {feedback_agent.landmarks_details}""")
    #extracted_data = feedback_agent.extract_workout_data()
    #print(extracted_data)
    #print('Generating feedback...')
    #feedback = feedback_agent.generate_feedback(extracted_data)
    #formatted_feedback = feedback_agent.format_feedback(feedback)
    #print(formatted_feedback)
    feedback = feedback_agent.agent_pipeline()
    
    print(feedback['formatted_feedback'])
    feedback_agent.db_conn.close()
