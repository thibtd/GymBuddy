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
    def __init__(self, db_conn:duckdb.DuckDBPyConnection,model:str='gemini-2.0-flash'):
        
        self.model:str = model
        self.db_conn:duckdb.DuckDBPyConnection = db_conn

        # dataset
        self.id_used:int = 0
        self.frame_start:int =0
        self.metadata:pd.Series = pd.Series()
        self.workout_analysis:dict = dict()
        self.landmarks:dict = dict()

        # Initialize the LLM model
        
        google_key = os.environ.get("GOOGLE_API_KEY")
        
        self.llm = ChatGoogleGenerativeAI(model=self.model,google_api_key=google_key)

            
    def get_id_frame(self)->dict[str,int]| None:
        try:
            query_id:str = "Select max(id) from workout"
            res_id:tuple|None = conn.sql(query_id).fetchone()
            if res_id is None:
                raise ValueError("No id found in database.")
            else:
                workout_id:int = res_id[0]
            # get the first good form and backtrack 10 frames as the start frame (the idea is to avoid analysing the frames when user is setting up)
            strat_frame_query:str = f" SELECT  frame from workout_analysis  where workout_id ={workout_id} and SUBSTRING(form_issues,1,4)= 'Good' order by frame"
            res_start_frame:tuple|None= conn.sql(strat_frame_query).fetchone() 
            if res_start_frame is None:
                raise ValueError("No analysis data found for the last workout.")
            else:
                frame_start:int = res_start_frame[0]-10
        except Exception as e:
            print(f"Error retrieving data: {e}")
            return None
        return {'id': workout_id, 'self.frame_start': frame_start}
    
    def extract_metadata(self)-> pd.Series:
        try:
            metadata:pd.DataFrame = conn.sql(f"SELECT * FROM workout where id = {self.id_used}").df()
            if metadata is None:
                raise ValueError("No metadata found for the last workout.")
            end_time_query = f"SELECT max(timestamp) FROM workout_analysis where workout_id = {self.id_used}"
            end_time:tuple|None = conn.sql(end_time_query).fetchone()
            if end_time is None:
                raise ValueError("No end time found for the last workout.")
            end_time = end_time[0]
            metadata['end_time'] = end_time
            metadata['duration']= metadata.apply(lambda x: round((x['end_time']-x['timestamp_start']).total_seconds(),2),axis=1)
        except Exception as e:
            print(f"Error retrieving metadata: {e}")
            return pd.Series()
        
        return metadata.iloc[0]
    
    def extract_analysis(self)-> dict[str,Any]:
        try: 
            # get total number of reps 
            tot_reps_query:str = f"select max(rep_count) from workout_analysis where workout_id = {self.id_used} and frame >= {self.frame_start}"
            total_reps_res:tuple|None = conn.sql(tot_reps_query).fetchone()
            if total_reps_res is None:
                raise ValueError("No analysis data found for current workout")
            else:
                total_reps:int = total_reps_res[0]
            
            # duration of each repetitons 
            frames_rep_query:str = f"""select min(frame) as start_frame,max(frame) as end_frame,rep_count+1 as repetitions, round(epoch(max(timestamp) - min(timestamp)),1) as duration ,
                        from workout_analysis where workout_id = {self.id_used} and frame>= {self.frame_start} and repetitions <= {self.metadata['rep_goal']} group by rep_count"""
            frames_rep:pd.DataFrame = conn.sql(frames_rep_query).df()
            
            # average time rep 
            avg_duration:float = round(frames_rep['duration'].mean(),2)
            
            # form issues
            form_issues_query:str = f"""SELECT form_issues, count(*) as count FROM workout_analysis WHERE workout_id = {self.id_used} AND frame >= {self.frame_start} GROUP BY form_issues"""
            form_issues:list = conn.sql(form_issues_query).fetchall()
            
            frames_issues_quesry:str = f"""SELECT  form_issues, LIST(frame) FROM workout_analysis WHERE workout_id = {self.id_used} AND frame >= {self.frame_start} and form_issues not like 'Good form' group by form_issues  """
            frames_w_issues:list = conn.sql(frames_issues_quesry).fetchall()
            
            worst_reps_query:str = f"""SELECT rep_count+1 as repetitions, count(form_issues) as count
            FROM workout_analysis 
            WHERE workout_id = {self.id_used} AND frame >= {self.frame_start} and 
            form_issues not like 'Good form'
            GROUP BY repetitions
            ORDER BY count DESC
            LIMIT 3"""
            worst_reps:list = conn.sql(worst_reps_query).fetchall()
            
            # exctract angles data 
            dif_angles_query:str = f""" select list(distinct(angle_element.name)) as angle_names FROM workout_analysis, UNNEST(angles_data) as t(angle_element)"""
            diff_names_ang_res:tuple|None = conn.sql(dif_angles_query).fetchone()
            if diff_names_ang_res is None:
                raise ValueError("Error exctracting names of angles")
            else:
                different_names:list = diff_names_ang_res[0]
            
            cases:list[str] = [f"""MAX(case WHEN element.name ='{name}' THEN round(element.value,2) end) as {name}_angle,
            MAX(case WHEN element.name ='{name}' THEN element.joint_indices end) as {name}_indices
            """ for name in different_names]
            angles_query:str= f"""select frame, {','.join(cases)} from workout_analysis, unnest(angles_data) as t(element) where workout_id = {self.id_used} AND frame >= {self.frame_start}
            and form_issues not like 'Good form' group by frame"""
            angles_df:pd.DataFrame = conn.sql(angles_query).df()

            index_to_name_map:dict = {v: k for k, v in self.metadata['ldmrks_of_interest'].items()} #to be removed
            
            # Define the list of columns to transform
            indices_col:list = [f"{name}_indices" for name in different_names]

            transformed_cols = {
                col: angles_df[col].apply(lambda idx_list: [index_to_name_map.get(k) for k in idx_list])
                for col in indices_col }

            angles_final = angles_df.assign(**transformed_cols)
        
            all_angles_query:str = f"""select frame, {','.join(cases)} from workout_analysis, unnest(angles_data) as t(element) where workout_id = {self.id_used} AND frame >= {self.frame_start}
            group by frame"""
            angles_desc = conn.sql(all_angles_query).df().describe()
            
        except Exception as e:
            print(f"Error extracting analysis data: {e}")
            return dict()
        extracted_data = {
            'total_repetitions': total_reps,
            'average_time_repetitions':avg_duration,
            'form_issues':form_issues,
            'frames_with_issues': frames_w_issues,
            'worst_reps':worst_reps,
            'frames_reps':frames_rep,
            'angles_data':angles_final,
            'angles_desc_stats':angles_desc
        }
        return extracted_data


    def extract_raw_landmarks(self)->dict[str,pd.DataFrame]:
        try:
            #get raw landmarks only for landmarks of interest
            index_to_name_map:dict = {v: k for k, v in self.metadata['ldmrks_of_interest'].items()} # to be removed
            ofinterest_keys = ''
            ofinterest_keys = ','.join([f""" round(landmark_{k}_x,2) as {v}_x, round(landmark_{k}_y,2) as {v}_y""" for k,v in index_to_name_map.items()])
            of_interest_query: str = f""" select frame, {ofinterest_keys} from raw_landmarks where frame >= {self.frame_start} and workout_id == {self.id_used}"""
            raw_of_int:pd.DataFrame = conn.sql(of_interest_query).df()
            of_int_desc:pd.DataFrame = raw_of_int.describe()
        except Exception as e:
            print(f"Error extracting analysis data: {e}")
            return dict()
        output = {
            'raw_of_interest':raw_of_int,
            'of_interest_desc':of_int_desc
        }
        return output
        

    def agent_pipeline(self)->Dict[str,Any]:
        """Main pipeline to extract data, generate feedback and format it"""

        id_frame = self.get_id_frame()
        if id_frame is None:
            raise ValueError('no data')
        self.id_used = id_frame['id']
        self.frame_start = id_frame['frame_start'] 

        self.metadata = self.extract_metadata()
        self.workout_analysis = self.extract_analysis()
        self.landmarks = self.extract_raw_landmarks()

        return {"a":'placeholder'}




if __name__ == "__main__":
    conn = duckdb.connect("data/workout_db.db")
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
