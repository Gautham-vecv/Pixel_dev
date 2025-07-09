from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
from datetime import datetime
from utils.helper import query_validator,fetch_jc_data

app = FastAPI(title="Vehicle Diagnostic Chat API", version="1.0.0")

# Add CORS middleware to allow Streamlit to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your Streamlit URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Vehicle models list
VEHICLE_MODELS = [
    'PRO 2059XP', 'PRO 6016 cwc', 'PRO 8035T', 'PRO 2114XP',
    'PRO 2095XP Truck', 'PRO 6028T', 'PRO 6028', 'PRO 6035',
    'PRO 2075', 'PRO 3015 Truck', 'PRO 2075 CNG', 'PRO 2090 Bus',
    'PRO 2049 Truck', 'PRO 3019S', 'PRO 2114XP CNG', 'PRO 2110',
    'PRO 3010 cwc', 'PRO 3019', 'PRO 2110XP', 'PRO 6025T', 'PRO 6035T',
    'PRO 2095XP CNG', 'PRO 3016 CWC', 'PRO 6055-1', 'PRO 2095',
    'PRO 3018', 'PRO 6019T', 'PRO 3015XP', 'PRO 6055', '2050 Bus',
    'PRO 2080', 'PRO 2055T', 'PRO 8028T', 'PRO 6048',
    'PRO 3019J', 'PRO 3010 Bus', 'PRO 2110XPT', 'PRO 6025',
    'PRO 3019M', 'PRO 2065 Bus', 'PRO 3011 Bus', 'PRO 2118',
    'PRO 2112 cwc', 'PRO 6019 Cwc', 'PRO 6049', 'PRO 8031H',
    'PRO 2075 cwc', 'PRO 2090 cwc', 'PRO 2055', 'PRO 5016 Truck',
    '9M EV Bus', 'PRO 6054', 'PRO 2059', 'PRO 6041',
    'PRO 6028 S CWC 32FT', 'PRO 3009 Bus', 'PRO 2075 Bus', 'PRO 6031',
    'PRO 2080T', 'PRO 6037', 'PRO 2059XP CNG', 'PRO 6040',
    'PRO 2049 CNG', 'PRO 2095T', 'PRO 6042', 'PRO 3018 CNG',
    'PRO 2110XP CNG', 'PRO 1095XP Truck', 'PRO 8055',
    'PRO 8049 6X4', 'PRO 2050 cwc', 'PRO 2070 bus', 'PRO 3009 CWC',
    'PRO 3015 Diesel 32FT', 'PRO 5031 Truck', 'PRO 3016', 'PRO 1049',
    'PRO 2090', 'PRO 2059 CNG', 'PRO 2109 CNG', 'PRO 6046',
    'PRO 2065 cwc', 'PRO 3012 Truck', 'PRO 8031T', 'PRO 8025',
    'PRO 6042HT', '10.90 Bus', 'PRO 2050', 'PRO 2070 cwc', 'PRO 6019',
    'PRO 2119', 'PRO 8049 6X2', 'PRO 3014 Truck', 'PRO 3015 CNG 32FT',
    'PRO 3014 CWC', 'PRO 2112 Bus', 'PRO 6048T', 'PRO 1059 Truck',
    'PRO 3012 BUS', 'PRO 1080XPT Truck', 'Ambulance Built up',
    'PRO 5035 Truck', 'PRO 2110 CNG', 'PRO 2055 EV', 'PRO 3011 cwc',
    '10.75 Bus', 'PRO 5025 Truck', 'PRO 5019', 'PRO 2050 CNG',
    'Ambulance Chassis', 'PRO 5040 Truck', 'PRO 6016 Bus',
    'PRO 1114XP Truck', 'PRO 2116', 'PRO 5016T', 'PRO 3013 Truck',
    '10.80 Truck', '10.59 SL-XP', 'PRO 2118 CNG'
]

# Issue categories
ISSUE_CATEGORIES = [
    "accessory_belt_drive_system",
    "accidental",
    "air_intake",
    "axles",
    "brake",
    "cabin_and_accessories",
    "cargo_body",
    "chassis_frame",
    "clutch",
    "cooling_system",
    "differential_issues",
    "eats",
    "engine_issues",
    "ev_motor",
    "fuel_system",
    "gearbox_and_transmission",
    "general_service_and_pms",
    "hvac",
    "miscellaneous",
    "pdi_and_campaign",
    "pickup_issues",
    "poor_mileage",
    "pto_hydralics",
    "sensors",
    "steering",
    "suspension",
    "turbo_and_intercooler",
    "tyre",
    "vehicle_electricals",
    "vehicle_electronics"
]

