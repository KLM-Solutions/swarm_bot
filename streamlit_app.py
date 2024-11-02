import streamlit as st
import os
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

# Load API key from Streamlit secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# Initialize session states for both chatbots
if "chat_history_1" not in st.session_state:
    st.session_state.chat_history_1 = []

if "chat_history_2" not in st.session_state:
    st.session_state.chat_history_2 = []

if "current_agent_1" not in st.session_state:
    st.session_state.current_agent_1 = "Triage Agent"

if "current_agent_2" not in st.session_state:
    st.session_state.current_agent_2 = "All Agents"

if "user_submitted_1" not in st.session_state:
    st.session_state.user_submitted_1 = False

if "user_submitted_2" not in st.session_state:
    st.session_state.user_submitted_2 = False

# Agent Colors for visual distinction
AGENT_COLORS_1 = {
    "Triage Agent": "#FF9999",           # Light Red
    "Product Strategy Agent": "#99FF99",  # Light Green
    "Market Research Agent": "#9999FF",   # Light Blue
    "Technical Advisor Agent": "#FFFF99", # Light Yellow
    "UX Design Agent": "#FF69B4"         # Hot Pink
}

AGENT_COLORS_2 = {
    "Product Strategy Agent": "#99FF99",  # Light Green
    "Market Research Agent": "#9999FF",   # Light Blue
    "Technical Advisor Agent": "#FFFF99", # Light Yellow
    "UX Design Agent": "#FF69B4"         # Hot Pink
}

# Agent system messages for first chatbot
AGENT_INSTRUCTIONS_1 = {
    "Triage Agent": """You are a product management triage agent and the first point of contact. Your role is to:
    1. Greet users professionally
    2. Analyze queries and route them to the appropriate specialist:
       - For product strategy, roadmap, and vision → Product Strategy Agent
       - For market analysis, competitive research → Market Research Agent
       - For technical feasibility and implementation → Technical Advisor Agent
       - For user experience and design → UX Design Agent
    3. If user message is unclear, ask clarifying questions
    4. Always maintain a professional and solution-oriented tone
    
    Important: You must ALWAYS determine which specialist agent should handle the query and explicitly state the transfer.""",
    
    "Product Strategy Agent": """You are a product strategy specialist.
    1. Help define product vision and strategy
    2. Assist with roadmap planning and prioritization
    3. Provide guidance on product-market fit
    4. Help with feature prioritization frameworks
    5. Offer solutions for product positioning
    6. For technical or UX-specific queries, indicate need to transfer back to Triage Agent""",
    
    "Market Research Agent": """You are a market research and analysis expert.
    1. Provide market analysis frameworks
    2. Help with competitive analysis
    3. Guide user research methodologies
    4. Assist with market sizing and opportunity assessment
    5. Offer insights on market trends
    6. For strategy or technical queries, indicate need to transfer back to Triage Agent""",
    
    "Technical Advisor Agent": """You are a technical advisor for product development.
    1. Assess technical feasibility of features
    2. Provide implementation guidance
    3. Help with technical architecture decisions
    4. Offer solutions for technical challenges
    5. Guide API and integration strategies
    6. For strategy or UX queries, indicate need to transfer back to Triage Agent""",
    
    "UX Design Agent": """You are a UX design specialist.
    1. Provide user experience best practices
    2. Guide interface design decisions
    3. Help with user flow optimization
    4. Offer solutions for usability challenges
    5. Assist with prototyping strategies
    6. For technical or market research queries, indicate need to transfer back to Triage Agent"""
}

# Agent system messages for second chatbot
AGENT_INSTRUCTIONS_2 = {
    "Product Strategy Agent": """You are a product strategy specialist.
    1. Help define product vision and strategy
    2. Assist with roadmap planning and prioritization
    3. Provide guidance on product-market fit
    4. Help with feature prioritization frameworks
    5. Offer solutions for product positioning""",
    
    "Market Research Agent": """You are a market research and analysis expert.
    1. Provide market analysis frameworks
    2. Help with competitive analysis
    3. Guide user research methodologies
    4. Assist with market sizing and opportunity assessment
    5. Offer insights on market trends""",
    
    "Technical Advisor Agent": """You are a technical advisor for product development.
    1. Assess technical feasibility of features
    2. Provide implementation guidance
    3. Help with technical architecture decisions
    4. Offer solutions for technical challenges
    5. Guide API and integration strategies""",
    
    "UX Design Agent": """You are a UX design specialist.
    1. Provide user experience best practices
    2. Guide interface design decisions
    3. Help with user flow optimization
    4. Offer solutions for usability challenges
    5. Assist with prototyping strategies"""
}

