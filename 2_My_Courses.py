import streamlit as st
from supabase_client import fetch_active_courses
from ui_components import inject_base_css, bottom_nav, wordmark

st.set_page_config(page_title="My Courses | Switch", page_icon="🟠", layout="centered", initial_sidebar_state="collapsed")
inject_base_css()

wordmark(size="1.1rem")
st.markdown("### My Courses")
st.caption("Browse into your course tree.")

courses = fetch_active_courses()
for course in courses:
    count = course.get('resource_count')
    count_label = f"{count} resources" if count is not None else "Tap to browse"
    with st.container():
        st.markdown(
            f"""
            <div class="card">
                <div class="card-title">{course['code']} — {course['name']}</div>
                <div class="card-meta">{count_label}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if st.button("View resources", key=f"mycourse_{course['id']}", use_container_width=True):
            st.session_state["active_course"] = course
            st.switch_page("pages/3_Course_Detail.py")

st.write("")
bottom_nav(active="My Courses")
