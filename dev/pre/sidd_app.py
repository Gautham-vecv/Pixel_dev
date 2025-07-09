from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional
import json
import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, SystemMessage
from langchain.tools import tool
import asyncio

app = FastAPI()

# Configure Gemini API
os.environ["GOOGLE_API_KEY"] = "your_google_api_key_here"  # Replace with your actual API key
llm = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)

# System prompt for information extraction
SYSTEM_PROMPT = """
You are an automotive service assistant that helps extract information from customer conversations to query a service database.

Your task is to extract the following information from user messages:
1. Job_card_number (string) - Service job card identifier
2. Chassis_number (string) - Vehicle chassis number
3. Customer_Voice (string) - Customer's complaint or concern
4. Label (string) - Service category or type
5. Parts_Replaced (string) - Parts that were replaced during service

IMPORTANT RULES:
- If ANY required information is missing, ask the user for the missing details
- Only when ALL 5 fields are collected, respond with: "INFORMATION_COMPLETE"
- Before asking for missing information, always acknowledge what you've already collected
- Be conversational and helpful
- If user provides partial information, extract what you can and ask for the rest

Current extracted information: {extracted_info}

Based on the conversation history and the user's latest message, either:
1. Extract available information and ask for missing details, OR
2. If all information is complete, respond with "INFORMATION_COMPLETE"

Remember: You must collect ALL 5 fields before saying "INFORMATION_COMPLETE"
"""

SQL_GENERATION_PROMPT = """
You are a SQL query generator for an automotive service database.

Based on the extracted information, generate a SQL query to retrieve relevant records.

Table Schema:
- Table name: service_records
- Columns: Job_card_number, Chassis_number, Customer_Voice, Label, Parts_Replaced

Extracted Information:
{extracted_info}

Generate a SQL SELECT query that would find records matching the provided criteria.
Use appropriate WHERE conditions and consider partial matches where relevant.
Return ONLY the SQL query, no explanations.
"""

# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: str
    extracted_info: Optional[Dict[str, Any]] = None

class ChatResponse(BaseModel):
    response: str
    extracted_info: Dict[str, Any]
    is_complete: bool
    sql_query: Optional[str] = None
    query_result: Optional[Dict[str, Any]] = None

# In-memory session storage (use Redis or database in production)
sessions = {}

@tool
def execute_sql_query(query: str) -> Dict[str, Any]:
    """
    Dummy tool to execute SQL query and return results.
    In production, this would connect to your actual database.
    """
    # Simulate database query execution
    dummy_result = {
        "status": "success",
        "rows_affected": 3,
        "data": [
            {
                "Job_card_number": "JC001",
                "Chassis_number": "CH123456",
                "Customer_Voice": "Engine making noise",
                "Label": "Engine Service",
                "Parts_Replaced": "Oil filter, Spark plugs"
            },
            {
                "Job_card_number": "JC002",
                "Chassis_number": "CH789012",
                "Customer_Voice": "Brake pedal feels soft",
                "Label": "Brake Service",
                "Parts_Replaced": "Brake pads, Brake fluid"
            }
        ]
    }
    return dummy_result

def extract_information_from_response(response_text: str, current_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract information from LLM response and update the current info dictionary.
    This is a simple implementation - you might want to use more sophisticated NLP.
    """
    # This is a basic implementation. In production, you might want to use
    # structured output or function calling to extract information more reliably
    
    # For now, we'll keep the existing information and let the LLM handle extraction
    # through conversation flow
    return current_info

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    try:
        # Get or create session
        session_id = request.session_id
        if session_id not in sessions:
            sessions[session_id] = {
                "extracted_info": {
                    "Job_card_number": "",
                    "Chassis_number": "",
                    "Customer_Voice": "",
                    "Label": "",
                    "Parts_Replaced": ""
                },
                "conversation_history": []
            }
        
        session = sessions[session_id]
        
        # Update extracted info if provided
        if request.extracted_info:
            session["extracted_info"].update(request.extracted_info)
        
        # Add user message to conversation history
        session["conversation_history"].append(f"User: {request.message}")
        
        # Prepare messages for LLM
        system_message = SystemMessage(content=SYSTEM_PROMPT.format(
            extracted_info=json.dumps(session["extracted_info"], indent=2)
        ))
        
        # Include recent conversation history
        conversation_context = "\n".join(session["conversation_history"][-10:])  # Last 10 messages
        human_message = HumanMessage(content=f"Conversation history:\n{conversation_context}\n\nLatest message: {request.message}")
        
        # Get LLM response
        response = llm.invoke([system_message, human_message])
        response_text = response.content
        
        # Add LLM response to conversation history
        session["conversation_history"].append(f"Assistant: {response_text}")
        
        # Check if information extraction is complete
        is_complete = "INFORMATION_COMPLETE" in response_text
        
        sql_query = None
        query_result = None
        
        if is_complete:
            # Generate SQL query
            sql_prompt = SQL_GENERATION_PROMPT.format(
                extracted_info=json.dumps(session["extracted_info"], indent=2)
            )
            sql_response = llm.invoke([SystemMessage(content=sql_prompt)])
            sql_query = sql_response.content.strip()
            
            # Execute the query using the tool
            try:
                query_result = execute_sql_query(sql_query)
                response_text = f"Great! I've collected all the information and found the following records:\n\n{json.dumps(query_result['data'], indent=2)}"
            except Exception as e:
                response_text = f"I've collected all the information, but there was an error executing the query: {str(e)}"
        
        # Extract any new information from the response
        session["extracted_info"] = extract_information_from_response(
            response_text, 
            session["extracted_info"]
        )
        
        return ChatResponse(
            response=response_text,
            extracted_info=session["extracted_info"],
            is_complete=is_complete,
            sql_query=sql_query,
            query_result=query_result
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get current session information"""
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return sessions[session_id]

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """Clear session data"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session cleared"}
    raise HTTPException(status_code=404, detail="Session not found")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)