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

st.title("🤖 Facebook Group Auto-Poster")
st.markdown("### Control Panel (CSV Mode)")

# --- STEP 1: LOAD GROUPS FROM CSV ---
st.subheader("1. Target Groups (Source: groups.csv)")

def load_csv():
    if os.path.exists(CSV_FILE):
        try:
            df = pd.read_csv(CSV_FILE)
            # Normalize Select column
            if 'Select' not in df.columns:
                df['Select'] = False
            else:
                # Handle string 'true'/'false' or booleans
                df['Select'] = df['Select'].astype(str).str.lower() == 'true'
            return df
        except Exception as e:
            st.error(f"Error reading CSV: {e}")
            return pd.DataFrame(columns=['Select', 'id', 'name'])
    else:
        st.warning(f"⚠️ {CSV_FILE} not found. Please create it with columns: Select,id,name")
        return pd.DataFrame(columns=['Select', 'id', 'name'])

# Initialize session state
if 'groups_df' not in st.session_state:
    st.session_state.groups_df = load_csv()

# Reload Button
if st.button("qc Reload CSV"):
    st.session_state.groups_df = load_csv()
    st.rerun()

# Editor
if not st.session_state.groups_df.empty:
    edited_df = st.data_editor(
        st.session_state.groups_df,
        column_config={
            "Select": st.column_config.CheckboxColumn("Post?", required=True),
            "id": st.column_config.TextColumn("Group ID", disabled=True),
            "name": st.column_config.TextColumn("Group Name", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        key="group_editor"
    )
    
    # Save changes back to CSV
    if not edited_df.equals(st.session_state.groups_df):
        st.session_state.groups_df = edited_df
        save_df = edited_df.copy()
        save_df['Select'] = save_df['Select'].apply(lambda x: 'true' if x else 'false')
        save_df.to_csv(CSV_FILE, index=False)
        st.toast("CSV Saved!", icon="💾")

    # Filter for execution
    selected_groups = edited_df[edited_df['Select'] == True].to_dict('records')
    st.caption(f"✅ Selected: {len(selected_groups)} groups")
else:
    selected_groups = []

st.divider()

# --- STEP 2: CONTENT ---
st.subheader("2. Post Content")
caption = st.text_area("Message", height=150, placeholder="Type your message here...")

if st.button("🚀 Start Posting", type="primary", disabled=len(selected_groups)==0 or not caption):
    st.session_state.running = True

# --- STEP 3: EXECUTION ---
if st.session_state.get('running'):
    st.divider()
    st.subheader("3. Execution Log")
    log_container = st.empty()
    progress_bar = st.progress(0)
    logs = []

    def add_log(msg):
        logs.append(f"[{time.strftime('%H:%M:%S')}] {msg}")
        log_container.code("\n".join(logs[-10:])) # Show last 10 lines

    try:
        client = FacebookClient(access_token="") # Token not used for mbasic
        total = len(selected_groups)
        
        for i, group in enumerate(selected_groups):
            add_log(f"bw Processing: {group.get('name', 'Unknown')} ({group['id']})")
            try:
                client.post_via_mbasic(str(group['id']), caption)
                add_log(f"✅ Posted to {group.get('name')}")
            except Exception as e:
                add_log(f"❌ Failed: {e}")
            
            progress_bar.progress((i + 1) / total)
            
            if i < total - 1:
                sleep_time = client.get_random_sleep()
                add_log(f"zk Sleeping {sleep_time}s...")
                time.sleep(sleep_time)
        
        st.success("Done!")
        st.session_state.running = False
        
    except Exception as e:
        st.error(f"Critical Error: {e}")
        st.session_state.running = False
