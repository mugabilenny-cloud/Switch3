import streamlit as st
from supabase_client import fetch_children_as_resources
from ui_components import inject_base_css, resource_card, bottom_nav

st.set_page_config(page_title="Course | Switch", page_icon="🟠", layout="centered", initial_sidebar_state="collapsed")
inject_base_css()

course = st.session_state.get("active_course", {"code": "—", "name": "Unknown course"})

if st.button("← Back"):
    st.switch_page("pages/1_Home.py")

st.markdown(f"### {course.get('code')}")
st.caption(course.get("name", ""))

st.divider()

# The real tree is 8 levels deep — a node here may hold more nodes
# (keep drilling) or, at the bottom, real links (show them). The old
# version assumed every course had a flat resource list one click away;
# that assumption doesn't hold against a real multi-level tree, so this
# branches instead of flattening.
kind, items = fetch_children_as_resources(course.get("id"))

if kind == "nodes":
    st.markdown("#### Browse further")
    for node in items:
        with st.container():
            st.markdown(
                f"""<div class="card"><div class="card-title">{node['code']} — {node['name']}</div></div>""",
                unsafe_allow_html=True,
            )
            if st.button("Open", key=f"drill_{node['id']}", use_container_width=True):
                st.session_state["active_course"] = node
                st.rerun()
else:
    st.markdown("#### Resources")
    if not items:
        st.info("No links added here yet.")
    for resource in items:
        resource_card(resource, key_prefix="coursedetail")

st.write("")
bottom_nav(active="My Courses")
