from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from typing import List, Tuple
from pre.tool_prompts import query_writer_prompt, formater_prompt
from google.genai import types
from google import genai
from pydantic import BaseModel, Field
import mysql.connector


# Configuration constants
EMBEDDING_MODEL = "nomic-embed-text:latest"
PERSIST_DIR = "./parts_vectorstore"
COLLECTION = "parts_collection"
API_KEY = "AIzaSyB38bA4GgxitJT3KiSOCzrxS26g0dHcY7M"



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


def find_similar_parts(part_name: str, k: int = 5) -> List[Tuple[str, float]]:
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    """
    Find the top-k most similar parts to a given part name using a persisted Chroma vectorstore.

    Args:
        part_name (str): The name or description of the part to search for.
        k (int, optional): Number of top similar parts to return. Defaults to 5.

    Returns:
        List[Tuple[str, float]]: A list of tuples, each containing:
            - part_text (str): The stored part description.
            - similarity_score (float): The similarity score (lower is more similar).
    """
    # Load the persisted vectorstore
    vs = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embeddings,
        collection_name=COLLECTION
    )
    # Perform similarity search
    results = vs.similarity_search_with_score(part_name, k=k)
    # Extract content and score
    return [(doc.page_content, score) for doc, score in results]


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


def fetch_jc_data_retry(user_query: str, max_retries: int = 3):
    """
    Generate a SQL query via LLM, execute it against the DB, format & return the results.
    If execution fails with a syntax error, resend the faulty query+error back to the LLM
    for correction, and retry up to `max_retries` times.

    Args:
        user_query (str): The natural-language question to translate into SQL.
        max_retries (int): Number of times to attempt LLM-based query repair.

    Returns:
        str: Either the formatted LLM response, "No results found…" or an error message.
    """
    client = genai.Client(api_key=API_KEY)

    # 1) Initial SQL generation
    base_prompt = query_writer_prompt + user_query
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=base_prompt,
        config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=10000),
            response_mime_type="application/json",
            response_schema=SQLResponse,
        ),
    )
    parsed = response.parsed

    if not parsed.valid_request:
        return parsed.reason

    sql_query = parsed.query
    print("Response from LLM:", sql_query)

    # 2) Try executing, with retry-on-syntax-error
    for attempt in range(1, max_retries + 1):
        try:
            conn = mysql.connector.connect(
                host="localhost", user="root", password="Gautham@20010", database="vehicle_db"
            )
            cursor = conn.cursor()
            cursor.execute(sql_query)
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            break  # success, exit retry loop

        except mysql.connector.Error as err:
            print(f"error -{err}")
            # If we still have retries left, ask the LLM to fix the query
            if attempt < max_retries:
                fix_prompt = (
                    base_prompt
                    + "\n\n-- The following SQL failed with error:\n"
                    + sql_query
                    + f"\nError: {err}\n\nPlease rewrite the SQL so it runs without syntax errors."
                )
                correction = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=fix_prompt,
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(thinking_budget=0),
                        response_mime_type="application/json",
                        response_schema=SQLResponse,
                    ),
                )
                parsed = correction.parsed
                if not parsed.valid_request:
                    return parsed.reason
                sql_query = parsed.query  # retry with the new query
            else:
                return f"Failed after {max_retries} attempts; last error: {err}"

    # 3) No rows?
    if not results:
        return "No results found for your query."

    # 4) Format & return
    format_prompt = formater_prompt.format(user_query=user_query, results=results)
    final = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=format_prompt,
    )
    return final.text