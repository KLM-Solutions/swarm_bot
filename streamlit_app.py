import streamlit as st
import os
from datetime import datetime, timedelta
import json
from typing import Dict
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

try:
    # First try to get from Streamlit secrets
    if 'OPENAI_API_KEY' not in os.environ:
        os.environ['OPENAI_API_KEY'] = st.secrets['OPENAI_API_KEY']
    
    if not os.environ['OPENAI_API_KEY']:
        st.error("OpenAI API key not found! Please configure it in your secrets.")
        st.stop()
except Exception as e:
    st.error("Error loading OpenAI API key from secrets. Please check your configuration.")
    st.stop()

# Initialize OpenAI client
client = OpenAI()

# Initialize session states
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "current_agent" not in st.session_state:
    st.session_state.current_agent = "Triage Agent"

if "user_submitted" not in st.session_state:
    st.session_state.user_submitted = False

# Agent Colors for visual distinction
AGENT_COLORS = {
    "Triage Agent": "#FF9999",        # Light Red
    "Medical Advice Agent": "#99FF99", # Light Green
    "Appointment Scheduling Agent": "#9999FF",  # Light Blue
    "Prescription Details Agent": "#FFFF99",    # Light Yellow
    "Fitness and Exercise Agent": "#4682B4",    # Steel Blue
    "Women's Health Agent": "#FF69B4"           # Hot Pink
}

# Utility Functions
def get_next_wednesday():
    today = datetime.now()
    days_ahead = (2 - today.weekday() + 7) % 7
    next_wednesday = today + timedelta(days=days_ahead)
    return next_wednesday.strftime("%Y-%m-%d")

def get_appointments() -> Dict:
    return st.session_state.get('appointments', {})

def save_appointments(appointments):
    st.session_state.appointments = appointments

def book_appointment(date: str, time: str) -> str:
    appointments = get_appointments()
    appointment_key = f"{date}_{time}"
    
    if appointment_key in appointments:
        return f"Sorry, the time slot for {date} at {time} is already booked."
    
    appointments[appointment_key] = {
        "date": date,
        "time": time,
        "booked_at": datetime.now().isoformat()
    }
    
    save_appointments(appointments)
    return f"Appointment booked successfully for {date} at {time}."

def agent_book_appointment(date: str = "next_wednesday", time: str = "15:00") -> dict:
    if date == "next_wednesday":
        date = get_next_wednesday()
    result = book_appointment(date, time)
    success = "successfully" in result
    return {"result": result, "success": success, "date": date, "time": time}

# Agent system messages
AGENT_INSTRUCTIONS = {
    "Triage Agent": """You are a healthcare triage agent and the first point of contact. Your role is to:
    1. Greet new users warmly
    2. Analyze user messages and route them to the appropriate specialist:
       - For symptoms and health concerns → Medical Advice Agent
       - For appointment scheduling → Appointment Scheduling Agent
       - For medication questions → Prescription Details Agent
    3. If user message is unclear, ask clarifying questions
    4. Always maintain a professional and caring tone
    
    Important: You must ALWAYS determine which specialist agent should handle the query and explicitly state the transfer.""",
    
    "Medical Advice Agent": """You are a medical professional providing general medical advice.
    1. Listen carefully to symptoms
    2. Provide general health guidance
    3. Always remind users to seek professional medical help for serious conditions
    4. Be detailed but cautious in your advice
    5. If user asks about medications or appointments, indicate need to transfer back to Triage Agent""",
    
    "Appointment Scheduling Agent": """You are an appointment scheduler.
    1. Help users book healthcare appointments efficiently
    2. You can book appointments using the book_appointment function
    3. If user asks for 'next Wednesday', use that directly as the date parameter
    4. For medical advice or prescription queries, indicate need to transfer back to Triage Agent""",
    
    "Prescription Details Agent": """You are a pharmacist providing medication information.
    1. Provide general information about medications
    2. Explain common side effects and interactions
    3. Never prescribe medications
    4. Always recommend consulting a doctor for specific prescriptions
    5. For medical advice or appointment queries, indicate need to transfer back to Triage Agent""",
    
    "Fitness and Exercise Agent": """You are a fitness coach providing exercise advice and information.
    1. Offer general fitness tips and exercise recommendations
    2. Discuss basic workout routines for different fitness levels
    3. Provide information on exercise safety and injury prevention
    4. Emphasize the importance of consulting a healthcare professional before starting new exercise regimens
    5. For medical advice or nutrition queries, indicate need to transfer back to Triage Agent""",
    
    "Women's Health Agent": """You are a women's health specialist providing information on women's health issues.
1. Offer general information on women's health topics (e.g., menstruation, menopause, pregnancy)
2. Discuss common women's health concerns and preventive care
3. Provide guidance on when to seek professional medical advice
4. Maintain a sensitive and supportive tone
5. For specific medical advice or appointment queries, indicate need to transfer back to Triage Agent"""
}

