# Facebook Auto Poster - WSL User Manual

Welcome! This guide is specifically designed for running the Auto Poster on **Windows Subsystem for Linux (Ubuntu)**.

## 📋 Prerequisites

1. **Open WSL**:
   - Press `Windows Key`, type `Ubuntu`, and press Enter.
   - You should see a terminal window.

2. **Install System Requirements**:
   Copy and paste this command into your terminal to ensure you have Python and Git:
   ```bash
   sudo apt-get update && sudo apt-get install -y git python3 python3-pip python3-venv
   ```

---

## 🚀 Installation

**1. Clone the Repository**
(Skip this if you already have the files)
```bash
git clone <YOUR_REPO_URL_HERE>
cd facebook-group-autoposter
```

**2. Run the Setup Script**
This script will create a virtual environment and install all necessary libraries.
```bash
chmod +x setup.sh run.sh
./setup.sh
```

---

## ⚙️ Configuration

**1. Get your Access Token**
- You need a **Page Access Token** from Facebook.

**2. Edit the Configuration File**
```bash
nano .env
```
- Delete `REPLACE_ME`.
- Paste your token after `FACEBOOK_ACCESS_TOKEN=`.
- **To Save**: Press `Ctrl + O`, then `Enter`.
- **To Exit**: Press `Ctrl + X`.

---

## ▶️ Running the Bot

Start the visual dashboard with one command:
```bash
./run.sh
```

- The terminal will show a **Local URL** (usually `http://localhost:8501`).
- Open your Windows Web Browser (Chrome/Edge) and visit that URL.
- Use the Dashboard to upload your image and start posting!

---

## ❓ Troubleshooting

- **"Command not found"**: Ensure you ran the `sudo apt-get install` command in Prerequisites.
- **Browser doesn't open**: Manually copy the `http://localhost:8501` link from the terminal to your browser.
- **Token Error**: Ensure your token has `publish_to_groups` permissions.
