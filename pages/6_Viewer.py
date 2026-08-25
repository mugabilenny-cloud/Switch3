import streamlit as st
from supabase_client import fetch_resource, save_bookmark
from ui_components import inject_base_css, file_type_chip

st.set_page_config(page_title="Viewer | Switch", page_icon="📄", layout="centered", initial_sidebar_state="collapsed")
inject_base_css()

resource_id = st.session_state.get("active_resource_id")
if not resource_id:
    st.warning("No resource selected.")
    if st.button("← Back to Home"):
        st.switch_page("pages/1_Home.py")
    st.stop()

resource = fetch_resource(resource_id)

top = st.columns([1, 4, 1])
if top[0].button("✕ Close"):
    st.switch_page("pages/1_Home.py")
top[1].markdown(f"**{resource.get('title', 'Resource')}**")
fullscreen = top[2].button("⛶")

st.markdown(file_type_chip(resource.get("file_type", "")), unsafe_allow_html=True)
st.caption(resource.get("course_code", ""))

st.markdown(
    f"""
    <div style="border:1px solid #E5E7EB; border-radius:12px; padding: {"3rem" if fullscreen else "5rem"} 1rem;
                text-align:center; background:#F5F6FA; margin-top: 0.6rem;">
        <div style="font-size:2.5rem;">{'📄' if resource.get('file_type') == 'pdf' else '📊' if resource.get('file_type') == 'ppt' else '📝'}</div>
        <div style="color:#6B7280; margin-top:0.5rem;">
            Inline preview placeholder — this is where the real PDF/slide/text
            renderer mounts. No download forced to open this.
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

cols = st.columns(3)
if cols[0].button("🔖 Save", use_container_width=True):
    save_bookmark(resource)
    st.toast("Saved")
if cols[1].button("🔗 Copy Share Link", use_container_width=True):
    st.toast("Share links aren't available yet — no deep-link scheme exists in this schema.")
cols[2].button("⬇️ Download", use_container_width=True, disabled=True, help="Intentionally de-emphasized per spec — inline viewing is the default.")
