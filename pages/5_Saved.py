import streamlit as st
from supabase_client import fetch_saved
from ui_components import inject_base_css, resource_card, bottom_nav

st.set_page_config(page_title="Saved | Switch", page_icon="🔖", layout="centered", initial_sidebar_state="collapsed")
inject_base_css()

st.markdown("### 🔖 Saved")
st.caption("Bookmarked notes for quick review.")

saved = fetch_saved()
if not saved:
    st.info("Nothing saved yet. Tap 🔖 Save on any resource card to add it here.")
else:
    for resource in saved:
        resource_card(resource, key_prefix="saved")

st.write("")
bottom_nav(active="Saved")
