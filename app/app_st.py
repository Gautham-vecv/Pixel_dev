import streamlit as st
import time

# Configure page
st.set_page_config(
    page_title="Vehicle Diagnostic ChatBot",
    page_icon="🚗",
    layout="centered"
)

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_stage" not in st.session_state:
    st.session_state.chat_stage = "initial"
if "selected_model" not in st.session_state:
    st.session_state.selected_model = None
if "initial_message_shown" not in st.session_state:
    st.session_state.initial_message_shown = False
if "issue_input" not in st.session_state:
    st.session_state.issue_input = ""

# Dummy user credentials
VALID_USERS = {
    "admin": "password123",
    "user1": "demo123",
    "test": "test123"
}

# Vehicle models array
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

issue_categories = [
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

def add_message(role, content):
    """Add message to chat history"""
    st.session_state.messages.append({"role": role, "content": content})
    # Log to terminal in real-time
    print(f"{role.upper()}: {content}")

def filter_models(user_input):
    """Filter vehicle models based on user input"""
    if not user_input:
        return VEHICLE_MODELS[:10]  # Show first 10 models if no input
    
    filtered = [model for model in VEHICLE_MODELS if user_input.upper() in model.upper()]
    return filtered[:10]  # Return max 10 matches

def filter_issues(user_input):
    """Filter issue categories based on user input"""
    if not user_input:
        return []
    
    # Replace underscores with spaces for better matching
    formatted_categories = [cat.replace('_', ' ') for cat in issue_categories]
    filtered = []
    
    for i, category in enumerate(formatted_categories):
        if user_input.lower() in category.lower():
            filtered.append(issue_categories[i])
    
    return filtered[:5]  # Return max 5 matches

def reset_chat():
    """Reset chat to initial state"""
    st.session_state.messages = []
    st.session_state.chat_stage = "initial"
    st.session_state.selected_model = None
    st.session_state.initial_message_shown = False
    st.session_state.issue_input = ""
    print("SYSTEM: Chat reset")

# LOGIN PAGE
if not st.session_state.authenticated:
    st.title("🚗 Vehicle Diagnostic ChatBot - Login")
    st.markdown("---")
    
    # Create login form
    with st.container():
        st.subheader("Please login to continue")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            username = st.text_input("Username", placeholder="Enter your username")
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            
            if st.button("Login", use_container_width=True):
                if username in VALID_USERS: #VALID_USERS[username] == password
                    st.session_state.authenticated = True
                    print(f"SYSTEM: User '{username}' logged in successfully")
                    st.success("Login successful! 🎉")
                    time.sleep(1)
                    st.rerun()
                else:
                    print(f"SYSTEM: Failed login attempt for username '{username}'")
                    st.error("Invalid username or password! ❌")
    
    # Show demo credentials
    st.markdown("---")
    st.subheader("Demo Credentials")
    st.info("""
    **Try these demo accounts:**
    - Username: `admin` | Password: `password123`
    - Username: `user1` | Password: `demo123`  
    - Username: `test` | Password: `test123`
    """)

# CHAT PAGE
else:
    # Header with logout
    col1, col2 = st.columns([3, 1])
    with col1:
        st.title("🚗 Vehicle Diagnostic Chat")
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
        # Handle different chat stages
        if st.session_state.chat_stage == "initial":
            # Show initial greeting message first
            if not st.session_state.initial_message_shown:
                add_message("assistant", "Welcome to Vehicle Diagnostic Chat! 🚗\n\nAre you here for a vehicle diagnostic of a particular model?")
                st.session_state.initial_message_shown = True
                st.rerun()
        
        # Display chat messages
        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])
        
        # Show interaction buttons based on stage
        if st.session_state.chat_stage == "initial" and st.session_state.initial_message_shown:
            # Show Yes/No buttons after the initial message is displayed
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes", use_container_width=True, key="yes_btn"):
                    add_message("user", "Yes")
                    add_message("assistant", "Great! Please enter or select your vehicle model from the dropdown below:")
                    st.session_state.chat_stage = "model_selection"
                    st.rerun()
            
            with col2:
                if st.button("No", use_container_width=True, key="no_btn"):
                    add_message("user", "No")
                    add_message("assistant", "No problem! If you need any vehicle diagnostic services in the future, feel free to come back. Have a great day! 👋")
                    st.session_state.chat_stage = "ended"
                    st.rerun()
        
        elif st.session_state.chat_stage == "model_selection":
            # Model selection with searchable dropdown
            st.markdown("**Select your vehicle model:**")
            
            selected_model = st.selectbox("Choose from matching models:", [""] + VEHICLE_MODELS, key="model_dropdown")
            if selected_model:
                if st.button("Confirm Model", disabled=not selected_model, use_container_width=True):
                    if selected_model:
                        add_message("user", f"Selected model: {selected_model}")
                        st.session_state.selected_model = selected_model
                        add_message("assistant", f"Perfect! You've selected **{selected_model}**.\n\nNow, please describe the issue you're experiencing. You can type your own description or search from our common issue categories:")
                        st.session_state.chat_stage = "issue_selection"
                        st.rerun()
            else:
                st.info("No models found matching your search. Please try a different search term.")
        
        elif st.session_state.chat_stage == "issue_selection":
            # Issue selection with searchable dropdown that allows custom input
            st.markdown("**Describe your issue:**")
            
            # Text input to capture user typing for filtering
            search_input = st.text_input(
                "Start typing to search categories or describe your custom issue:",
                placeholder="e.g., engine not starting, brake problems, cooling system issues...",
                key="issue_search_input"
            )
            
            # Create dynamic options based on search input
            if search_input:
                # Get matching categories
                matching_issues = filter_issues(search_input)
                formatted_matches = [issue.replace('_', ' ').title() for issue in matching_issues]
                
                # Create options list: custom input first, then matching categories
                options = [f"🔧 Custom: {search_input}"] + [f"📂 {match}" for match in formatted_matches]
            else:
                # Show some default categories when no input
                formatted_defaults = [cat.replace('_', ' ').title() for cat in issue_categories]
                options = [f"📂 {cat}" for cat in formatted_defaults]
            
            # Selectbox with dynamic options
            selected_option = st.selectbox(
                "Select from suggestions or your custom description:",
                [""] + options,
                key="issue_selectbox"
            )
            
            if selected_option and st.button("Confirm Issue", use_container_width=True):
                if selected_option.startswith("🔧 Custom:"):
                    # Extract custom description
                    custom_issue = selected_option.replace("🔧 Custom: ", "")
                    add_message("user", f"Custom issue description: {custom_issue}")
                    st.session_state.selected_issue = custom_issue
                    add_message("assistant", f"Thank you for describing your issue: **{custom_issue}**\n\nI'm now connecting you to our diagnostic system. Please wait while I run the initial diagnostic checks...")
                elif selected_option.startswith("📂"):
                    # Extract category
                    category_issue = selected_option.replace("📂 ", "")
                    add_message("user", f"Selected issue category: {category_issue}")
                    st.session_state.selected_issue = category_issue
                    add_message("assistant", f"Perfect! You've selected **{category_issue}** for diagnosis.\n\nI'm now connecting you to our diagnostic system for this issue. Please wait while I run the initial diagnostic checks...")
                
                st.session_state.chat_stage = "diagnostic_complete"
                st.rerun()
            
            # Help text
            if search_input:
                st.info("💡 **Tip:** Your custom description will appear at the top of the list, or select from suggested categories below.")
            else:
                st.info("💡 **Tip:** Start typing to see matching categories or describe your issue in your own words.")
        
        elif st.session_state.chat_stage == "diagnostic_complete":
            st.markdown("**Diagnostic complete!**")
            st.write("Our technical team will contact you shortly with the diagnostic results and next steps. Thank you for using our vehicle diagnostic service! 🔧")
            st.session_state.chat_stage = "ended"
            st.rerun()
        
        elif st.session_state.chat_stage == "ended":
            # Show restart option
            if st.button("Start Over", use_container_width=True):
                reset_chat()
                st.rerun()
    
    # Sidebar with chat info
    with st.sidebar:
        st.header("Diagnostic Info")
        st.write(f"**Stage:** {st.session_state.chat_stage.replace('_', ' ').title()}")
        if st.session_state.selected_model:
            st.write(f"**Selected Model:** {st.session_state.selected_model}")
        if hasattr(st.session_state, 'selected_issue') and st.session_state.selected_issue:
            st.write(f"**Issue:** {st.session_state.selected_issue}")
        st.write(f"**Messages:** {len(st.session_state.messages)}")
        
        st.markdown("---")
        st.subheader("Available Models")
        st.write(f"**Total Models:** {len(VEHICLE_MODELS)}")
        st.write("• PRO Series")
        st.write("• Bus Models") 
        st.write("• Truck Models")
        st.write("• CNG Variants")
        st.write("• EV Models")
        


        
        st.markdown("---")
        if st.button("Clear Chat", use_container_width=True):
            reset_chat()
            st.rerun()