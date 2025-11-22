import streamlit as st
import pandas as pd
import os
import tempfile
import time
from dotenv import load_dotenv
from facebook_client import FacebookClient

st.set_page_config(page_title="FB Auto Poster", page_icon="wb", layout="wide")
load_dotenv()
default_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

if 'groups_df' not in st.session_state:
    st.session_state.groups_df = None
if 'preview_confirmed' not in st.session_state:
    st.session_state.preview_confirmed = False

# --- CALLBACKS FOR MASS SELECTION ---
def select_all():
    if st.session_state.groups_df is not None:
        st.session_state.groups_df['Select'] = True

def deselect_all():
    if st.session_state.groups_df is not None:
        st.session_state.groups_df['Select'] = False

st.title="🤖 Facebook Group Auto-Poster"
st.markdown("### Control Panel (WSL Edition)")

st.sidebar.header("Configuration")
token = st.sidebar.text_input("Page Access Token", value=default_token, type="password")

# --- STEP 1: FETCH GROUPS ---
st.subheader("1. Target Groups")
col_fetch, col_status = st.columns([1, 3])
with col_fetch:
    if st.button("🔄 Load Groups"):
        if not token:
            st.error("Token required!")
        else:
            try:
                with st.spinner("Fetching groups (API + Cookie Fallback)..."):
                    client = FacebookClient(token)
                    groups = client.get_groups()
                    if groups:
                        df = pd.DataFrame(groups)
                        df.insert(0, "Select", True)
                        st.session_state.groups_df = df
                        st.success(f"Loaded {len(groups)} groups.")
                    else:
                        st.error("No groups found.")
            except Exception as e:
                st.error(f"Error: {str(e)}")

selected_groups = []
if st.session_state.groups_df is not None:
    # Mass Selection UI
    c1, c2, c3 = st.columns([1, 1, 4])
    with c1:
        st.button("✅ Select All", on_click=select_all, use_container_width=True)
    with c2:
        st.button("UB Deselect All", on_click=deselect_all, use_container_width=True)
    
    # Data Editor
    edited_df = st.data_editor(
        st.session_state.groups_df,
        column_config={
            "Select": st.column_config.CheckboxColumn("Post?", help="Check to post to this group", required=True),
            "id": st.column_config.TextColumn("Group ID", disabled=True),
            "name": st.column_config.TextColumn("Group Name", disabled=True),
        },
        disabled=["id", "name"],
        hide_index=True,
        use_container_width=True,
        height=300,
        key="group_editor" # Key helps maintain state stability
    )
    
    # Sync edits back to session state to persist manual changes
    st.session_state.groups_df = edited_df
    
    selected_groups = edited_df[edited_df["Select"]].to_dict('records')
    st.caption(f"✅ Target: {len(selected_groups)} groups selected.")

st.divider()

# --- STEP 2: CONTENT & PREVIEW ---
st.subheader("2. Create Content")
col_input, col_preview = st.columns([1, 1])

with col_input:
    uploaded_files = st.file_uploader("Upload Images (Multi-Select)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
    caption = st.text_area("Post Caption", height=150, placeholder="Write your message here...")
    
    if st.button("👁️ Generate Preview"):
        if not uploaded_files:
            st.warning("Please upload at least one image.")
        elif not selected_groups:
            st.warning("Please select at least one group above.")
        else:
            st.session_state.preview_confirmed = True

with col_preview:
    if st.session_state.preview_confirmed:
        st.info("👇 Safety Preview")
        st.markdown(f"**Summary:** Posting to **{len(selected_groups)}** groups.")
        st.markdown(f"**Caption:** {caption}")
        st.markdown(f"**Images:** {[f.name for f in uploaded_files]}")
        
        if uploaded_files:
            st.image(uploaded_files, width=150)
        
        st.warning("⚠️ Please confirm details above.")
        if st.button("🚀 CONFIRM & BLAST", type="primary"):
            st.session_state.start_posting = True

# --- STEP 3: EXECUTION ---
if st.session_state.get('start_posting'):
    st.divider()
    st.subheader("3. Live Execution Log")
    log_area = st.empty()
    progress_bar = st.progress(0)
    logs = []

    def log(message):
        timestamp = time.strftime("%H:%M:%S")
        logs.append(f"[{timestamp}] {message}")
        if len(logs) > 15: logs.pop(0)
        log_area.code("\n".join(logs), language="text")

    temp_paths = []
    for uf in uploaded_files:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
            tmp.write(uf.getbuffer())
            temp_paths.append(tmp.name)

    try:
        client = FacebookClient(token)
        total = len(selected_groups)
        
        for i, group in enumerate(selected_groups):
            log(f"bw Posting to: {group['name']} ({i+1}/{total})...")
            try:
                client.post_images(group['id'], temp_paths, caption)
                log(f"✅ Success: {group['name']}")
            except Exception as e:
                log(f"❌ Failed: {group['name']} - {e}")
            
            progress_bar.progress((i + 1) / total)
            
            if i < total - 1:
                wait_time = client.get_random_sleep()
                log(f"⏳ Sleeping {wait_time}s...")
                time.sleep(wait_time)
        
        st.success("🎉 Batch Operation Complete!")
        st.session_state.preview_confirmed = False
        st.session_state.start_posting = False

    except Exception as e:
        st.error(f"Critical Error: {str(e)}")
    finally:
        for p in temp_paths:
            if os.path.exists(p): os.remove(p)
