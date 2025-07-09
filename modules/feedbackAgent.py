import duckdb
import json
import os
import pandas as pd
from datetime import datetime
from typing import Dict, Any
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain_core.prompts import ChatPromptTemplate


class FeedbackAgent:
    def __init__(
        self, db_conn: duckdb.DuckDBPyConnection, model: str = "gemini-2.0-flash"
    ):

        self.model: str = model
        self.db_conn: duckdb.DuckDBPyConnection = db_conn

        # dataset
        self.id_used: int = 0
        self.frame_start: int = 0
        self.metadata: pd.Series = pd.Series()
        self.workout_analysis: dict = {}
        self.landmarks: dict = {}
        self.previous_rolling_summary:str = "No previous sets in this session."

        # Initialize the LLM model
        load_dotenv()
        google_key = os.environ.get("GOOGLE_API_KEY")
        self.llm = ChatGoogleGenerativeAI(model=self.model, google_api_key=google_key)

    def update_rolling_summary(self,summary:str)->None:
        self.previous_rolling_summary = summary

    def get_id_frame(self) -> dict[str, int] | None:
        try:
            query_id: str = "Select max(id) from workout"
            res_id: tuple | None = self.db_conn.sql(query_id).fetchone()
            if res_id is None:
                raise ValueError("No id found in database.")
            workout_id: int = res_id[0]
            # get the first good form and backtrack 10 frames as the start frame (the idea is to avoid analysing the frames when user is setting up)
            strat_frame_query: str = (
                f" SELECT  frame from workout_analysis  where workout_id ={workout_id} and SUBSTRING(form_issues,1,4)= 'Good' order by frame"
            )
            res_start_frame: tuple | None = self.db_conn.sql(
                strat_frame_query
            ).fetchone()
            if res_start_frame is None:
                raise ValueError("No analysis data found for the last workout.")
            frame_start: int = res_start_frame[0] - 10
        except Exception as e:
            print(f"Error retrieving data: {e}")
            return None
        return {"id": workout_id, "frame_start": frame_start}

    def extract_metadata(self) -> pd.Series:
        try:
            metadata: pd.DataFrame = self.db_conn.sql(
                f"SELECT * FROM workout where id = {self.id_used}"
            ).df()
            if metadata is None:
                raise ValueError("No metadata found for the last workout.")
            end_time_query = f"SELECT max(timestamp) FROM workout_analysis where workout_id = {self.id_used}"
            end_time: tuple | None = self.db_conn.sql(end_time_query).fetchone()
            if end_time is None:
                raise ValueError("No end time found for the last workout.")
            end_time = end_time[0]
            metadata["end_time"] = end_time
            metadata["duration"] = metadata.apply(
                lambda x: round(
                    (x["end_time"] - x["timestamp_start"]).total_seconds(), 2
                ),
                axis=1,
            )
        except Exception as e:
            print(f"Error retrieving metadata: {e}")
            return pd.Series()

        return metadata.iloc[0]

    def extract_analysis(self) -> dict[str, Any]:
        try:
            # get total number of reps
            tot_reps_query: str = (
                f"select max(rep_count) from workout_analysis where workout_id = {self.id_used} and frame >= {self.frame_start}"
            )
            total_reps_res: tuple | None = self.db_conn.sql(tot_reps_query).fetchone()
            if total_reps_res is None:
                raise ValueError("No analysis data found for current workout")
            total_reps: int = total_reps_res[0]

            # duration of each repetitons
            frames_rep_query: str = f"""select min(frame) as start_frame,max(frame) as end_frame,rep_count+1 as repetitions, round(epoch(max(timestamp) - min(timestamp)),1) as duration ,
                        from workout_analysis where workout_id = {self.id_used} and frame>= {self.frame_start} and repetitions <= {self.metadata['rep_goal']} group by rep_count"""
            frames_rep: pd.DataFrame = self.db_conn.sql(frames_rep_query).df()

            # average time rep
            avg_duration: float = round(frames_rep["duration"].mean(), 2)

            # form issues
            form_issues_query: str = (
                f"""SELECT form_issues, count(*) as count FROM workout_analysis WHERE workout_id = {self.id_used} AND frame >= {self.frame_start} GROUP BY form_issues"""
            )
            form_issues: list = self.db_conn.sql(form_issues_query).fetchall()

            frames_issues_quesry: str = (
                f"""SELECT  form_issues, LIST(frame) FROM workout_analysis WHERE workout_id = {self.id_used} AND frame >= {self.frame_start} and form_issues not like 'Good form' group by form_issues  """
            )
            frames_w_issues: list = self.db_conn.sql(frames_issues_quesry).fetchall()

            worst_reps_query: str = f"""SELECT rep_count+1 as repetitions, count(form_issues) as count
            FROM workout_analysis 
            WHERE workout_id = {self.id_used} AND frame >= {self.frame_start} and 
            form_issues not like 'Good form'
            GROUP BY repetitions
            ORDER BY count DESC
            LIMIT 3"""
            worst_reps: list = self.db_conn.sql(worst_reps_query).fetchall()

            # exctract angles data
            dif_angles_query: str = (
                """ select list(distinct(angle_element.name)) as angle_names FROM workout_analysis, UNNEST(angles_data) as t(angle_element)"""
            )
            diff_names_ang_res: tuple | None = self.db_conn.sql(
                dif_angles_query
            ).fetchone()
            if diff_names_ang_res is None:
                raise ValueError("Error exctracting names of angles")
            different_names: list = diff_names_ang_res[0]

            cases: list[str] = [
                f"""MAX(case WHEN element.name ='{name}' THEN round(element.value,2) end) as {name}_angle,
            MAX(case WHEN element.name ='{name}' THEN element.joint_indices end) as {name}_indices
            """
                for name in different_names
            ]
            angles_query: str = f"""select frame, {','.join(cases)} from workout_analysis, unnest(angles_data) as t(element) where workout_id = {self.id_used} AND frame >= {self.frame_start}
            and form_issues not like 'Good form' group by frame"""
            angles_df: pd.DataFrame = self.db_conn.sql(angles_query).df()

            index_to_name_map: dict = {
                v: k for k, v in self.metadata["ldmrks_of_interest"].items()
            }  # to be removed

            # Define the list of columns to transform
            indices_col: list = [f"{name}_indices" for name in different_names]

            transformed_cols = {
                col: angles_df[col].apply(
                    lambda idx_list: [index_to_name_map.get(k) for k in idx_list]
                )
                for col in indices_col
            }

            angles_final = angles_df.assign(**transformed_cols)

            all_angles_query: str = f"""select frame, {','.join(cases)} from workout_analysis, unnest(angles_data) as t(element) where workout_id = {self.id_used} AND frame >= {self.frame_start}
            group by frame"""
            angles_desc = self.db_conn.sql(all_angles_query).df().describe()

        except Exception as e:
            print(f"Error extracting analysis data: {e}")
            return {}
        extracted_data = {
            "total_repetitions": total_reps,
            "average_time_repetitions": avg_duration,
            "form_issues": form_issues,
            "frames_with_issues": frames_w_issues,
            "worst_reps": worst_reps,
            "frames_reps": frames_rep,
            "angles_data": angles_final,
            "angles_desc_stats": angles_desc,
        }
        return extracted_data

    def extract_raw_landmarks(self) -> dict[str, pd.DataFrame]:
        try:
            # get raw landmarks only for landmarks of interest
            index_to_name_map: dict = {
                v: k for k, v in self.metadata["ldmrks_of_interest"].items()
            }  # to be removed
            ofinterest_keys = ""
            ofinterest_keys = ",".join(
                [
                    f""" round(landmark_{k}_x,2) as {v}_x, round(landmark_{k}_y,2) as {v}_y"""
                    for k, v in index_to_name_map.items()
                ]
            )
            of_interest_query: str = (
                f""" select frame, {ofinterest_keys} from raw_landmarks where frame >= {self.frame_start} and workout_id == {self.id_used}"""
            )
            raw_of_int: pd.DataFrame = self.db_conn.sql(of_interest_query).df()
            of_int_desc: pd.DataFrame = raw_of_int.describe()
        except Exception as e:
            print(f"Error extracting analysis data: {e}")
            return {}
        output = {"raw_of_interest": raw_of_int, "of_interest_desc": of_int_desc}
        return output

    def create_prompt(self):

        encouragement:ResponseSchema = ResponseSchema(
                name="encouragement",
                description="A brief, encouraging opening statement congratulating the user on their effort.",
            )   
        positive_point:ResponseSchema = ResponseSchema(
                name="positive_point",
                description="A positive one sentence note highlighting something positif in the workout. ",
            )
        main_feedback:ResponseSchema = ResponseSchema(
                name="main_feedback",
                description="The primary piece of feedback, focusing on the most critical form issue. Explain the issue, why it's important, and how to fix it.",
            )
        second_feedback:ResponseSchema = ResponseSchema(
                name="secondary_feedback",
                description="Feedback on any other significant form issues or comments on pacing and consistency.",
            )
        summ:ResponseSchema = ResponseSchema(
                name="summary",
                description="A concluding summary and a key takeaway for the user to focus on in their next session.",
            )
        rolling_summary:ResponseSchema = ResponseSchema(
                name='Rolling_Summary',
                description="a summary of the key metadata (number of reps, time per rep, total time, number of series so far,...) events, form issues, and trends observed across all sets completed so far in this session.."
            )
        response_schemas = [encouragement,positive_point,main_feedback,second_feedback,summ,rolling_summary]

        output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
        format_instructions = output_parser.get_format_instructions()

        system_prompt = """
        You are an expert, data-driven fitness coach. Your tone should be encouraging, clear, and direct. Make sure anyone can understand you, avoid using technical terms.
        You are analyzing a user's workout based on the data provided in the user message.
        The user's goal was to perform {rep_goal} {workout_name}. 
        This is the user's set number {series_number} so far for this workout session. 
        The strictness level for form analysis was set to '{strictness_crit}', with an allowed deviation of {strictness_definition} degrees.

        To ensure a consistent and parsable output, please structure your response as a JSON object with the following format:
        {format_instructions}
        """

        user_prompt = """
        Here is the data from the user's workout session:

        [PREVIOUS SETS SUMMARY]
        {rolling_summary}

        [CURRENT SET DATA | Set Number: {series_number}]
        - Total Repetitions Performed: {total_repetitions}
        - Total Workout Duration: {duration} seconds
        - Average Time Per Repetition: {average_time_repetitions} seconds
    

        [FORM ANALYSIS]
        - Form Issues Encountered: {form_issues}
        - Repetitions with the Most Form Errors: {worst_reps}

        [ANGLE ANALYSIS]
        - Angle Statistics:
        {angle_stats}

        Please provide your feedback based on this data.
        """

        prompt = ChatPromptTemplate.from_messages(
            [
                ("system", system_prompt),
                ("human", user_prompt),
            ]
        )

        return prompt, output_parser, format_instructions

    def format_feedback(self, feedback: dict) -> str:
        now = datetime.now()
        formatted = f"""
        <div class=\"feedback-details\">
            <p>💪 {feedback["encouragement"]}</p>
            <p>🔥 {feedback['positive_point']}</p>
            <p>🏋️ {feedback["summary"]} </p>
            <p>🔎 {feedback["main_feedback"]} {feedback["secondary_feedback"]}</p>
            <small> Disclaimer: Analysis generated on {now}. This analysis was generated using artificial intelligence and can contain errors.</small>
            </div>
            <hr> 
            """
        return formatted

    def agent_pipeline(self) -> Dict[str, Any]:
        """Main pipeline to extract data, generate feedback and format it"""

        id_frame = self.get_id_frame()
        if id_frame is None:
            raise ValueError("no data")
        self.id_used = id_frame["id"]
        self.frame_start = id_frame["frame_start"]

        self.metadata = self.extract_metadata()
        self.workout_analysis = self.extract_analysis()


        prompt_template, output_parser, format_instructions = self.create_prompt()
        print(prompt_template)
        chain = prompt_template | self.llm | output_parser

        # Format the extracted data for the prompt
        form_issues_summary = ", ".join(
            [
                f"{issue[0]} ({issue[1]} times)"
                for issue in self.workout_analysis["form_issues"]
                if issue[0] != "Good form"
            ]
        )
        worst_reps_summary = ", ".join(
            [
                f"Rep {rep[0]} ({rep[1]} issues)"
                for rep in self.workout_analysis["worst_reps"]
            ]
        )
        print(f"rolling summary to be used: {self.previous_rolling_summary}")
        # Invoke the chain with the necessary data
        feedback = chain.invoke(
            {
                "rep_goal": self.metadata.get("rep_goal", "N/A"),
                "workout_name": self.metadata.get("workout_name", "N/A"),
                "strictness_crit": self.metadata.get("strictness_crit", "N/A"),
                "strictness_definition": self.metadata.get(
                    "strictness_definition", "N/A"
                ),
                "series_number":self.metadata.get("series_number",'N/A"'),
                "total_repetitions": self.workout_analysis.get("total_repetitions", 0),
                "duration": self.metadata.get("duration", 0),
                "average_time_repetitions": self.workout_analysis.get(
                    "average_time_repetitions", 0
                ),
                "form_issues": form_issues_summary,
                "worst_reps": worst_reps_summary,
                "angle_stats": self.workout_analysis.get(
                    "angles_desc_stats", pd.DataFrame()
                ).to_string(),
                "format_instructions": format_instructions,
                "rolling_summary":self.previous_rolling_summary
            }
        )
        formatted_feedback = self.format_feedback(feedback=feedback)
        feedback["formatted_feedback"] = formatted_feedback
        self.update_rolling_summary(summary = feedback["Rolling_Summary"])
        print(f"new rolling summary: {self.previous_rolling_summary}")
        return feedback


if __name__ == "__main__":
    # Load environment variables
    load_dotenv()

    # Establish database connection
    conn = duckdb.connect("data/db_test.db")

    # Initialize the FeedbackAgent
    feedback_agent = FeedbackAgent(conn)
    i = 0 
   
    try:
         while i<2:
            # Generate feedback
            fb = feedback_agent.agent_pipeline()
            

            # Pretty print the structured feedback
            if fb:
                print(json.dumps(fb, indent=4))

            else:
                print("No feedback was generated.")
            i+=1

    except Exception as e:
        print(f"Error generating feedback: {e}")

    finally:
        # Close the database connection
        if conn is not None:
            conn.close()
