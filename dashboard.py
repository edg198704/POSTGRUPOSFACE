import streamlit as st
import os
import tempfile
import time
from dotenv import load_dotenv
from facebook_client import FacebookClient

# Page Config
st.set_page_config(page_title="FB Auto Poster", page_icon="wb", layout="wide")

# Load Env
load_dotenv()
default_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

st.title("🤖 Facebook Group Auto-Poster")
st.markdown("### Control Panel (WSL Edition)")

# Sidebar
st.sidebar.header("Configuration")
token = st.sidebar.text_input("Page Access Token", value=default_token, type="password")

if "preview_mode" not in st.session_state:
    st.session_state.preview_mode = False

# Main Layout
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Create Post")
    uploaded_files = st.file_uploader("Upload Images", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
    caption = st.text_area("Post Caption", height=150, placeholder="Write your message here...")
    
    if st.button("Generate Preview", type="primary"):
        if not uploaded_files:
            st.error("Please upload at least one image.")
        else:
            st.session_state.preview_mode = True

    if st.session_state.preview_mode:
        st.divider()
        st.info("👀 PREVIEW MODE: Review your post below.")
        st.markdown(f"**Caption:**\n{caption}")
        
        # Display Image Grid
        cols = st.columns(3)
        for i, img in enumerate(uploaded_files):
            cols[i % 3].image(img, use_container_width=True)
            
        if st.button("✅ CONFIRM & BLAST", type="primary"):
            st.session_state.start_posting = True

with col2:
    st.subheader("2. Live Logs")
    log_area = st.empty()
    logs = []

    def log(message):
        timestamp = time.strftime("%H:%M:%S")
        logs.append(f"[{timestamp}] {message}")
        if len(logs) > 20: logs.pop(0)
        log_area.code("\n".join(logs), language="text")

# Logic Execution
if st.session_state.get("start_posting"):
    st.session_state.start_posting = False  # Reset trigger
    st.session_state.preview_mode = False   # Reset preview
    
    if not token or token == "REPLACE_ME":
        st.error("❌ Error: Access Token is missing.")
    else:
        # Save temp files
        temp_paths = []
        for uploaded_file in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uploaded_file.getbuffer())
                temp_paths.append(tmp.name)

        try:
            client = FacebookClient(token)
            
            log("🔐 Validating Token...")
            try:
                me = client.validate_token()
                log(f"✅ Authenticated as: {me.get('name')}")
            except Exception as e:
                log(f"⚠️ Token issue: {e}. Trying cookies for groups...")

            log("🔍 Fetching Groups...")
            groups = client.get_groups()
            log(f"✅ Found {len(groups)} groups.")
            
            if not groups:
                st.warning("⚠️ No groups found.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, group in enumerate(groups):
                    status_text.text(f"Posting to: {group['name']}...")
                    log(f"bw Posting to: {group['name']}...")
                    
                    try:
                        client.post_images(group['id'], temp_paths, caption)
                        log(f"✅ Success: {group['name']}")
                    except Exception as e:
                        log(f"❌ Failed: {group['name']} - {e}")
                    
                    progress_bar.progress((i + 1) / len(groups))
                    
                    if i < len(groups) - 1:
                        log("⏳ Waiting 30-60s...")
                        client.sleep_random(30, 60)
                
                st.success("🎉 All posts completed!")
                
        except Exception as e:
            st.error(f"Critical Error: {str(e)}")
        finally:
            for p in temp_paths:
                if os.path.exists(p):
                    os.remove(p)
