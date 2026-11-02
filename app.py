import streamlit as st
from stemmate.core import SessionPlanService, ConflictResolver, SyncCoordinator, AccessGuard, SessionPlan, SyncQueueItem, RemoteSyncGateway

st.set_page_config(page_title="STEMMate Namibia - A4 Prototype", layout="centered", initial_sidebar_state="collapsed")

# Custom CSS matching Figma Design System (Teal theme & clean card layout)
st.markdown("""
<style>
    .stApp {
        background-color: #F8F9FA;
        font-family: 'Arial', sans-serif;
    }
    .stemmate-header {
        background-color: #0B5D6B;
        color: white;
        padding: 12px 20px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
    }
    .badge-online {
        background-color: #2E7D32;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .badge-offline {
        background-color: #C62828;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: bold;
    }
    .evaluator-panel {
        background-color: #FBEED9;
        border: 1px solid #E0A96D;
        padding: 12px;
        border-radius: 8px;
        margin-top: 25px;
    }
</style>
""", unsafe_allow_html=True)

# Initialize Core Services
if "guard" not in st.session_state:
    st.session_state.guard = AccessGuard()
if "coordinator" not in st.session_state:
    st.session_state.coordinator = SyncCoordinator()
if "online" not in st.session_state:
    st.session_state.online = True
if "storage_full" not in st.session_state:
    st.session_state.storage_full = False

# Header
status_html = '<span class="badge-online">🟢 Online</span>' if st.session_state.online else '<span class="badge-offline">🔴 Offline</span>'
st.markdown(f"""
<div class="stemmate-header">
    <div><strong>STEMMate Namibia</strong> | Low-Resource STEM Platform</div>
    <div>{status_html}</div>
</div>
""", unsafe_allow_html=True)

# Tabs matching Figma Screens
tab_auth, tab_wf1, tab_wf2, tab_wf3 = st.tabs([
    "S01 Sign In", 
    "WF1 Find & Save", 
    "WF2 Plan Editor", 
    "WF3 Outbox & Sync"
])

# S01: Sign In
with tab_auth:
    st.subheader("S01 Sign In on Shared Device (SR-01)")
    profile = st.selectbox("Select Profile", ["Facilitator A (Primary)", "Volunteer B (Shared Device)"])
    pin = st.text_input("Enter 4-Digit PIN", type="password", value="1234")
    
    if st.button("Unlock Profile"):
        if st.session_state.guard.signIn("prince_nde", "secure_pass"):
            st.success(f"Welcome, {profile}! Local profile storage partition unlocked.")
        else:
            st.error("Invalid PIN. Access locked after 5 failed attempts.")

# WF1: Find & Save Activity
with tab_wf1:
    st.subheader("S04 Activity Detail (FR-01, FR-02)")
    st.info("📚 Activity: Grade 8 Physics - Simple Circuits")
    st.write("📦 **Download Size:** ~2.4 MB (Data-Saver mode optimized)")
    
    if st.button("Save Activity for Offline Use"):
        if not st.session_state.online:
            st.error("Cannot save while offline. Connect to network or retry.")
        elif st.session_state.storage_full:
            st.error("Not enough device space (Storage Full). Free up space to continue.")
        else:
            st.success("Saved on this device! Ready for offline lesson planning.")

# WF2: Plan Editor
with tab_wf2:
    st.subheader("S06 Session Plan Editor (FR-03, PR-01)")
    plan_title = st.text_input("Session Title", value="Simple Circuits Practical")
    plan_notes = st.text_area("Inclusion Prompts & Notes", value="Group students into pairs. Ensure all learners have safety gloves.")
    
    st.caption("💾 Status: *Draft saved locally on this device at 12:45 PM*")
    
    if st.button("Mark Ready and Queue for Sync"):
        service = SessionPlanService()
        plan = SessionPlan(title=plan_title, content=plan_notes)
        try:
            if "081" in plan_notes or "@" in plan_notes:
                st.error("PR-01 Privacy Guard: Learner phone numbers or emails detected. Please remove personal identifiers.")
            elif service.validate(plan):
                st.success("Plan validated! Added to Sync Outbox (Status: QUEUED).")
        except ValueError as e:
            st.error(f"Validation Error: {e}")

# WF3: Outbox & Sync
with tab_wf3:
    st.subheader("S07/S08 Outbox & Semantic Conflict Resolver (FR-05, FR-07)")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("### Sync Outbox")
        item = SyncQueueItem(id=101, data={"title": plan_title, "notes": plan_notes})
        
        if st.button("Flush Sync Queue"):
            if not st.session_state.online:
                st.warning("Queued: Waiting for network connection...")
            else:
                st.session_state.coordinator.sync_item(item)
                if item.status == "RETRY_SCHEDULED":
                    st.error(f"Upload Failed (503 Service Unavailable). Retry #{item.retry_count} scheduled with backoff.")
                else:
                    st.success("Synced successfully with Regional Server!")

    with col2:
        st.markdown("### S08 Conflict Resolver")
        local_v = st.text_input("Local Step", value="Step A: Connect LED to Battery")
        server_v = st.text_input("Server Step", value="Step B: Add Switch to Circuit")
        
        if st.button("Resolve Field Conflict"):
            resolver = ConflictResolver()
            res = resolver.merge({"steps": [local_v]}, {"steps": [server_v]})
            if res["status"] == "MERGED":
                st.success(f"Merged Result: {res['steps']}")
            else:
                st.error("Conflict Flagged for Manual Review!")

# Bottom Evaluator Test Controls
st.markdown("---")
with st.expander("🛠️ Evaluator Test Controls (Simulate Conditions)", expanded=True):
    st.caption("Use these toggles to simulate failure states live during your video recording:")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.session_state.online = st.toggle("Network Connected", value=st.session_state.online)
    with c2:
        st.session_state.storage_full = st.toggle("Simulate Storage Full", value=st.session_state.storage_full)
    with c3:
        sim_503 = st.toggle("Simulate Gateway 503")
        if sim_503:
            RemoteSyncGateway.send = lambda item: (_ for _ in ()).throw(Exception("503 Service Unavailable"))
        else:
            RemoteSyncGateway.send = lambda item: None
