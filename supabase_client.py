"""
Supabase data layer — real schema (nodes/links/RPCs), shaped to match the
function signatures the ORIGINAL six-screen UX (Home / My Courses /
Course Detail / Upload / Saved / Viewer) already calls. Per
DATABASE_INTEGRATION.md:

- Direct `select` is allowed ONLY on `nodes` and `links`.
- Everything else (ads, notifications, student_devices, impressions,
  receipts) goes through the listed RPC functions, never a direct
  .from() call.
- No student login — a random device_token, generated once and carried
  in the URL's query params (Streamlit has no localStorage API),
  identifies the browser to device-scoped RPCs.
- The Application has NO write path to nodes/links, ever. Two functions
  below (bookmark/upload helpers) are explicitly session-local, not
  database writes — see their docstrings.
"""

import os
import uuid
import requests
import streamlit as st

SUPABASE_URL = st.secrets.get("SUPABASE_URL", os.environ.get("SUPABASE_URL", ""))
SUPABASE_ANON_KEY = st.secrets.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_ANON_KEY", ""))

_HEADERS = {
    "apikey": SUPABASE_ANON_KEY,
    "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
    "Content-Type": "application/json",
}


def _configured() -> bool:
    return bool(SUPABASE_URL and SUPABASE_ANON_KEY)


def _get(path: str, params: dict | None = None):
    if not _configured():
        return None
    try:
        resp = requests.get(f"{SUPABASE_URL}/rest/v1/{path}", headers=_HEADERS, params=params or {}, timeout=8)
        if resp.status_code == 200:
            return resp.json()
        _record_debug_error(f"GET {path}", params, resp.status_code, resp.text)
        return None
    except requests.RequestException as e:
        _record_debug_error(f"GET {path}", params, None, str(e))
        return None


def _record_debug_error(call: str, payload, status, body):
    """
    Every failed GET/RPC call gets appended here instead of vanishing.
    Nothing reads this by default — it costs nothing when everything
    works. See show_debug_panel() below to surface it in the app when
    diagnosing a silent failure.
    """
    errors = st.session_state.get("_debug_errors", [])
    errors.append({"call": call, "payload": payload, "status": status, "body": body})
    st.session_state["_debug_errors"] = errors[-20:]  # keep it bounded


def show_debug_panel():
    """
    Call this from any page (e.g. at the bottom of Home) to see the last
    20 failed Supabase calls in an expander. Safe to leave in permanently
    — an empty list renders nothing but a collapsed, empty expander.
    """
    errors = st.session_state.get("_debug_errors", [])
    with st.expander(f"🔧 Debug: {len(errors)} failed call(s) this session", expanded=False):
        if not errors:
            st.caption("No failed Supabase calls recorded this session.")
        for e in errors:
            st.code(f"{e['call']}\npayload: {e['payload']}\nstatus: {e['status']}\n{e['body']}", language="text")


def _rpc(fn_name: str, payload: dict):
    if not _configured():
        return None
    try:
        resp = requests.post(f"{SUPABASE_URL}/rest/v1/rpc/{fn_name}", headers=_HEADERS, json=payload, timeout=8)
        if resp.status_code == 200:
            return resp.json()
        _record_debug_error(f"RPC {fn_name}", payload, resp.status_code, resp.text)
        return {"__error__": resp.text, "__status__": resp.status_code}
    except requests.RequestException as e:
        _record_debug_error(f"RPC {fn_name}", payload, None, str(e))
        return {"__error__": str(e)}


# ---------------------------------------------------------------------
# Device identity
# ---------------------------------------------------------------------

def get_or_create_device_token() -> str:
    params = st.query_params
    token = params.get("device")
    if not token:
        token = str(uuid.uuid4())
        st.query_params["device"] = token
    return token


