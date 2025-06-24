import duckdb 
from typing import Any
import pandas as pd
from ast import literal_eval
from modules.utils import extend_row

def connect_in_memory_db()-> duckdb.DuckDBPyConnection:
    """
    Connect to an in-memory DuckDB database.
    
    Returns:
        duckdb.DuckDBPyConnection: A connection object to the in-memory database.
    """
    conn = duckdb.connect(database=':memory:')
    #conn = duckdb.connect(database=':memory', read_only=False)
    setup_database(conn)
    return conn

def setup_database(conn:duckdb.DuckDBPyConnection)->None:
    """
    Setup the DuckDB database with the necessary tables and sequences.
    Args:
        conn (duckdb.DuckDBPyConnection): The connection to the DuckDB database.
    """
    print("Setting up DuckDB database...")
    #create a sequence for the workout ids.
    conn.sql("""CREATE SEQUENCE IF NOT EXISTS workout_id_seq INCREMENT BY 1; """)
    
    # in the workout table we values that do not change over time. i.e. name, start time, 
    # rep goal, strictness crit, left side, workout type, critness definition,
    conn.sql("""
        CREATE TABLE IF NOT EXISTS workout (
            ID INTEGER PRIMARY KEY default(nextval('workout_id_seq')),
            workout_name VARCHAR(128) NOT NULL,
            timestamp_start TIMESTAMP not null, 
            rep_goal INTEGER not null,
            strictness_crit VARCHAR(16) not null,
            strictness_definition DOUBLE not null,
            left_side BOOLEAN not null,
            ldmrks_of_interest MAP(INTEGER,VARCHAR) not null,
             )
            """)
    # Create a table for the workout analysis. 
    # This table will be used to store the analysis of each frame.
    # contains the following columns: frame, time, series number, rep count, down, form issues
    # angles data is a list of dictionaries with the following keys: name, value, joint indices
    # landmark of interest (i.e. indices of the points used for the workout)
    conn.sql("""
        CREATE TABLE IF NOT EXISTS workout_analysis (
            workout_id INTEGER not null,
            frame INTEGER not null,
            timestamp TIMESTAMP not null,
            series_number INTEGER,
            rep_count INTEGER not null,
            down BOOLEAN not null,
            form_issues VARCHAR not null,
            angles_data STRUCT(name VARCHAR, value DOUBLE, joint_indices INT[])[] not null,
            primary key (workout_id, timestamp),
            FOREIGN KEY (workout_id) REFERENCES workout(ID))
            """)
    print("DuckDB setup complete.")
    #print(conn.sql(""" describe workout """))
    #print(conn.sql(""" describe workout_analysis """))

def write_workout_metadata(conn:duckdb.DuckDBPyConnection, metadata:dict)->int:
    """
    Write workout metadata to the DuckDB database.
    Args:
        conn (duckdb.DuckDBPyConnection): The connection to the DuckDB database.
        metadata (dict): A dictionary containing workout metadata.
        The dictionary should contain the same keys as the columns in the workout table.
    Returns:
        int: The id of the newly inserted workout entry, or 0 if the insertion failed.
    """

    try:
        conn.sql("""
            INSERT INTO workout (workout_name, timestamp_start,rep_goal,
            strictness_crit,strictness_definition, left_side,ldmrks_of_interest)
            VALUES (?,?,?,?,?,?,MAP(?,?)) """,
            params=[metadata["workout_name"],
                    metadata["timestamp_start"],
                    metadata['rep_goal'],
                    metadata['strictness_crit'],
                    metadata['strictness_definition'],
                    metadata['left_side'],
                    metadata['ldmrks_values'],
                    metadata['ldmrks_keys']
                    ])
        # Get the last inserted id
        last_id = conn.sql("SELECT max(id) from workout").fetchone()
        if last_id is not None:
            return last_id[0]
        else:
            print("No workout entries found in the database.")
            return 0
    except Exception as e:
        print(f"Error inserting new workout: {e}")
        return 0
    
    
