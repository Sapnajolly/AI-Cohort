import streamlit as st
import requests
import uuid
import pandas as pd

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Coverage Chatbot", page_icon="chat")

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "member_id" not in st.session_state:
    st.session_state.member_id = "M1001"

with st.sidebar:
    st.header("Coverage Chatbot")
    st.text_input("Member ID", key="member_id")
    try:
        plans_df = pd.read_csv("data/plans.csv")
        plan_names = plans_df["plan_name"].tolist()
    except Exception:
        plan_names = ["Bronze Basic", "Silver Standard", "Gold Complete", "Platinum Plus"]
    selected_plan = st.selectbox("Plan", plan_names)
    st.caption("Session: " + st.session_state.session_id[:8])
    if st.button("New conversation"):
        st.session_state.session_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

st.title("Coverage Chatbot")

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

user_input = st.chat_input("Ask about your coverage...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.write("Thinking...")
        try:
            payload = {
                "session_id": st.session_state.session_id,
                "member_id": st.session_state.member_id,
                "message": "[" + selected_plan + "] " + user_input,
            }
            resp = requests.post(API_URL + "/chat", json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            answer = data.get("response", "No response from backend.")
        except requests.exceptions.RequestException as e:
            answer = "Error reaching chatbot backend: " + str(e)
        placeholder.write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})
