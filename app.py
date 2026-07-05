"""
app.py
------
Step 4 & 5: Streamlit chatbot app for Lumbini ICT Campus.

- Login / Register screen (only emails that exist in the SQLite `admin` table can log in)
- ChatGPT-like dark theme chat UI
- Persists conversation history to SQLite per logged-in admin
- Handles greetings and small talk

Run:
    streamlit run app.py

Before running for the first time:
    python scraper.py
    python data_processor.py
(database.py is auto-initialized by app.py, with a seeded default admin:
 email: admin@lict.edu.np | password: admin123)
"""

import streamlit as st
from datetime import datetime

import database as db
from chatbot_engine import ChatbotEngine

st.set_page_config(
    page_title="LICT Campus Assistant",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# ChatGPT-like dark theme styling
# ---------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .stApp {
        background-color: #212121;
        color: #ececec;
    }
    section[data-testid="stSidebar"] {
        background-color: #171717;
        border-right: 1px solid #2f2f2f;
    }
    div[data-testid="stChatMessage"] {
        background-color: #2f2f2f;
        border-radius: 12px;
        padding: 12px 16px;
        margin-bottom: 8px;
    }
    .stTextInput input, .stTextInput textarea {
        background-color: #2f2f2f;
        color: #ececec;
        border: 1px solid #4d4d4d;
        border-radius: 8px;
    }
    .stButton button {
        background-color: #10a37f;
        color: white;
        border-radius: 8px;
        border: none;
        padding: 0.5em 1.2em;
    }
    .stButton button:hover {
        background-color: #0d8c6c;
        color: white;
    }
    h1, h2, h3 {
        color: #ececec;
    }
    .login-card {
        background-color: #2f2f2f;
        padding: 2rem;
        border-radius: 16px;
        max-width: 420px;
        margin: 3rem auto;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------
db.init_db()
db.seed_default_admin()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "admin" not in st.session_state:
    st.session_state.admin = None
if "messages" not in st.session_state:
    st.session_state.messages = []


@st.cache_resource(show_spinner="Loading knowledge base...")
def load_bot():
    return ChatbotEngine()


bot = load_bot()


# ---------------------------------------------------------------------------
# Auth screens
# ---------------------------------------------------------------------------
def show_login():
    st.markdown("<h1 style='text-align:center;'>🎓 LICT Campus Assistant</h1>", unsafe_allow_html=True)
    st.markdown("<div class='login-card'>", unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["Login", "Register"])

    with tab_login:
        st.subheader("Admin Login")
        email = st.text_input("Email", key="login_email", placeholder="you@example.com")
        password = st.text_input("Password", type="password", key="login_password")
        if st.button("Login", key="login_btn"):
            if not db.is_valid_email(email):
                st.error("Please enter a valid email address (must contain '@' and a valid domain).")
            else:
                success, admin_row, msg = db.verify_login(email, password)
                if success:
                    st.session_state.logged_in = True
                    st.session_state.admin = admin_row
                    # Load this admin's saved conversation history
                    history = db.get_history(admin_row["email"])
                    st.session_state.messages = [
                        {"role": h["role"], "content": h["message"]} for h in history
                    ]
                    st.rerun()
                else:
                    st.error(msg)

    with tab_register:
        st.subheader("Register New Admin")
        st.caption("Your details are stored in the SQLite `admin` table. Only registered emails can log in.")
        name = st.text_input("Full Name", key="reg_name")
        contact = st.text_input("Contact Detail (phone)", key="reg_contact")
        reg_email = st.text_input("Email", key="reg_email", placeholder="you@example.com")
        reg_password = st.text_input("Password", type="password", key="reg_password")
        address = st.text_input("Address", key="reg_address")
        if st.button("Register", key="register_btn"):
            if not db.is_valid_email(reg_email):
                st.error("Please enter a valid email address (must contain '@' and a valid domain).")
            else:
                success, msg = db.add_admin(name, contact, reg_email, reg_password, address)
                if success:
                    st.success(msg + " You can now log in from the Login tab.")
                else:
                    st.error(msg)

    st.markdown("</div>", unsafe_allow_html=True)
    st.info("Default demo account -> **admin@lict.edu.np** / **admin123**", icon="ℹ️")


# ---------------------------------------------------------------------------
# Chat screen
# ---------------------------------------------------------------------------
def show_chat():
    admin = st.session_state.admin

    with st.sidebar:
        st.markdown("### 🎓 LICT Campus Assistant")
        st.markdown(f"**Logged in as:** {admin['name']}")
        st.markdown(f"📧 {admin['email']}")
        st.markdown("---")

        if st.button("🗑️ Clear conversation"):
            db.clear_history(admin["email"])
            st.session_state.messages = []
            st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.logged_in = False
            st.session_state.admin = None
            st.session_state.messages = []
            st.rerun()

        st.markdown("---")
        st.caption("Ask me about:")
        st.caption("• Courses (BSc CSIT, BCA, BIM, BHM)")
        st.caption("• Faculty & Board of Directors")
        st.caption("• Syllabus, Notices & Events")
        st.caption("• Admissions & Contact Info")

        if not bot.is_ready():
            st.warning(
                "⚠️ Knowledge base not found. Run `python scraper.py` then "
                "`python data_processor.py` to populate it.",
            )

    st.markdown("<h2 style='text-align:center;'>💬 Chat with LICT Campus Assistant</h2>", unsafe_allow_html=True)

    # Greet on first load of a fresh conversation
    if not st.session_state.messages:
        welcome = "👋 Hi! I'm the Lumbini ICT Campus assistant. Ask me anything about courses, admissions, faculty, or notices."
        st.session_state.messages.append({"role": "assistant", "content": welcome})
        db.save_message(admin["email"], "bot", welcome)

    for msg in st.session_state.messages:
        role = "user" if msg["role"] == "user" else "assistant"
        with st.chat_message(role):
            st.markdown(msg["content"])

    user_input = st.chat_input("Type your message...")
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        db.save_message(admin["email"], "user", user_input)
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                reply = bot.get_response(user_input)
            st.markdown(reply)

        st.session_state.messages.append({"role": "assistant", "content": reply})
        db.save_message(admin["email"], "bot", reply)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
if st.session_state.logged_in:
    show_chat()
else:
    show_login()