def analyze_message_for_routing(message: str) -> str:
    """Analyze message content to determine appropriate agent"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Analyze the following message and determine which specialist should handle it:
                - If about symptoms/health concerns → 'Medical Advice Agent'
                - If about appointments → 'Appointment Scheduling Agent'
                - If about medications → 'Prescription Details Agent'
                - If about fitness or exercise → 'Fitness and Exercise Agent'
                - If about women's health → 'Women's Health Agent'
                - If unclear or general → 'Triage Agent'
                Only respond with the exact agent name."""},
                {"role": "user", "content": message}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        suggested_agent = response.choices[0].message.content.strip()
        return suggested_agent if suggested_agent in AGENT_INSTRUCTIONS else "Triage Agent"
    except Exception:
        return "Triage Agent"

def get_agent_response(message: str, agent_type: str, chat_history: list) -> tuple:
    """Get response from agent"""
    try:
        # Include relevant chat history for context
        messages = [
            {"role": "system", "content": AGENT_INSTRUCTIONS[agent_type]},
            {"role": "user", "content": message}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        response_text = response.choices[0].message.content
        return response_text, agent_type
        
    except Exception as e:
        return f"Error: Unable to get response. Please try again. ({str(e)})", agent_type

def handle_user_input():
    if st.session_state.user_input and not st.session_state.user_submitted:
        user_message = st.session_state.user_input
        
        # Add user message to chat history
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        
        # Analyze the message and determine the appropriate agent
        new_agent = analyze_message_for_routing(user_message)
        
        # Get response from the appropriate agent
        response, final_agent = get_agent_response(
            user_message, 
            new_agent,
            st.session_state.chat_history
        )
        
        # Update current agent
        st.session_state.current_agent = final_agent
        
        # Add assistant response to chat history
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": response,
            "agent": final_agent,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        
        # Mark as submitted
        st.session_state.user_submitted = True
        
        # Rerun the app
        st.experimental_rerun()


# Streamlit UI
st.title("Healthcare Assistant")
st.write("Welcome to your AI Healthcare Assistant! How can I help you today?")

# Sidebar
with st.sidebar:
    st.header("Current Agent")
    st.markdown(
        f'<div style="padding:10px;border-radius:5px;background-color:{AGENT_COLORS[st.session_state.current_agent]}">Speaking with: {st.session_state.current_agent}</div>',
        unsafe_allow_html=True
    )
    
    # Agent Color Legend
    st.header("Agent Types")
    for agent, color in AGENT_COLORS.items():
        st.markdown(
            f'<div style="padding:5px;border-radius:3px;background-color:{color};margin:2px">{agent}</div>',
            unsafe_allow_html=True
        )
    
    st.header("Appointment Calendar")
    appointments = get_appointments()
    if appointments:
        st.write("Current Appointments:")
        for key, value in appointments.items():
            st.write(f"📅 {value['date']} at {value['time']}")
    else:
        st.write("No appointments scheduled")

# Chat interface
st.markdown("### Conversation")
for message in st.session_state.chat_history:
    if message["role"] == "user":
        with st.chat_message("user"):
            st.write(f"{message['timestamp']} - You: {message['content']}")
    else:
        with st.chat_message("assistant", avatar="👨‍⚕️"):
            agent = message.get("agent", "Triage Agent")
            st.markdown(
                f'<div style="padding:5px;border-radius:3px;background-color:{AGENT_COLORS[agent]};margin-bottom:5px">'
                f'{message["timestamp"]} - {agent}</div>',
                unsafe_allow_html=True
            )
            st.write(message["content"])

# Chat input
st.text_input(
    "Type your message here...",
    key="user_input",
    on_change=handle_user_input,
    value=""
)

if st.session_state.user_submitted:
    st.session_state.user_submitted = False

# Add a clear chat button
if st.button("Clear Chat"):
    st.session_state.chat_history = []
    st.session_state.current_agent = "Triage Agent"
    st.session_state.user_submitted = False
    st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("*This is an AI healthcare assistant. For medical emergencies, please call emergency services.*")
