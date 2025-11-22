import streamlit as st
import pandas as pd
import os
import time
from dotenv import load_dotenv
from facebook_client import FacebookClient

# 3. FIX SYNTAX ERROR (Ensuring correct import)
load_dotenv()

st.set_page_config(page_title="FB Auto Poster", page_icon="wb", layout="wide")

st.title="🤖 Facebook Group Auto-Poster (CSV Mode)"
st.markdown("### Control Panel")

# --- CONFIGURATION ---
st.sidebar.header="Configuration"
# We still initialize the client for cookie loading, even if we don't use the API token for fetching groups
client = FacebookClient()

# --- STEP 1: LOAD GROUPS FROM CSV ---
st.subheader("1. Target Groups (Source: groups.csv)")

csv_file = "groups.csv"
if not os.path.exists(csv_file):
    st.error(f"❌ File '{csv_file}' not found. Please create it with columns: Select,id,name")
    st.stop()

try:
    # Load CSV
    df = pd.read_csv(csv_file)
    # Ensure 'Select' is boolean for the checkbox UI
    if 'Select' in df.columns:
        df['Select'] = df['Select'].astype(bool)
    else:
        df['Select'] = True
    
    # Display Data Editor
    edited_df = st.data_editor(
        df,
        column_config={
            "Select": st.column_config.CheckboxColumn("Post?", help="Check to post to this group", required=True),
            "id": st.column_config.TextColumn("Group ID", disabled=True),
            "name": st.column_config.TextColumn("Group Name", disabled=True),
        },
        hide_index=True,
        use_container_width=True,
        height=300,
        key="groups_editor"
    )
    
    # Save selection state back to CSV (Optional UX improvement)
    # edited_df.to_csv(csv_file, index=False)
    
    selected_groups = edited_df[edited_df["Select"]].to_dict('records')
    st.caption(f"✅ Target: {len(selected_groups)} groups selected.")

except Exception as e:
    st.error(f"Error reading CSV: {e}")
    st.stop()

st.divider()

# --- STEP 2: CONTENT ---
st.subheader("2. Create Content")
caption = st.text_area("Post Caption", height=150, placeholder="Write your message here...")
st.info("ℹ️ Note: mbasic mode currently supports text-only payloads to ensure high success rates.")

if st.button("🚀 CONFIRM & BLAST", type="primary"):
    if not selected_groups:
        st.warning("Please select at least one group.")
    elif not caption:
        st.warning("Please enter a caption.")
    else:
        st.divider()
        st.subheader("3. Live Execution Log")
        log_area = st.empty()
        progress_bar = st.progress(0)
        logs = []

        def log(message):
            timestamp = time.strftime("%H:%M:%S")
            logs.append(f"[{timestamp}] {message}")
            if len(logs) > 15: logs.pop(0)
            log_area.markdown("  \n".join(logs))

        total = len(selected_groups)
        for i, group in enumerate(selected_groups):
            log(f"bw Posting to: {group['name']}...")
            try:
                # 2. IMPLEMENT MBASIC POSTING CALL
                result_url = client.post_via_mbasic(str(group['id']), caption)
                if "view=permalink" in result_url or "groups" in result_url:
                    log(f"✅ Success: {group['name']}")
                else:
                    log(f"❓ Unknown Result: {result_url}")
            except Exception as e:
                log(f"❌ Failed: {group['name']} - {str(e)}")
            
            progress_bar.progress((i + 1) / total)
            
            if i < total - 1:
                time.sleep(5) # Polite delay
        
        st.success("🎉 Batch Operation Complete!")
