import streamlit as st
import requests
import uuid
import json
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
        full_text = ""
        try:
            payload = {
                "session_id": st.session_state.session_id,
                "member_id": st.session_state.member_id,
                "message": "[" + selected_plan + "] " + user_input,
            }
            with requests.post(API_URL + "/chat", json=payload, stream=True, timeout=30) as resp:
                resp.raise_for_status()
                first_token_received = False
                for line in resp.iter_lines(decode_unicode=True):
                    if not line or not line.startswith("data:"):
                        continue
                    raw = line[len("data:"):].strip()
                    try:
                        event = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if "error" in event:
                        full_text = "Error from backend: " + event["error"]
                        placeholder.write(full_text)
                        break
                    if event.get("done"):
                        break
                    token = event.get("token", "")
                    full_text += token
                    first_token_received = True
                    placeholder.write(full_text)
                if not first_token_received and not full_text:
                    full_text = "No response received before stream ended."
                    placeholder.write(full_text)
        except requests.exceptions.Timeout:
            full_text = "Error: request timed out waiting for the backend to respond."
            placeholder.write(full_text)
        except requests.exceptions.RequestException as e:
            full_text = "Error reaching chatbot backend: " + str(e)
            placeholder.write(full_text)
        st.session_state.messages.append({"role": "assistant", "content": full_text})
