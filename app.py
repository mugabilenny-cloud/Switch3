import streamlit as st
from supabase_client import get_or_create_device_token, register_device

st.set_page_config(
    page_title="Switch",
    page_icon="🟠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    '<link rel="manifest" href="assets/manifest.json"><meta name="theme-color" content="#E85D2C">',
    unsafe_allow_html=True,
)

# Device bootstrap — required by the real schema's device-scoped RPCs
# (ads, notifications). Invisible to the user; not a UX change.
device_token = get_or_create_device_token()
st.session_state["device_token"] = device_token
register_device(device_token, home_node_id=st.session_state.get("home_node_id"))

st.switch_page("pages/1_Home.py")
