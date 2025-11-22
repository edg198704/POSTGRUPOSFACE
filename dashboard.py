import streamlit as st
import pandas as pd
import os
import time
from dotenv import load_dotenv
from facebook_client import FacebookClient

st.set_page_config(page_title="FB Auto Poster", page_icon="wb", layout="wide")
load_dotenv()

# --- CONFIGURATION ---
CSV_FILE = "groups.csv"

if 'groups_df' not in st.session_state:
    st.session_state.groups_df = None
if 'preview_confirmed' not in st.session_state:
    st.session_state.preview_confirmed = False

st.title("🤖 Facebook Group Auto-Poster")
st.markdown("### Control Panel (CSV Mode)")

st.sidebar.header("Configuration")
token = st.sidebar.text_input("Page Access Token (Optional for mbasic)", value=os.getenv("FACEBOOK_ACCESS_TOKEN", ""), type="password")

# --- STEP 1: LOAD GROUPS FROM CSV ---
st.subheader("1. Target Groups (Source: groups.csv)")

def load_csv():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            # Ensure columns exist
            if 'id' not in df.columns or 'name' not in df.columns:
                st.error("CSV must contain 'id' and 'name' columns.")
                return pd.DataFrame(columns=['Select', 'id', 'name'])
            
            # Normalize Select column
            if 'Select' not in df.columns:
                df['Select'] = False
            else:
                # Robust boolean conversion
                df['Select'] = df['Select'].astype(str).str.lower().map({'true': True, 'false': False, '1': True, '0': False}).fillna(False)
            
            return df
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return pd.DataFrame(columns=['Select', 'id', 'name'])
    else:
        st.error(f"❌ {CSV_FILE} not found! Please create it with columns: Select,id,name")
        return pd.DataFrame(columns=['Select', 'id', 'name'])

col_fetch, col_save = st.columns([1, 4])
with col_fetch:
    if st.button("qc Reload CSV") or st.session_state.groups_df is None:
        st.session_state.groups_df = load_csv()
        # Reset editor state
        if "groups_editor" in st.session_state:
            del st.session_state["groups_editor"]

if st.session_state.groups_df is not None and not st.session_state.groups_df.empty:
    # MASS SELECTION UI
    c1, c2, c3 = st.columns([1, 1, 5])
    with c1:
        if st.button("✅ Select All"):
            st.session_state.groups_df['Select'] = True
            st.rerun()
    with c2:
        if st.button("DW Deselect All"):
            st.session_state.groups_df['Select'] = False
            st.rerun()
    
    # DATA EDITOR
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
        key="groups_editor"
    )
    
    # SAVE CHANGES TO CSV
    if not edited_df.equals(st.session_state.groups_df):
        st.session_state.groups_df = edited_df
        save_df = edited_df.copy()
        # Save as lowercase string 'true'/'false' for consistency
        save_df['Select'] = save_df['Select'].apply(lambda x: 'true' if x else 'false')
        save_df.to_csv(CSV_FILE, index=False)
        st.toast("CSV Updated!", icon="💾")

    # Filter for execution
    selected_groups = edited_df[edited_df["Select"] == True].to_dict('records')
    st.caption(f"✅ Target: {len(selected_groups)} groups selected.")
else:
    selected_groups = []

st.divider()

# --- STEP 2: CONTENT & PREVIEW ---
st.subheader("2. Create Content")
col_input, col_preview = st.columns([1, 1])

with col_input:
    uploaded_files = st.file_uploader("Upload Images (Skipped in mbasic mode)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
    caption = st.text_area("Post Caption", height=150, placeholder="Write your message here...")
    
    if st.button("👁️ Generate Preview"):
        if not selected_groups:
            st.warning("Please select at least one group above.")
        elif not caption:
            st.warning("Please enter a caption.")
        else:
            st.session_state.preview_confirmed = True

with col_preview:
    if st.session_state.preview_confirmed:
        st.info("👇 Safety Preview")
        st.markdown(f"**Summary:** Posting to **{len(selected_groups)}** groups via **mbasic**.")
        st.markdown(f"**Caption:** {caption}")
        if uploaded_files:
            st.warning("⚠️ Note: Images are currently skipped in mbasic cookie mode. Only text will be posted.")
        if st.button("🚀 CONFIRM & BLAST", type="primary"):
            st.session_state.start_posting = True

# --- STEP 3: EXECUTION ---
if st.session_state.get('start_posting'):
    st.divider()
    st.subheader("3. Live Execution Log")
    log_area = st.empty()
    progress_bar = st.progress(0)
    logs = []

    def log(message, link=None):
        timestamp = time.strftime("%H:%M:%S")
        if link:
            logs.append(f"[{timestamp}] {message} -> [Verify]({link})")
        else:
            logs.append(f"[{timestamp}] {message}")
        
        # Keep last 15 logs
        if len(logs) > 15: logs.pop(0)
        log_area.markdown("  \n".join(logs))

    try:
        # Initialize Client
        client = FacebookClient(token if token else "MBASIC_MODE")
        total = len(selected_groups)
        
        for i, group in enumerate(selected_groups):
            log(f"bw Posting to: {group['name']} ({i+1}/{total})...")
            try:
                # USE MBASIC POSTING
                link = client.post_via_mbasic(str(group['id']), caption)
                log(f"✅ Success: {group['name']}", link)
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