def write_workout_analysis(conn:duckdb.DuckDBPyConnection, analysis_data:list[dict[str,Any]],workout_id:int)->None:
    """
    Write workout analysis data to the DuckDB database.
    Args:
        conn (duckdb.DuckDBPyConnection): The connection to the DuckDB database.
        analysis_data (list[dict[str,Any]]): A dictionary containing workout analysis data. The list should contain a dictionary for each frame.
        Each dictionary should contain the following keys: frame, timestamp, rep_count, down, form_issues, angles_data, ldmrks_keys,
        ldmrks_values.
    workout_id (int): The id of the workout to which the analysis data belongs.
        
    """
    data_to_insert = pd.DataFrame(analysis_data)
    data_to_insert['workout_id'] = workout_id
    
    try:
        conn.sql("INSERT INTO workout_analysis BY NAME SELECT * FROM data_to_insert")
    except Exception as e:
        print(f"Error inserting new workout: {e}")
        return
    
def write_raw_landmarks(conn:duckdb.DuckDBPyConnection, raw_landmarks:list[dict[str,Any]], workout_id:int)->None:
    """
    Write raw landmarks data to the DuckDB database.
    Args:
        conn (duckdb.DuckDBPyConnection): The connection to the DuckDB database.
        raw_landmarks (pd.DataFrame): A DataFrame containing raw landmarks data.
        workout_id (int): The id of the workout to which the raw landmarks data belongs.
    """
    columns =[]
    for i in range(33):
        columns.extend([f'landmark_{i}_x', f'landmark_{i}_y'])
    raw_landmarks_df = pd.DataFrame(raw_landmarks)
    raw_landmarks_df['workout_id'] = workout_id
    landmarks= raw_landmarks_df['landmarks'].apply(lambda x: extend_row(x))
    landmarks_df = pd.DataFrame(landmarks.to_list(), columns=columns)
    landmarks_processed = pd.concat([raw_landmarks_df, landmarks_df], axis=1)
    landmarks_processed.drop(columns=['landmarks'], inplace=True)
    try:
        conn.sql("CREATE TABLE IF NOT EXISTS raw_landmarks AS SELECT * FROM landmarks_processed")
    except Exception as e:
        print(f"Error inserting raw landmarks: {e}")
        return
    
def save_data_to_db(conn:duckdb.DuckDBPyConnection, metadata:dict, analysis_data:list[dict[str,Any]], raw_landmarks:list[dict[str,Any]])->bool:
    """
    Save workout metadata, analysis data, and raw landmarks to the DuckDB database.
    Args:
        conn (duckdb.DuckDBPyConnection): The connection to the DuckDB database.
        metadata (dict): A dictionary containing workout metadata.
        analysis_data (list[dict[str,Any]]): A list of dictionaries containing workout analysis data.
        raw_landmarks (list[dict[str,Any]]): A list of dictionaries containing raw landmarks data.
    Returns:
        int: The id of the newly inserted workout entry, or 0 if the insertion failed.
    """
    print("Saving data to DuckDB...")
    workout_id = write_workout_metadata(conn, metadata)
    print(f"saved meatdata for workout id {workout_id}")
    if workout_id == 0:
        print("Failed to insert workout metadata. Aborting data save.")
        return False
    write_workout_analysis(conn, analysis_data, workout_id)
    print(f"saved analysis data for workout id {workout_id}")
    write_raw_landmarks(conn, raw_landmarks, workout_id)
    print(f"saved raw landmarks for workout id {workout_id}")
    print(f"Data saved successfully for workout ID: {workout_id}")
    return True

def close_db_connection(conn:duckdb.DuckDBPyConnection)->None:
    """
    Close the DuckDB database connection.
    Args:
        conn (duckdb.DuckDBPyConnection): The connection to the DuckDB database.
    """
    if conn is not None:
        conn.close()
        print("Database connection closed.")
    else:
        print("No database connection to close.")
    