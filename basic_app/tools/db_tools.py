import mysql.connector
from google.genai import types
from pydantic import BaseModel, Field
from google import genai

from schemas.tools_schema import SQLResponse
from prompts.tool_prompts_v1 import query_writer_prompt

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

    print(response.parsed.query)
    if parsed.valid_request:
        # Establish a persistent database connection
        conn = mysql.connector.connect(
            host="localhost",
            user="root",
            password="Gautham@20010",
            database="vehicle_db")
        cursor = conn.cursor()
        cursor.execute(parsed.query)
        results = cursor.fetchall()
        cursor.close()
        return results
    else:
        # Return the reason for an invalid or unsafe query
        return parsed.reason
