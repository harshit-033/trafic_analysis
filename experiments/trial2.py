import streamlit as st
import requests

status = requests.get("http://127.0.0.1:8000/status/J1").json()

st.metric("Cars", status["last_counts"]["car"])
st.metric("Bikes", status["last_counts"]["bike"])
st.metric("Status", status["status"])

if st.button("Simulate Failure"):
    requests.post("http://127.0.0.1:8000/simulate-fail?junction=J1")