# Valid users for authentication
VALID_USERS = {
    "admin": "password123",
    "user1": "demo123",
    "test": "test123"
}

# Pydantic models for request/response
class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    success: bool
    message: str

class ChatRequest(BaseModel):
    action: str  # "initial", "model_selected", "submit_query", "followup_query", "reset"
    selected_model: Optional[str] = None
    user_query: Optional[str] = None
    data: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    stage: str
    options: Optional[List[str]] = None
    timestamp: str

class FilterRequest(BaseModel):
    query: str
    filter_type: str  # "models" or "issues"

class FilterResponse(BaseModel):
    results: List[str]

class ValidateRequest(BaseModel):
    user_query: str

class ValidateResponse(BaseModel):
    valid: bool

class FetchResponse(BaseModel):
    result: str


@app.get("/")
async def root():
    return {"message": "Vehicle Diagnostic Chat API is running"}

@app.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Authenticate user"""
    if request.username in VALID_USERS and VALID_USERS[request.username] == request.password:
        return LoginResponse(success=True, message="Login successful")
    else:
        return LoginResponse(success=False, message="Invalid username or password")

@app.get("/models")
async def get_models():
    """Get all vehicle models"""
    return {"models": VEHICLE_MODELS}

@app.get("/issues")
async def get_issues():
    """Get all issue categories"""
    return {"issues": ISSUE_CATEGORIES}

@app.post("/filter", response_model=FilterResponse)
async def filter_data(request: FilterRequest):
    """Filter models or issues based on query"""
    if request.filter_type == "models":
        if not request.query:
            filtered = VEHICLE_MODELS[:10]
        else:
            filtered = [model for model in VEHICLE_MODELS if request.query.upper() in model.upper()][:10]
    elif request.filter_type == "issues":
        if not request.query:
            filtered = []
        else:
            formatted_categories = [cat.replace('_', ' ') for cat in ISSUE_CATEGORIES]
            filtered = []
            for i, category in enumerate(formatted_categories):
                if request.query.lower() in category.lower():
                    filtered.append(ISSUE_CATEGORIES[i])
            filtered = filtered[:5]
    else:
        filtered = []
    
    return FilterResponse(results=filtered)

@app.post("/validate_query", response_model=ValidateResponse)
async def validate_query_endpoint(request: ValidateRequest):
    """
    Validate the user's SQL-related question.
    Returns {"valid": True} or {"valid": False}.
    """
    if not request.user_query.strip():
        raise HTTPException(status_code=400, detail="`user_query` must not be empty")
    is_valid = query_validator(request.user_query)
    return ValidateResponse(valid=is_valid)

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """Handle chat interactions"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if request.action == "initial":
        return ChatResponse(
            message="Hi! I'm Pixel, your Job Card assistant. 🚗✨\n\nI can help you find information from our vehicle job card database. Whether you're looking for specific model data, maintenance records, parts information, or troubleshooting help - I'm here to assist you!",
            stage="model_selection",
            options=VEHICLE_MODELS,
            timestamp=timestamp
        )
    
    elif request.action == "model_selected":

        if request.selected_model:
            return ChatResponse(
                message=f"{request.selected_model} selected. What issue are you facing? (e.g., pickup, engine, brake, transmission, electrical)",
                stage="query_input",
                timestamp=timestamp
            )
        else:
            return ChatResponse(
                message="What issue are you facing? (e.g., pickup, engine, brake, transmission, electrical)",
                stage="query_input",
                timestamp=timestamp
            )
    
    elif request.action == "submit_query" or request.action == "followup_query":
        # Handle the main query submission and follow-up queries
        if request.selected_model:
            user_input = f'the model user selected - {request.selected_model} {request.user_query}'
        else:
            user_input = request.user_query
            
        result = fetch_jc_data(user_input)
        
        if request.action == "followup_query":
            follow_up_message = f"Here's the additional information you requested:\n\n{result}\n\nIs there anything else you'd like to know about this topic or any other job card information you need?"
        else:
            follow_up_message = f"{result}\n\nDoes this help? Feel free to ask any follow-up questions or request more specific information!"

        return ChatResponse(
            message=follow_up_message,
            stage="conversation",
            timestamp=timestamp
        )
    
    elif request.action == "reset":
        return ChatResponse(
            message="Chat has been reset. Starting over...",
            stage="reset",
            timestamp=timestamp
        )
    
    else:
        raise HTTPException(status_code=400, detail="Invalid action")

# if __name__ == "__main__":
#     print("Starting Vehicle Diagnostic Chat API...")
#     print("API will be available at: http://localhost:8000")
#     print("Docs available at: http://localhost:8000/docs")
#     uvicorn.run(app, host="0.0.0.0", port=8000)