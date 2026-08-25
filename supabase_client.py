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
    for sponsored content via fn_get_ads_for_device, reshaped into the
    old resource-card format so the existing UI keeps working. Ad
    impression recording happens once, here, the first time each ad is
    fetched in a session — matching the doc's "record once per render"
    guidance without threading impression-tracking through every caller.
    """
    device_token = st.session_state.get("device_token")
    if not device_token:
        return []
    ads = _rpc("fn_get_ads_for_device", {"p_device_token": device_token, "p_limit": 3})
    if isinstance(ads, dict) and "__error__" in ads:
        return []
    ads = ads or []

    if "_ads_shown" not in st.session_state:
        st.session_state["_ads_shown"] = set()
    for ad in ads:
        if ad["ad_id"] not in st.session_state["_ads_shown"]:
            _rpc("fn_record_ad_impression", {"p_ad_id": ad["ad_id"], "p_device_token": device_token})
            st.session_state["_ads_shown"].add(ad["ad_id"])

    return [
        {
            "id": ad["ad_id"],
            "title": ad.get("title", "Sponsored"),
            "course_code": "Sponsored",
            "file_type": "ad",
            "cta_url": ad.get("cta_url", "#"),
        }
        for ad in ads
    ]


def fetch_saved(student_id: str = "demo-student"):
    """
    No bookmarks table/RPC exists in the real schema. This reads from
    st.session_state instead — a real, working feature, just scoped to
    the current browser session rather than persisted server-side.
    Honest about the limitation rather than silently returning nothing.
    """
    return st.session_state.get("_session_bookmarks", [])


def save_bookmark(resource: dict):
    """Session-local save — see fetch_saved()'s docstring."""
    saved = st.session_state.get("_session_bookmarks", [])
    if not any(r["id"] == resource["id"] for r in saved):
        saved.append(resource)
    st.session_state["_session_bookmarks"] = saved


def fetch_resource(resource_id: str):
    """
    Old signature fetched one resource by id for the Viewer screen. The
    real schema's links don't support a standalone by-id lookup outside
    a node context, so this checks session state first (covers the
    Home-feed-ad and Saved-list paths, which already hold the full
    object) and falls back to a placeholder shape if the id is unknown
    — matching the old function's graceful-fallback behavior.
    """
    for bucket_key in ("_last_opened_resource", "_session_bookmarks"):
        bucket = st.session_state.get(bucket_key)
        if isinstance(bucket, dict) and bucket.get("id") == resource_id:
            return bucket
        if isinstance(bucket, list):
            for r in bucket:
                if r["id"] == resource_id:
                    return r
    return {"id": resource_id, "title": "Resource", "course_code": "—", "file_type": "link"}


def search_courses(query: str):
    """
    Old signature searched courses by name. Real search covers the
    whole tree (nodes AND links) via fn_search_tree — this filters the
    combined results down to node-type hits only and reshapes them to
    the old {id, code, name} card format, so course-style search
    results keep working; link-type hits are available via the real
    search_tree() below for screens that want the full picture.
    """
    if not query:
        return []
    result = _rpc("fn_search_tree", {"search_query": query, "result_limit": 25})
    if isinstance(result, dict) and "__error__" in result:
        return []
    node_hits = [r for r in (result or []) if r.get("result_type") == "node"]
    return [{"id": r["id"], "code": r.get("node_path", "")[:12], "name": r.get("title", "")} for r in node_hits]


# ---------------------------------------------------------------------
# Real-schema functions, exposed directly for screens that need the
# actual tree/link shape rather than the old-format shims above.
# ---------------------------------------------------------------------

def fetch_children_as_resources(node_id: str):
    """
    Used by Course Detail: if the node has children, return them
    reshaped as course-cards to keep drilling; if it's a leaf, return
    its links reshaped as resource-cards. Course Detail's existing
    logic already branches on "is this a folder or a resource list" —
    this just gives it real data to branch on instead of a flat filter.
    """
    children = _fetch_child_nodes(node_id)
    if children:
        return "nodes", [_node_to_course_shape(n) for n in children]
    node = _fetch_node(node_id)
    node_name = node.get("name", "") if node else ""
    links = _fetch_unit_links(node_id)
    return "links", [_link_to_resource_shape(link, node_name) for link in links]
