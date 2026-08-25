"""
Pure UI building blocks. No direct database writes here — Save persists
to session state via supabase_client.save_bookmark(), matching what the
real schema can actually offer (see that function's docstring).
"""

import streamlit as st
from supabase_client import save_bookmark

FILE_TYPE_STYLE = {
    "ppt":  {"color": "#F97316", "label": "PPT",  "icon": "📊"},
    "pdf":  {"color": "#EF4444", "label": "PDF",  "icon": "📄"},
    "note": {"color": "#3B82F6", "label": "NOTE", "icon": "📝"},
    "doc":  {"color": "#3B82F6", "label": "DOC",  "icon": "📃"},
}

DEFAULT_STYLE = {"color": "#6B7280", "label": "FILE", "icon": "📎"}


def inject_base_css():
    st.markdown(
        """
        <style>
        div[data-testid="stAppViewContainer"] > .main { padding-bottom: 5.5rem; }
        .card {
            border: 1px solid #E5E7EB;
            border-radius: 12px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.6rem;
            background: #FFFFFF;
        }
        .card-title { font-weight: 600; font-size: 0.98rem; margin-bottom: 0.15rem; }
        .card-meta { color: #6B7280; font-size: 0.8rem; }
        .type-chip {
            display: inline-block;
            font-size: 0.7rem;
            font-weight: 700;
            padding: 0.1rem 0.5rem;
            border-radius: 6px;
            color: white;
            margin-right: 0.4rem;
        }
        .course-chip {
            display: inline-block;
            border: 1px solid #E85D2C;
            color: #E85D2C;
            border-radius: 999px;
            padding: 0.3rem 0.9rem;
            margin-right: 0.5rem;
            font-weight: 600;
            font-size: 0.85rem;
        }
        .switch-wordmark {
            font-weight: 800;
            letter-spacing: -0.02em;
            color: #E85D2C;
        }
        .switch-wordmark .dot { color: #1A1A2E; }
        .bottom-nav {
            position: fixed;
            bottom: 0; left: 0; right: 0;
            background: #FFFFFF;
            border-top: 1px solid #E5E7EB;
            padding: 0.4rem 0.5rem;
            z-index: 999;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def wordmark(size: str = "1.4rem"):
    """Renders the 'switch.' wordmark — lowercase, bold, trailing dot in ink not orange."""
    st.markdown(
        f'<div class="switch-wordmark" style="font-size:{size};">switch<span class="dot">.</span></div>',
        unsafe_allow_html=True,
    )


def file_type_chip(file_type: str) -> str:
    style = FILE_TYPE_STYLE.get(file_type, DEFAULT_STYLE)
    return f'<span class="type-chip" style="background:{style["color"]}">{style["icon"]} {style["label"]}</span>'


def resource_card(resource: dict, key_prefix: str):
    """Renders one feed/list card. Returns the button-click routing signal, if any."""
    style = FILE_TYPE_STYLE.get(resource.get("file_type"), DEFAULT_STYLE)
    with st.container():
        st.markdown(
            f"""
            <div class="card" style="border-left: 4px solid {style['color']};">
                <div>{file_type_chip(resource.get('file_type', ''))}
                    <span class="card-meta">{resource.get('course_code', '')}</span>
                </div>
                <div class="card-title">{resource.get('title', 'Untitled')}</div>
                <div class="card-meta">
                    {resource.get('uploader', '')}{' · ' if resource.get('uploader') else ''}{resource.get('uploaded_at', '')}
                    {' · ▲ ' + str(resource['upvotes']) if 'upvotes' in resource else ''}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        cols = st.columns([1, 1, 1])
        open_clicked = cols[0].button("Open", key=f"{key_prefix}_open_{resource['id']}", use_container_width=True)
        save_clicked = cols[1].button("🔖 Save", key=f"{key_prefix}_save_{resource['id']}", use_container_width=True)
        share_clicked = cols[2].button("🔗 Share", key=f"{key_prefix}_share_{resource['id']}", use_container_width=True)

        if open_clicked:
            st.session_state["active_resource_id"] = resource["id"]
            st.session_state["_last_opened_resource"] = resource
            st.switch_page("pages/6_Viewer.py")
        if save_clicked:
            save_bookmark(resource)
            st.toast(f"Saved \"{resource.get('title')}\"")
        if share_clicked:
            st.toast("Share link copied (placeholder — wire to real deep-link generation later)")


def bottom_nav(active: str):
    """Renders the fixed bottom tab bar. `active` highlights the current tab."""
    st.markdown('<div class="bottom-nav">', unsafe_allow_html=True)
    cols = st.columns(4)
    tabs = [
        ("Home", "🏠", "pages/1_Home.py"),
        ("My Courses", "📚", "pages/2_My_Courses.py"),
        ("Upload", "⬆️", "pages/4_Upload.py"),
        ("Saved", "🔖", "pages/5_Saved.py"),
    ]
    for col, (label, icon, page) in zip(cols, tabs):
        is_active = label == active
        display = f"**{icon} {label}**" if is_active else f"{icon} {label}"
        if col.button(display, key=f"nav_{label}", use_container_width=True):
            st.switch_page(page)
    st.markdown("</div>", unsafe_allow_html=True)
