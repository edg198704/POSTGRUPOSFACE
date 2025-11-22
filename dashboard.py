import streamlit as st
import os
import tempfile
import time
from dotenv import load_dotenv
from facebook_client import FacebookClient

st.set_page_config(page_title="FB Auto Poster", page_icon="wb", layout="wide")
load_dotenv()
default_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

if 'preview_confirmed' not in st.session_state:
    st.session_state.preview_confirmed = False

st.title("🤖 Facebook Group Auto-Poster")
st.markdown("### Control Panel (WSL Edition)")

st.sidebar.header("Configuration")
token = st.sidebar.text_input("Page Access Token", value=default_token, type="password")

col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Create Post")
    # Multi-Photo Support Input
    uploaded_files = st.file_uploader("Upload Images", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
    caption = st.text_area("Post Caption", height=150, placeholder="Write your message here...")
    
    # Safety Preview Logic
    if st.button("👁️ Preview Post"):
        if not uploaded_files:
            st.error("Please upload at least one image.")
        else:
            st.session_state.preview_confirmed = True

    if st.session_state.preview_confirmed:
        st.info("👇 Review your post below. Click 'Confirm & Blast' to start.")
        st.markdown(f"**Caption:** {caption}")
        # Display Grid of Images
        st.image(uploaded_files, width=150, caption=[f.name for f in uploaded_files])
        
        if st.button("🚀 CONFIRM & BLAST", type="primary"):
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

if st.session_state.get('start_posting'):
    if not token:
        st.error("❌ Error: Access Token is missing.")
    else:
        temp_paths = []
        # Save temp files for the backend to read
        for uf in uploaded_files:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(uf.getbuffer())
                temp_paths.append(tmp.name)

        try:
            client = FacebookClient(token)
            log("🔐 Validating Token...")
            me = client.validate_token()
            log(f"✅ Authenticated as: {me.get('name')}")
            
            log("🔍 Fetching Groups...")
            groups = client.get_groups()
            log(f"✅ Found {len(groups)} groups.")
            
            progress_bar = st.progress(0)
            
            for i, group in enumerate(groups):
                log(f"bw Posting to: {group['name']}...")
                try:
                    # Multi-Photo Logic Call
                    client.post_images(group['id'], temp_paths, caption)
                    log(f"✅ Success: {group['name']}")
                except Exception as e:
                    log(f"❌ Failed: {group['name']} - {e}")
                
                progress_bar.progress((i + 1) / len(groups))
                if i < len(groups) - 1:
                    log("⏳ Waiting 30-60s...")
                    client.sleep_random(30, 60)
            
            st.success("🎉 All posts completed!")
            st.session_state.preview_confirmed = False
            st.session_state.start_posting = False
                
        except Exception as e:
            st.error(f"Critical Error: {str(e)}")
        finally:
            # Cleanup Temp Files
            for p in temp_paths:
                if os.path.exists(p): os.remove(p)
