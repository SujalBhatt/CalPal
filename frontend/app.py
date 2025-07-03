import streamlit as st
import requests
import random
import math

# Generate 120 stars, each with a random direction and speed
star_styles = []
star_keyframes = []
for i in range(120):
    left = random.randint(0, 99)
    top = random.randint(0, 99)
    duration = random.uniform(8, 18)
    delay = random.uniform(0, 10)
    angle = random.uniform(0, 360)
    distance = random.randint(60, 120)  # how far the star will travel (vh)
    # Calculate x/y offset using angle
    dx = distance * random.uniform(0.7, 1.0) * math.cos(math.radians(angle))
    dy = distance * random.uniform(0.7, 1.0) * math.sin(math.radians(angle))
    # Unique keyframes for each star
    kf_name = f"moveStar{i}"
    star_styles.append(
        f'<div class="star" style="left:{left}vw; top:{top}vh; animation: {kf_name} {duration:.1f}s linear {delay:.1f}s infinite;"></div>'
    )
    star_keyframes.append(
        f"""
        @keyframes {kf_name} {{
            0% {{ transform: translate(0, 0); opacity: 0.85; }}
            90% {{ opacity: 0.85; }}
            100% {{ transform: translate({dx:.1f}px, {dy:.1f}px); opacity: 0.2; }}
        }}
        """
    )

star_divs = "".join(star_styles)
keyframes_css = "\n".join(star_keyframes)

