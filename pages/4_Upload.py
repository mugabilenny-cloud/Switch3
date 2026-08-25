import streamlit as st
from ui_components import inject_base_css, bottom_nav

st.set_page_config(page_title="Upload | Switch", page_icon="⬆️", layout="centered", initial_sidebar_state="collapsed")
inject_base_css()

st.markdown("### ⬆️ Upload a Resource")
st.caption("Students browse curated links added by admins — there's no student upload in this app.")

with st.form("upload_form"):
    st.file_uploader("Choose a file", type=["pdf", "ppt", "pptx", "doc", "docx", "txt"])
    st.text_input("Title", placeholder="e.g. Titration Lab Guide")
    st.selectbox("Course", ["PHA 2101", "CSC 2202", "BBA 1104", "LAW 3201"])
    st.selectbox("Resource category", ["Lecture Slides", "Past Paper", "Lab Guide", "My Notes", "Textbook Excerpt"])
    submitted = st.form_submit_button("Upload", use_container_width=True)

if submitted:
    st.info("This form is a UX placeholder. Content is added by admins through a separate authenticated dashboard — students don't have a write path in Switch.")

st.write("")
bottom_nav(active="Upload")
