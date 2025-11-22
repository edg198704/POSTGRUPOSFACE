import streamlit as st
import os
import time
import uuid
from dotenv import load_dotenv
from facebook_client import FacebookClient

# Page Config
st.set_page_config(page_title="FB Auto Poster", page_icon="wb", layout="wide")

# Load Env
load_dotenv()
default_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "")

st.title("🤖 Facebook Group Auto-Poster")
st.markdown("**WSL Edition**: Control your posts from this local dashboard.")

# Sidebar: Configuration
st.sidebar.header("Configuration")
token = st.sidebar.text_input("Page Access Token", value=default_token, type="password")

if token == "REPLACE_ME" or not token:
    st.sidebar.warning("⚠️ Please update your .env file or paste a token here.")

# Main Area
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("1. Create Post")
    uploaded_file = st.file_uploader("Upload Image", type=['jpg', 'png', 'jpeg'])
    caption = st.text_area("Post Caption", height=150, placeholder="Write something amazing...")
    
    start_btn = st.button("🚀 Start Posting", type="primary", use_container_width=True)

with col2:
    st.subheader("2. Live Status")
    status_area = st.empty()
    log_area = st.empty()
    logs = []

    def log(message, level="info"):
        timestamp = time.strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        logs.append(entry)
        # Keep only last 20 logs to avoid clutter
        log_text = "\n".join(logs[-20:])
        log_area.code(log_text, language="text")
        if level == "error":
            st.toast(message, icon="❌")
        elif level == "success":
            st.toast(message, icon="✅")

# Logic
if start_btn:
    if not token or token == "REPLACE_ME":
        st.error("❌ Error: Invalid Access Token.")
    elif not uploaded_file:
        st.error("❌ Error: Please upload an image.")
    else:
        # Create unique temp file
        ext = uploaded_file.name.split('.')[-1]
        temp_filename = f"temp_{uuid.uuid4()}.{ext}"
        
        try:
            with open(temp_filename, "wb") as f:
                f.write(uploaded_file.getbuffer())
            
            client = FacebookClient(token)
            
            status_area.info("🔐 Authenticating...")
            me = client.validate_token()
            log(f"Authenticated as: {me.get('name')} ({me.get('id')})", "success")
            
            status_area.info("🔍 Fetching Groups...")
            groups = client.get_groups()
            log(f"Found {len(groups)} groups.")
            
            if not groups:
                st.warning("⚠️ No groups found. Make sure your Page has joined groups.")
            else:
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                for i, group in enumerate(groups):
                    group_name = group.get('name', 'Unknown Group')
                    status_text.text(f"Posting to: {group_name}...")
                    
                    try:
                        client.post_photo(group['id'], temp_filename, caption)
                        log(f"✅ Posted: {group_name}")
                    except Exception as e:
                        log(f"❌ Failed: {group_name} - {e}", "error")
                    
                    # Update Progress
                    progress_bar.progress((i + 1) / len(groups))
                    
                    # Delay if not last
                    if i < len(groups) - 1:
                        wait_time = 30 # Fixed 30s for safety, or random
                        for s in range(wait_time, 0, -1):
                            status_text.text(f"⏳ Cooling down... {s}s remaining")
                            time.sleep(1)
                
                status_text.text("Done!")
                st.success("🎉 All posts completed!")
                st.balloons()
                
        except Exception as e:
            st.error(f"Critical Error: {str(e)}")
        finally:
            # Cleanup
            if os.path.exists(temp_filename):
                os.remove(temp_filename)
