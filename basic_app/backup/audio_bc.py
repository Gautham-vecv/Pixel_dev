import streamlit as st
import requests
import time
import os
import json
import tempfile
from datetime import datetime
from audiorecorder import audiorecorder
from groq import Groq

# Configure page
st.set_page_config(
    page_title="Job Card ChatBot",
    layout="centered"
)

# API configuration
API_BASE_URL = "http://localhost:8000"

# Initialize Groq client for audio transcription
os.environ['GROQ_API_KEY'] = "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"
groq_client = Groq()

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_stage" not in st.session_state:
    st.session_state.chat_stage = "initial"
if "selected_model" not in st.session_state:
    st.session_state.selected_model = None
if "user_query" not in st.session_state:
    st.session_state.user_query = ""
if "initial_message_shown" not in st.session_state:
    st.session_state.initial_message_shown = False
if "vehicle_models" not in st.session_state:
    st.session_state.vehicle_models = []

def add_message(role, content):
    """
    Add message to chat history, unless the last one is exactly the same.
    """
    # Bail out if history ends with the same role+content
    if st.session_state.messages:
        last = st.session_state.messages[-1]
        if last["role"] == role and last["content"] == content:
            return
    
    st.session_state.messages.append({"role": role, "content": content})
    print(f"{role.upper()}: {content}")

def transcribe_audio(audio_bytes):
    """
    Transcribe audio using Groq API
    """
    try:
        # Create a temporary file to save the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_file:
            temp_file.write(audio_bytes)
            temp_file_path = temp_file.name
        
        # Transcribe the audio file
        with open(temp_file_path, "rb") as file:
            transcription = groq_client.audio.transcriptions.create(
                file=file,
                model="distil-whisper-large-v3-en",
                prompt="Vehicle maintenance and job card related transcription",
                response_format="text",  # Get just the text, not verbose JSON
                language="en",
                temperature=0.0
            )
        
        # Clean up the temporary file
        os.unlink(temp_file_path)
        
        return transcription
    
    except Exception as e:
        st.error(f"Error transcribing audio: {str(e)}")
        return None

def api_request(endpoint, method="GET", data=None):
    """Make API request with error handling"""
    try:
        url = f"{API_BASE_URL}{endpoint}"
        if method == "GET":
            response = requests.get(url)
        elif method == "POST":
            response = requests.post(url, json=data)
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"API error: {response.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        st.error("Could not connect to the API. Please make sure the FastAPI server is running on http://localhost:8000")
        return None
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None

def login_user(username, password):
    """Login user via API"""
    data = {"username": username, "password": password}
    return api_request("/login", "POST", data)

def get_chat_response(action, selected_model=None, user_query=None):
    """Get chat response from API"""
    request_data = {
        "action": action,
        "selected_model": selected_model,
        "user_query": user_query
    }
  
    return api_request("/chat", "POST", request_data)

def load_initial_data():
    """Load vehicle models"""
    models_response = api_request("/models")
    if models_response:
        st.session_state.vehicle_models = models_response["models"]

def reset_chat():
    """Reset chat to initial state"""
    st.session_state.messages = []
    st.session_state.chat_stage = "initial"
    st.session_state.selected_model = None
    st.session_state.user_query = ""
    st.session_state.initial_message_shown = False
    print("SYSTEM: Chat reset")

def process_user_input(user_input, input_type="text"):
    """Process user input (either text or transcribed audio)"""
    if user_input and user_input.strip():
        # Validate query
        valid_resp = api_request("/validate_query", "POST", {"user_query": user_input})
        if not valid_resp or not valid_resp.get("valid", False):
            add_message("assistant", "Sorry, that query isn't valid for this dataset. Please ask about parts, counts, action_taken, observation, or customer_voice.")
            st.rerun()
        else:
            # Add user query to chat with input type indicator
            if input_type == "audio":
                add_message("user", f"🎤 **Audio Query:** {user_input}")
            else:
                add_message("user", f"**Query:** {user_input}")
            
            st.session_state.user_query = user_input
            
            # Get API response
            with st.spinner("Searching job card data..."):
                if st.session_state.chat_stage == "query_input":
                    response = get_chat_response("submit_query", st.session_state.selected_model, user_input)
                    st.session_state.chat_stage = "conversation"
                else:  # conversation stage follow-up
                    response = get_chat_response("followup_query", st.session_state.selected_model, user_input)
            
            if response:
                add_message("assistant", response["message"])
                st.rerun()

# Load initial data if authenticated
if st.session_state.authenticated and not st.session_state.vehicle_models:
    load_initial_data()

# Set authenticated to True for testing purposes
st.session_state.authenticated = True