def register_device(device_token: str, home_node_id: str | None = None):
    """
    fn_register_device's real signature (confirmed via
    pg_get_function_identity_arguments) is:
        p_device_token text, p_home_node_id uuid
    with no visible default on p_home_node_id. PostgREST rejects an RPC
    call that omits a parameter without a database-side default, so the
    previous version of this function — which only included
    p_home_node_id in the payload when one was already chosen — was
    silently failing on every call made before a home node was set,
    which is the first launch and most launches after. Passing None
    explicitly (valid for a nullable uuid parameter) fixes this.
    """
    payload = {"p_device_token": device_token, "p_home_node_id": home_node_id}
    return _rpc("fn_register_device", payload)


# ---------------------------------------------------------------------
# Raw tree access (used internally by the shims below)
# ---------------------------------------------------------------------

def _fetch_root_nodes():
    return _get("nodes", {"select": "*", "parent_id": "is.null", "order": "sort_order"}) or []


def _fetch_child_nodes(parent_id: str):
    return _get("nodes", {"select": "*", "parent_id": f"eq.{parent_id}", "order": "sort_order"}) or []


def _fetch_node(node_id: str):
    rows = _get("nodes", {"select": "*", "id": f"eq.{node_id}"})
    return rows[0] if rows else None


def _fetch_unit_links(node_id: str):
    result = _rpc("fn_get_unit_links", {"p_node_id": node_id})
    if isinstance(result, dict) and "__error__" in result:
        return []
    return result or []


def _node_to_course_shape(node: dict) -> dict:
    """
    The old UX's course cards expect {id, code, name, resource_count}.
    The real schema's nodes have {id, name, node_type, parent_id, sort_order}
    with no code and no resource_count. This maps what exists and fills
    the rest with the node's own name so the old cards render sensibly
    without inventing data that isn't in the schema.
    """
    return {
        "id": node["id"],
        "code": node.get("node_type", "").upper()[:4] or "NODE",
        "name": node.get("name", "Untitled"),
        "resource_count": None,  # not tracked in this schema — UI hides it when None
    }


def _link_to_resource_shape(link: dict, node_name: str = "") -> dict:
    """
    The old UX's resource cards expect
    {id, title, course_code, file_type, uploader, uploaded_at, upvotes}.
    Real links have {link_kind, id, url, title, description} — no
    uploader, timestamp, or upvote count exists in this schema (there's
    no crowdsourcing yet, per DATABASE_INTEGRATION.md's scope note).
    Those keys are simply omitted rather than faked; ui_components.py
    already treats them as optional.
    """
    kind_to_filetype = {"youtube": "video", "drive_notes": "note", "drive_questions": "doc"}
    return {
        "id": link.get("id"),
        "title": link.get("title") or link.get("url", "Untitled link"),
        "course_code": node_name,
        "file_type": kind_to_filetype.get(link.get("link_kind"), "link"),
        "url": link.get("url"),
    }


# ---------------------------------------------------------------------
# Shims matching the ORIGINAL app's exact function names/signatures.
# Each is a thin real-schema implementation of what the old placeholder
# function promised, honest about what the real schema can't provide.
# ---------------------------------------------------------------------

def fetch_active_courses(student_id: str = "demo-student"):
    """
    Old signature returned the student's enrolled courses. No enrollment
    table exists in the real schema, so this returns the ROOT of the
    tree instead (top-level universities/faculties) — the closest real
    analog to "the courses available to browse into." If a home node is
    set, its children are returned instead, so the fast-lane reflects
    the student's chosen area.
    """
    home_node_id = st.session_state.get("home_node_id")
    nodes = _fetch_child_nodes(home_node_id) if home_node_id else _fetch_root_nodes()
    return [_node_to_course_shape(n) for n in nodes]


def fetch_recently_viewed(student_id: str = "demo-student"):
    """
    No view_history read is exposed to the Application in
    DATABASE_INTEGRATION.md (no direct table grant, no RPC listed for
    it). Rather than fabricate data, this returns an empty list — the
    Home screen already hides the "Pick up where you left off" section
    when this is empty, so nothing broken renders.
    """
    return []


def fetch_feed(department: str | None = None):
    """
    Old signature powered "What's New on Campus" — a resource feed. No
    such feed/table exists in the real schema. This repurposes the slot
