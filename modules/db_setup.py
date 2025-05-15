import duckdb 

def setup_database(conn:duckdb.DuckDBPyConnection):
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
            left_side BOOLEAN not null
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
            ldmrks_of_interest MAP(VARCHAR,INTEGER) not null,
            primary key (workout_id, timestamp),
            FOREIGN KEY (workout_id) REFERENCES workout(ID))
            """)
    print("DuckDB setup complete.")
    #print(conn.sql(""" describe workout """))
    #print(conn.sql(""" describe workout_analysis """))
    
    

    