if st.session_state.authenticated:
    
    # Header with logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("Job Card Chat")
    with col2:
        if st.button("Logout"):
            st.session_state.authenticated = False
            reset_chat()
            print("SYSTEM: User logged out")
            st.rerun()
    
    st.markdown("---")
    
    # Chat container
    chat_container = st.container()
    
    with chat_container:
        # Show initial greeting and model selection
        if not st.session_state.initial_message_shown:
            response = get_chat_response("initial")
            if response:
                add_message("assistant", response["message"])
                st.session_state.initial_message_shown = True
                st.session_state.chat_stage = "model_selection"
                st.rerun()
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Model selection stage (right after initial greeting)
        if st.session_state.chat_stage == "model_selection":
            st.markdown("---")
            st.markdown("**Vehicle Model Selection (Optional):**")
            selected_model = st.selectbox(
                "Select a vehicle model if you're looking for model-specific information:",
                ["None - General inquiry"] + st.session_state.vehicle_models,
                index=0,
                key="model_selectbox"
            )
            
            if st.button("Continue", use_container_width=True, type="primary"):
                # Store selected model (None if general inquiry)
                if selected_model == "None - General inquiry":
                    st.session_state.selected_model = None
                    user_message = "I'm looking for general information (no specific model selected)"
                else:
                    st.session_state.selected_model = selected_model
                    user_message = f"I'm interested in information about: **{selected_model}**"
                
                add_message("user", user_message)
                
                # Get response asking what they're looking for
                response = get_chat_response("model_selected", st.session_state.selected_model)
                if response:
                    add_message("assistant", response["message"])
                    st.session_state.chat_stage = "query_input"
                    st.rerun()
        
        # Query input stage (after model selection)
        elif st.session_state.chat_stage == "query_input":
            st.markdown("---")
            st.markdown("**Choose your input method:**")
            
            # Create tabs for text and audio input
            tab1, tab2 = st.tabs(["💬 Text Input", "🎤 Voice Input"])
            
            with tab1:
                user_query = st.chat_input("Describe the problem or information you need...")
                if user_query:
                    process_user_input(user_query, "text")
            
            with tab2:
                st.markdown("**Record your voice message:**")
                audio = audiorecorder(
                    start_prompt="",  # Empty string
                    stop_prompt="",   # Empty string  
                    pause_prompt="",  # Empty string
                    show_visualizer=True,  # Enable visualizer
                    key="visual_recorder"
                )

                
                if len(audio) > 0:
                    # Display audio player
                    # st.audio(audio.export().read())
                    audio_bytes = audio.export().read()
                    with st.spinner("Transcribing audio..."):
                        transcribed_text = transcribe_audio(audio_bytes)
                    if transcribed_text:
                                st.success(f"Transcribed: {transcribed_text}")
                    else:
                                st.error("Failed to transcribe audio. Please try again.")
                    if st.button("🔄 Send the query", use_container_width=True, type="primary"):
                        
                      process_user_input(transcribed_text, "audio")
                            
        
        # Conversation stage (back and forth after initial query)
        elif st.session_state.chat_stage == "conversation":
            st.markdown("---")
            st.markdown("**Continue the conversation:**")
            
            # Create tabs for follow-up input
            tab1, tab2 = st.tabs(["💬 Text Follow-up", "🎤 Voice Follow-up"])
            
            with tab1:
                follow_up_query = st.chat_input("Ask follow-up questions or request more information...")
                if follow_up_query:
                    process_user_input(follow_up_query, "text")
            
            with tab2:
                st.markdown("**Record your follow-up question:**")
                audio_followup = audiorecorder(
                    start_prompt="",  # Empty string
                    stop_prompt="",   # Empty string  
                    pause_prompt="",  # Empty string
                    show_visualizer=True,  # Enable visualizer
                    key="visual_recorder"
                )
                
                if len(audio_followup) > 0:
                    # Display audio player
                    # st.audio(audio_followup.export().read())
                    
                    # Transcribe button
                    if st.button("🔄 Transcribe & Send Follow-up", use_container_width=True, type="primary"):
                        with st.spinner("Transcribing audio..."):
                            # Get audio bytes
                            audio_bytes = audio_followup.export().read()
                            
                            # Transcribe audio
                            transcribed_text = transcribe_audio(audio_bytes)
                            
                            if transcribed_text:
                                st.success(f"Transcribed: {transcribed_text}")
                                # Add follow-up indicator to the message
                                add_message("user", f"🎤 **Audio Follow-up:** {transcribed_text}")
                                
                                with st.spinner("Searching for more information..."):
                                    response = get_chat_response("followup_query", st.session_state.selected_model, transcribed_text)
                                
                                if response:
                                    add_message("assistant", response["message"])
                                    st.rerun()
                            else:
                                st.error("Failed to transcribe audio. Please try again.")
            
            # Action buttons
            st.markdown("---")
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("🔄 Start New Query", use_container_width=True):
                    reset_chat()
                    st.rerun()
            with col2:
                if st.button("📋 Clear Chat", use_container_width=True):
                    st.session_state.messages = []
                    st.rerun()
    
    # Sidebar with info
    with st.sidebar:
        st.header("📊 Query Info")
        st.write(f"**Stage:** {st.session_state.chat_stage.replace('_', ' ').title()}")
        if st.session_state.selected_model:
            st.write(f"**Selected Model:** {st.session_state.selected_model}")
        if st.session_state.user_query:
            st.write(f"**Query:** {st.session_state.user_query[:50]}{'...' if len(st.session_state.user_query) > 50 else ''}")
        st.write(f"**Messages:** {len(st.session_state.messages)}")
        
        st.markdown("---")
        st.header("🔊 Audio Features")
        st.write("✅ Voice recording")
        st.write("✅ Auto-transcription") 
        st.write("✅ Text & Voice support")
        
        # API Status
        st.markdown("---")
        st.header("🌐 API Status")
        try:
            response = requests.get(f"{API_BASE_URL}/")
            if response.status_code == 200:
                st.success("🟢 API Connected")
            else:
                st.error("🔴 API Error")
        except:
            st.error("🔴 API Disconnected")
        
        st.markdown("---")
        if st.button("🗑️ Reset Everything", use_container_width=True):
            reset_chat()
            st.rerun()