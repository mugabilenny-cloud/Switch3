import streamlit as st
from supabase_client import fetch_active_courses, fetch_recently_viewed, fetch_feed, search_courses
from ui_components import inject_base_css, resource_card, bottom_nav, wordmark

st.set_page_config(page_title="Home | Switch", page_icon="🟠", layout="centered", initial_sidebar_state="collapsed")
inject_base_css()

# ---- 1. Header & persistent search ----
wordmark()
query = st.text_input(
    "Search",
    placeholder="Search course code, e.g. PHA 2101",
    label_visibility="collapsed",
)
if query:
    results = search_courses(query)
    if results:
        st.caption("Matching courses")
        for course in results:
            if st.button(f"{course['code']} — {course['name']}", key=f"searchres_{course['id']}", use_container_width=True):
                st.session_state["active_course"] = course
                st.switch_page("pages/3_Course_Detail.py")
    else:
        st.caption("No matches yet.")

st.divider()

# ---- 2. Active Semester fast-lane ----
st.markdown("#### My Active Courses")
courses = fetch_active_courses()
chip_cols = st.columns(2)
for i, course in enumerate(courses):
    with chip_cols[i % 2]:
        if st.button(f"{course['code']}", key=f"chip_{course['id']}", use_container_width=True):
            st.session_state["active_course"] = course
            st.switch_page("pages/3_Course_Detail.py")

recent = fetch_recently_viewed()
if recent:
    st.markdown("###### Pick up where you left off")
    for r in recent:
        cols = st.columns([4, 1])
        cols[0].write(f"{r['title']} · {r['course_code']}")
        if cols[1].button("Open", key=f"recent_{r['id']}"):
            st.session_state["active_resource_id"] = r["id"]
            st.session_state["_last_opened_resource"] = r
            st.switch_page("pages/6_Viewer.py")

st.divider()

# ---- 3. What's New on Campus feed ----
st.markdown("#### What's New on Campus")
feed = fetch_feed()
for resource in feed:
    resource_card(resource, key_prefix="feed")

st.write("")
bottom_nav(active="Home")