def analyze_message_for_routing(message: str) -> str:
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": """Analyze the following message and determine which specialist should handle it:
                - If about product strategy/roadmap → 'Product Strategy Agent'
                - If about market/competition → 'Market Research Agent'
                - If about technical feasibility → 'Technical Advisor Agent'
                - If about user experience/design → 'UX Design Agent'
                - If unclear or general → 'Triage Agent'
                Only respond with the exact agent name."""},
                {"role": "user", "content": message}
            ],
            temperature=0.3,
            max_tokens=1000
        )
        suggested_agent = response.choices[0].message.content.strip()
        return suggested_agent if suggested_agent in AGENT_INSTRUCTIONS_1 else "Triage Agent"
    except Exception:
        return "Triage Agent"

def get_agent_response_1(message: str, agent_type: str, chat_history: list) -> tuple:
    try:
        messages = [
            {"role": "system", "content": AGENT_INSTRUCTIONS_1[agent_type]},
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

def get_agent_response_2(message: str, agent_type: str, chat_history: list) -> str:
    try:
        messages = [
            {"role": "system", "content": AGENT_INSTRUCTIONS_2[agent_type]},
            {"role": "user", "content": message}
        ]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=1000
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        return f"Error: Unable to get response from {agent_type}. Please try again. ({str(e)})"

def handle_user_input_1():
    if st.session_state.user_input_1 and not st.session_state.user_submitted_1:
        user_message = st.session_state.user_input_1
        
        st.session_state.chat_history_1.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        
        new_agent = analyze_message_for_routing(user_message)
        
        response, final_agent = get_agent_response_1(
            user_message, 
            new_agent,
            st.session_state.chat_history_1
        )
        
        st.session_state.current_agent_1 = final_agent
        
        st.session_state.chat_history_1.append({
            "role": "assistant",
            "content": response,
            "agent": final_agent,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        
        st.session_state.user_submitted_1 = True
        st.rerun()

def handle_user_input_2():
    if st.session_state.user_input_2 and not st.session_state.user_submitted_2:
        user_message = st.session_state.user_input_2
        
        st.session_state.chat_history_2.append({
            "role": "user",
            "content": user_message,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        
        responses = {}
        for agent_type in AGENT_INSTRUCTIONS_2.keys():
            response = get_agent_response_2(
                user_message, 
                agent_type,
                st.session_state.chat_history_2
            )
            responses[agent_type] = response
        
        st.session_state.chat_history_2.append({
            "role": "assistant",
            "content": responses,
            "timestamp": datetime.now().strftime("%H:%M"),
        })
        
        st.session_state.user_submitted_2 = True
        st.rerun()

# Main UI
st.title("Product Management Assistant")

# Create tabs
tab1, tab2 = st.tabs(["Single Agent Chatbot", "Multi-Agent Chatbot"])

with tab1:
    st.write("Chat with a single agent at a time, starting with the Triage Agent")
    
    # Sidebar for first chatbot
    with st.sidebar:
        st.header("Current Agent")
        st.markdown(
            f'<div style="padding:10px;border-radius:5px;background-color:{AGENT_COLORS_1[st.session_state.current_agent_1]}">Speaking with: {st.session_state.current_agent_1}</div>',
            unsafe_allow_html=True
        )
        
        st.header("Agent Types")
        for agent, color in AGENT_COLORS_1.items():
            st.markdown(
                f'<div style="padding:5px;border-radius:3px;background-color:{color};margin:2px">{agent}</div>',
                unsafe_allow_html=True
            )
    
    # Chat interface for first chatbot
    st.markdown("### Conversation")
    for message in st.session_state.chat_history_1:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(f"{message['timestamp']} - You: {message['content']}")
        else:
            with st.chat_message("assistant", avatar="💡"):
                agent = message.get("agent", "Triage Agent")
                st.markdown(
                    f'<div style="padding:5px;border-radius:3px;background-color:{AGENT_COLORS_1[agent]};margin-bottom:5px">'
                    f'{message["timestamp"]} - {agent}</div>',
                    unsafe_allow_html=True
                )
                st.write(message["content"])
    
    # Chat input for first chatbot
    st.text_input(
        "Type your message here...",
        key="user_input_1",
        on_change=handle_user_input_1,
        value=""
    )
    
    if st.session_state.user_submitted_1:
        st.session_state.user_submitted_1 = False
    
    if st.button("Clear Chat", key="clear_1"):
        st.session_state.chat_history_1 = []
        st.session_state.current_agent_1 = "Triage Agent"
        st.session_state.user_submitted_1 = False
        st.rerun()

with tab2:
    st.write("Chat with all agents simultaneously")
    
    # Sidebar for second chatbot
    with st.sidebar:
        st.header("Agents View")
        st.markdown(
            '<div style="padding:10px;border-radius:5px;background-color:#DDDDDD">All agents will respond to your query</div>',
            unsafe_allow_html=True
        )
        
        st.header("Agent Types")
        for agent, color in AGENT_COLORS_2.items():
            st.markdown(
                f'<div style="padding:5px;border-radius:3px;background-color:{color};margin:2px">{agent}</div>',
                unsafe_allow_html=True
            )
    
    # Chat interface for second chatbot
    st.markdown("### Conversation")
    for message in st.session_state.chat_history_2:
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(f"{message['timestamp']} - You: {message['content']}")
        else:
            with st.chat_message("assistant", avatar="💡"):
                st.write(f"{message['timestamp']} - Agent Responses:")
                
                responses = message["content"]
                if isinstance(responses, dict):
                    for agent, response in responses.items():
                        with st.expander(f"{agent} Response", expanded=False):
                            st.markdown(
                                f'<div style="padding:5px;border-radius:3px;background-color:{AGENT_COLORS_2[agent]};margin-bottom:5px">'
                                f'{agent}</div>',
                                unsafe_allow_html=True
                            )
                            st.write(response)
    
    # Chat input for second chatbot
    st.text_input(
        "Type your message here...",
        key="user_input_2",
        on_change=handle_user_input_2,
        value=""
    )
    
    if st.session_state.user_submitted_2:
        st.session_state.user_submitted_2 = False
    
    if st.button("Clear Chat", key="clear_2"):
        st.session_state.chat_history_2 = []
        st.session_state.user_submitted_2 = False
        st.rerun()

# Footer
st.markdown("---")
st.markdown("*This is an AI product management assistant with two different interaction modes.*")
