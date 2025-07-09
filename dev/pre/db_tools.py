import mysql.connector
from google.genai import types
from pydantic import BaseModel, Field
from google import genai

# Define or import your SQLResponse schema and prompt prefix
# from your application context
# from your_app.schemas import SQLResponse
# from your_app.prompts import query_writer_prompt

query_writer_prompt = """
You are SQLBot, your role is to generate error-free SQL queries for a single table named `jc_table`. The table schema is as follows:


TABLE SCHEMA:
job_card_number (bigint): Unique service record identifier
vehicle_chassis_number (text): Vehicle VIN/chassis number
vehiclemode (text): Vehicle model - ONLY use: 'PRO 8035T'
emission (text): Emission standard
engine (text): Engine type - ONLY use: 'VEDX'
fuel (text): Fuel type
enginefuel (text): Engine-fuel combination
obd (bigint): OBD port number
fert_description (text): Vehicle variant description
customer_number (bigint): Customer identifier
dealername (text): Service dealer name
plant (text): Manufacturing plant code
failure_date (datetime): Issue occurrence date (format: YYYY-MM-DD HH:MM:SS)
jobs_description (text): Service job description
customer_voice (text): Original customer complaint
action_taken (text): Service action performed
observation (text): Technical observations
causal_code (text): Technical fault code
casual_description (text): Fault description
item_type (text): Part category ('SPARES', 'LABOR VALUE')
item_material (text): Part number/code
item_matrial_desription (text): Part description
region_group (text): Geographic region
culprit_code (text): Component fault code
culprit_description (text): Component fault description
clean_customer_voice (text): Cleaned customer complaint
issue_area (text): Issue category - ONLY use: 'axles', 'suspension', 'vehicle_electricals'
llm_primary_issue (text): Main issue identified by AI
llm_other_issue (text): Additional issues identified
llm_key_observation (text): Key observations from AI analysis
llm_root_cause (text): Root cause analysis
llm_affected_systems (text): Vehicle systems affected
llm_action_status (tinyint(1)): Action taken flag (1=TRUE, 0=FALSE)
llm_action_type (text): Type of service action
llm_work_done (text): Summary of repair work
llm_severity_level (bigint): Issue severity (1-5 scale)
llm_service_summary (text): AI-generated service summary
llm_additional_info (double): Additional information
llm_repair_details (double): Repair details
total_dtc_occurrences (bigint): Total DTC count
unique_dtc_codes (text): Comma-separated unique DTC codes
num_unique_dtcs (bigint): Number of unique DTCs
most_frequent_dtc (text): Most common DTC code
most_frequent_dtc_count (bigint): Count of most frequent DTC
most_frequent_dtc_aggregate (text): System category of most frequent DTC
last_occurred_dtc (text): Most recent DTC with timestamp
top_3_frequent_dtcs (text): Top 3 DTCs with frequencies
top_3_frequent_dtcs_with_aggregate (text): Top 3 DTCs with system categories
major_dtc_aggregate (text): Primary system affected by DTCs
major_dtc_aggregate_count (bigint): Count of DTCs in major system
aggregate_distribution (text): DTC distribution across systems

STRICT VALUE CONSTRAINTS:
vehiclemode: Must be exactly 'PRO 8035T' - NO OTHER VALUES ALLOWED
issue: Must be exactly one of: 'axles', 'suspension', 'vehicle_electricals' - NO OTHER VALUES ALLOWED

if the user input is not in the strict value constraints, return false and provide the reason 
engine: Must be exactly 'VEDX' - NO OTHER VALUES ALLOWED

QUERY GENERATION RULES:

- ALWAYS use exact string matching with single quotes for text fields
- Text fields are case-sensitive - use exact values as specified
- Date format: Use 'YYYY-MM-DD' format for failure_date comparisons
- Multiple rows can exist per job_card_number (different parts/services)
- NEVER suggest values outside the allowed lists for vehiclemode, issue_area, or engine
- If user requests invalid values, inform them of the correct available options
- if the user query has spelling mistakes, correct them and provide the correct query

Output format:
Return a JSON object with three keys:
	1.	valid_request (bool) – true if the user’s request can be translated to a valid SQL query, otherwise false.
	2.	query (string) – the generated SQL query if valid_request is true, or an empty string if false.
	3.	reason (string) – if valid_request is false, a brief explanation why the request is invalid; otherwise an empty string.


example 1 :

Input:
user_input : “Get all records where vehiclemode is PRO 8035T and issue_area is axles.”

output:
{
  "valid_request": true,
  "query": "SELECT *\n  FROM `job_cards`\n WHERE `vehiclemode` = 'PRO 8035T'\n   AND `issue_area` = 'axles';",
  "reason": ""
}

"""


class SQLResponse(BaseModel):
    valid_request: bool = Field(
        ...,
        description="True if the user's request was successfully translated into a valid SQL query; False otherwise."
    )
    query: str = Field(
        ...,
        description="The generated SQL query when valid_request is True, or an empty string otherwise."
    )
    reason: str = Field(
        ...,
        description="If valid_request is False, a brief explanation of why the request is invalid; otherwise an empty string."
    )
# Establish a persistent database connection
conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Gautham@20010",
    database="vehicle_db"
)


def fetch_jc_data(user_query: str):
    """
    Translates a natural language query into SQL using an LLM,
    executes it against the MySQL database, and returns the results.

    :param user_query: The user's natural language query.
    :return: A list of tuples with query results, or an error message string.
    """
    # Initialize the AI client
    client = genai.Client(api_key="AIzaSyB38bA4GgxitJT3KiSOCzrxS26g0dHcY7M")

    # Generate SQL via the LLM
    prompt = query_writer_prompt + user_query
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=0),  # disable extra thinking tokens
            response_mime_type="application/json",
            response_schema=SQLResponse,
        ),
    )

    # Parse the LLM output
    parsed = response.parsed
    if parsed.valid_request:
        cursor = conn.cursor()
        cursor.execute(parsed.query)
        results = cursor.fetchall()
        cursor.close()
        return results
    else:
        # Return the reason for an invalid or unsafe query
        return parsed.reason