# Custom CSS for chat area, input, and message bubbles
st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@700&family=Share+Tech+Mono&display=swap');
    body, .stApp {{
        background: #000 !important;
        color: #fff;
        font-family: 'Orbitron', 'Share Tech Mono', monospace;
    }}
    .stars {{
        width: 100vw;
        height: 100vh;
        position: fixed;
        top: 0; left: 0;
        z-index: 0;
        overflow: hidden;
        pointer-events: none;
    }}
    .star {{
        position: absolute;
        width: 2.2px;
        height: 2.2px;
        background: white;
        border-radius: 50%;
        opacity: 0.85;
        box-shadow: 0 0 6px 2px #fff2, 0 0 12px 4px #b2b7ff22;
    }}
    {keyframes_css}
    .space-header {{
        text-align: center;
        margin-top: 3.5rem;
        margin-bottom: 2.5rem;
    }}
    .space-header img {{
        width: 90px;
        margin-bottom: 1.2rem;
        filter: drop-shadow(0 0 18px #a259ff88);
    }}
    .space-title {{
        font-family: 'Orbitron', monospace;
        color: #00c3ff;
        font-size: 2.8rem;
        font-weight: 700;
        letter-spacing: 2px;
        text-shadow: 0 0 16px #00c3ff55, 0 0 32px #a259ff33;
        margin-bottom: 0.5rem;
    }}
    .space-subtitle {{
        color: #b2b7ff;
        font-size: 1.2rem;
        margin-bottom: 0.5rem;
        text-shadow: 0 0 8px #a259ff44;
    }}
    /* Chat area styling */
    .custom-chat-area {{
        background: rgba(24, 24, 40, 0.85);
        border-radius: 24px;
        box-shadow: 0 0 32px #a259ff33;
        padding: 2.5rem 0.5rem 1.5rem 0.5rem;
        max-width: 700px;
        margin: 0 auto 2.5rem auto;
        min-height: 350px;
    }}
    /* Message bubble animations */
    .fade-in {{
        animation: fadeInMsg 0.7s;
    }}
    @keyframes fadeInMsg {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}
    /* User message bubble */
    .custom-user-msg {{
        display: flex;
        align-items: flex-end;
        justify-content: flex-end;
        margin: 1.2rem 0 1.2rem 20%;
        gap: 0.7rem;
    }}
    .user-bubble {{
        background: linear-gradient(135deg, #00c3ff 0%, #a259ff 100%);
        color: #fff;
        border-radius: 18px 18px 4px 18px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 0 16px #00c3ff55;
        font-family: 'Orbitron', monospace;
        font-size: 1.08rem;
        max-width: 70%;
        word-break: break-word;
        border: 2px solid #00c3ff;
        position: relative;
    }}
    .user-icon {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #232526;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 8px #00c3ff88;
    }}
    /* Assistant message bubble */
    .custom-assistant-msg {{
        display: flex;
        align-items: flex-end;
        justify-content: flex-start;
        margin: 1.2rem 20% 1.2rem 0;
        gap: 0.7rem;
    }}
    .assistant-bubble {{
        background: linear-gradient(135deg, #232526 0%, #1b2735 100%);
        color: #fff;
        border-radius: 18px 18px 18px 4px;
        padding: 1.1rem 1.4rem;
        box-shadow: 0 0 16px #a259ff55;
        font-family: 'Share Tech Mono', monospace;
        font-size: 1.08rem;
        max-width: 70%;
        word-break: break-word;
        border: 2px solid #a259ff;
        position: relative;
    }}
    .assistant-icon {{
        width: 36px;
        height: 36px;
        border-radius: 50%;
        background: #1b2735;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0 8px #a259ff88;
    }}
    /* Custom input area */
    .custom-input-area {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.7rem;
        background: rgba(24, 24, 40, 0.95);
        border-radius: 18px;
        box-shadow: 0 0 16px #a259ff44;
        padding: 0.7rem 1.2rem;
        margin: 0 auto 2.5rem auto;
        max-width: 700px;
    }}
    .custom-input-box {{
        flex: 1;
        background: #181828;
        color: #fff;
        border: 2px solid #a259ff;
        border-radius: 12px;
        font-size: 1.1rem;
        font-family: 'Orbitron', monospace;
        box-shadow: 0 0 8px #a259ff44;
        padding: 0.7rem 1.1rem;
        outline: none;
        transition: border 0.2s, box-shadow 0.2s;
    }}
    .custom-input-box:focus {{
        border: 2px solid #00c3ff;
        box-shadow: 0 0 16px #00c3ff88;
    }}
    .custom-send-btn {{
        background: linear-gradient(90deg, #a259ff 0%, #00c3ff 100%);
        color: #fff;
        border: none;
        border-radius: 12px;
        font-family: 'Orbitron', monospace;
        font-size: 1.3rem;
        font-weight: 700;
        box-shadow: 0 0 16px #a259ff88;
        padding: 0.7rem 1.3rem;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 0.5rem;
        transition: box-shadow 0.2s;
    }}
    .custom-send-btn:hover {{
        box-shadow: 0 0 32px #00c3ffcc;
    }}
    </style>
    <div class="stars">{star_divs}</div>
    """,
    unsafe_allow_html=True
)

st.set_page_config(page_title="CalPal - AI Calendar Assistant", page_icon="🪐")

# Space-themed header
st.markdown(
    """
    <div class="space-header">
        <img src="https://img.icons8.com/ios-filled/100/ffffff/planet.png" alt="Planet Icon" />
        <div class="space-title">CalPal - Book Appointments with AI</div>
        <div class="space-subtitle">Your cosmic calendar assistant</div>
    </div>
    """,
    unsafe_allow_html=True
)

if "messages" not in st.session_state:
    st.session_state["messages"] = []

# Display chat history with custom bubbles and icons
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(
            f'''
            <div class="custom-user-msg fade-in">
                <div class="user-bubble">{msg["content"]}</div>
                <div class="user-icon">
                    <img src="https://img.icons8.com/ios-filled/50/00c3ff/astronaut.png" width="26" height="26" alt="User" />
                </div>
            </div>
            ''', unsafe_allow_html=True
        )
    else:
        st.markdown(
            f'''
            <div class="custom-assistant-msg fade-in">
                <div class="assistant-icon">
                    <img src="https://img.icons8.com/ios-filled/50/a259ff/robot-2.png" width="26" height="26" alt="Bot" />
                </div>
                <div class="assistant-bubble">{msg["content"]}</div>
            </div>
            ''', unsafe_allow_html=True
        )

# Add custom instruction above the input
st.markdown('<div style="text-align:center; color:#b2b7ff; font-size:1.1rem; margin-bottom:0.5rem;">Press the rocket button 🚀 to submit your message.</div>', unsafe_allow_html=True)

# Custom input area using Streamlit's public API
with st.form(key="custom-chat-form", clear_on_submit=True):
    col1, col2 = st.columns([8, 1])
    with col1:
        user_input = st.text_input(
            "Message",  # Non-empty label for accessibility
            placeholder="Type your message and launch it into the cosmos...",
            key="input_box",
            label_visibility="collapsed",
        )
    with col2:
        send_clicked = st.form_submit_button(
            label="\U0001F680",  # Rocket emoji
            help="Send message",
            use_container_width=True
        )
    st.markdown(
        """
        <style>
        button[kind="secondary"] {
            background: linear-gradient(90deg, #a259ff 0%, #00c3ff 100%) !important;
            color: #fff !important;
            border-radius: 12px !important;
            font-family: 'Orbitron', monospace !important;
            font-size: 1.3rem !important;
            font-weight: 700 !important;
            box-shadow: 0 0 16px #a259ff88 !important;
            padding: 0.7rem 1.3rem !important;
            cursor: pointer !important;
            display: flex !important;
            align-items: center !important;
            gap: 0.5rem !important;
            transition: box-shadow 0.2s !important;
        }
        button[kind="secondary"]:hover {
            box-shadow: 0 0 32px #00c3ffcc !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

if send_clicked and user_input.strip():
    st.session_state["messages"].append({"role": "user", "content": user_input.strip()})
    try:
        response = requests.post(
            "http://localhost:8000/chat",
            json={"message": user_input.strip()},
            timeout=30
        )
        response.raise_for_status()
        bot_reply = response.json().get("response", "(No response)")
    except Exception as e:
        bot_reply = f"Error: {e}"
    st.session_state["messages"].append({"role": "assistant", "content": bot_reply})
    st.experimental_rerun() 