


API_KEY = "AIzaSyB38bA4GgxitJT3KiSOCzrxS26g0dHcY7M"
from google.genai import types
from pydantic import BaseModel, Field
from google import genai
from pydantic import BaseModel
import mysql.connector
from google.genai import types
from pydantic import BaseModel, Field
from google import genai

from schemas.tools_schema import SQLResponse
from prompts.tool_prompts_v1 import query_writer_prompt,formater_prompt



class BoolResponse(BaseModel):
    """
    A Pydantic model that represents a bare boolean response.
    Use this to parse or serialize a plain True/False JSON value.
    """
    valid: bool

def query_validator(user_query: str):
    
    prompt = f"""
    You are QueryValidatorBot.  
    When given a user’s SQL-related question on vehicle service data of an automotive company, respond with exactly **True** if the question is valid, or **False** if it is not.  

    VALID if the user asks about:  
    • Part information for a specific model   
    • Counts or aggregates (COUNT, GROUP BY)  
    • Any of these columns: action_taken, observation, customer_voice  


    INVALID if the user asks about:  
    • Customer name or any personal identifiers  
    • Irrelevant topics (weather, time, general knowledge, etc.)  
    

    Here is the User's question:
    {user_query}
    only Return `True` or `False`.  """

    client = genai.Client(api_key=API_KEY)

    # Generate SQL via the LLM
    response = client.models.generate_content(
        model="gemini-2.5-flash-lite-preview-06-17",
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=BoolResponse,
        ),
    )
    
    if response.parsed:
        if isinstance(response.parsed.valid, bool):
            return response.parsed.valid
        else:
            raise ValueError("Response is not a boolean value.")




def fetch_jc_data(user_query: str):
    

    # Initialize the AI client
    client = genai.Client(api_key=API_KEY)

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

    print("Response from LLM:", response.text)
    # Parse the LLM output
    parsed = response.parsed

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
    
        if results:
            print(f"Results found: {results}")
            # Format the results using the formatter prompt
            prompt_2 = formater_prompt.format(user_query=user_query,results=results)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt_2)
            
            return response.text
                    

        else:
            return "No results found for your query."
  
    
    else:    # Return the reason for an invalid or unsafe query
        return parsed.reason
