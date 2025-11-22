import streamlit as st
import os
import tempfile
import time
from dotenv import load_dotenv
from facebook_client import FacebookClient

# Page Config
st.set_page_config(page_title="FB Auto Poster", page_icon="wb", layout="wide")
load_dotenv()

# State Initialization
if 'groups' not in st.session_state:
    st.session_state.groups = []
if 'selected_groups' not in st.session_state:
    st.session_state.selected_groups = []
if 'logs' not in st.session_state:
    st.session_state.logs = []

def log(message):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state.logs.append(f"[{timestamp}] {message}")

# Sidebar
st.sidebar.header("Configuration")
default_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")
token = st.sidebar.text_input("Page Access Token", value=default_token, type="password")
st.sidebar.info("ℹ️ If the API fails (Error 400), the bot will automatically switch to Cookie Scraping using config/cookies.json.")

st.title("🤖 Facebook Group Auto-Poster")

# Layout
col_left, col_right = st.columns([2, 1])

with col_left:
    st.markdown("### 1. Prepare Content")
    uploaded_files = st.file_uploader("Upload Images (Multi-Photo Supported)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
    caption = st.text_area("Post Caption", height=120, placeholder="Write your message here...")

    st.markdown("### 2. Select Groups")
    
    # Fetch Button
    if st.button("🔄 Load Groups"):
        if not token:
            st.error("Please enter an Access Token first.")
        else:
            try:
                client = FacebookClient(token)
                with st.spinner("Fetching groups (API + Cookie Fallback)..."):
                    st.session_state.groups = client.get_groups()
                if not st.session_state.groups:
                    st.warning("No groups found.")
                else:
                    st.success(f"Found {len(st.session_state.groups)} groups.")
            except Exception as e:
                st.error(f"Error fetching groups: {e}")

    # Selection UI
    if st.session_state.groups:
        # Select All Toggle
        select_all = st.checkbox("Select All Groups", value=True)
        
        group_options = {g['name']: g['id'] for g in st.session_state.groups}
        default_selection = list(group_options.keys()) if select_all else []
        
        selected_names = st.multiselect(
            "Choose groups to post to:",
            options=list(group_options.keys()),
            default=default_selection
        )
        
        # Update selected IDs
        st.session_state.selected_groups = [
            {'name': name, 'id': group_options[name]} 
            for name in selected_names
        ]
        
        st.caption(f"Selected {len(st.session_state.selected_groups)} groups for posting.")

    st.markdown("### 3. Preview & Blast")
    
    # Preview
    if uploaded_files or caption:
        with st.expander("👁️ Preview Post", expanded=True):
            st.markdown(f"**Text:** {caption}")
            if uploaded_files:
                st.image(uploaded_files, width=150, caption=[f.name for f in uploaded_files])
            else:
                st.warning("No images attached.")

    # Post Button
    if st.button("🚀 CONFIRM & POST", type="primary", disabled=not st.session_state.selected_groups):
        if not token:
            st.error("Token missing.")
        else:
            # Save temp files for backend
            temp_paths = []
            for uf in uploaded_files:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                    tmp.write(uf.getbuffer())
                    temp_paths.append(tmp.name)
            
            try:
                client = FacebookClient(token)
                progress_bar = st.progress(0)
                total = len(st.session_state.selected_groups)
                
                for i, group in enumerate(st.session_state.selected_groups):
                    log(f"bw Posting to: {group['name']}...")
                    try:
                        client.post_images(group['id'], temp_paths, caption)
                        log(f"✅ Success: {group['name']}")
                    except Exception as e:
                        log(f"❌ Failed: {group['name']} - {e}")
                    
                    progress_bar.progress((i + 1) / total)
                    
                    if i < total - 1:
                        wait_time = client.sleep_random(30, 60)
                        log(f"⏳ Waiting {wait_time}s...")
                
                st.success("🎉 Batch Posting Completed!")
            except Exception as e:
                st.error(f"Critical Error: {e}")
            finally:
                # Cleanup Temp Files
                for p in temp_paths:
                    if os.path.exists(p): os.remove(p)

with col_right:
    st.markdown("### 📜 Live Logs")
    log_box = st.empty()
    # Render logs
    log_text = "\n".join(st.session_state.logs)
    log_box.text_area("Log Output", log_text, height=600, disabled=True)
