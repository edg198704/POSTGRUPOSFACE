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

st.title="🤖 Facebook Group Auto-Poster"
st.markdown("### Control Panel (WSL Edition)")

# Sidebar: Configuration
st.sidebar.header("Configuration")
token = st.sidebar.text_input("Page Access Token", value=default_token, type="password")

if not token or token == "REPLACE_ME":
    st.sidebar.error("⚠️ Invalid Token. Please edit your .env file or paste a token here.")

# Main Area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Create Post")
    uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
    caption = st.text_area("Post Caption", height=150, placeholder="Write your message here...")
    
    start_btn = st.button("🚀 Start Posting", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Live Logs")
    log_area = st.empty()
    logs = []

    def log(message):
        timestamp = time.strftime("%H:%M:%S")
        logs.append(f"[{timestamp}] {message}")
        # Keep only last 20 logs to avoid clutter
        if len(logs) > 20:
            logs.pop(0)
        log_area.code("\n".join(logs), language="text")

# Logic
if start_btn:
    if not token or token == "REPLACE_ME":
        st.error("❌ Error: Access Token is missing.")
    elif not uploaded_file:
        st.error("❌ Error: Please upload an image.")
    else:
        # Use tempfile for safe handling in WSL/Linux
        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            temp_path = tmp_file.name

        try:
            client = FacebookClient(token)
            
            log("🔐 Validating Token...")
            me = client.validate_token()
            log(f"✅ Authenticated as: {me.get('name')} ({me.get('id')})")
            
            log("🔍 Fetching Groups...")
            groups = client.get_groups()
            log(f"✅ Found {len(groups)} groups.")
            
            if not groups:
                st.warning("⚠️ No groups found. Make sure your Page has joined groups.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, group in enumerate(groups):
                    status_text.text(f"Posting to: {group['name']}...")
                    log(f"bw Posting to: {group['name']}...")
                    
                    try:
                        client.post_photo(group['id'], temp_path, caption)
                        log(f"✅ Success: {group['name']}")
                    except Exception as e:
                        log(f"❌ Failed: {group['name']} - {e}")
                    
                    # Update Progress
                    progress_bar.progress((i + 1) / len(groups))
                    
                    # Delay if not last
                    if i < len(groups) - 1:
                        log("⏳ Waiting 30-60s (Rate Limit Safety)...")
                        client.sleep_random(30, 60)
                
                status_text.text("Done!")
                st.success("🎉 All posts completed!")
                
        except Exception as e:
            st.error(f"Critical Error: {str(e)}")
        finally:
            # Cleanup temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
