const { ipcRenderer } = require('electron');

let selectedImagePath = null;

document.getElementById('selectImgBtn').onclick = async () => {
    const path = await ipcRenderer.invoke('select-file');
    if (path) {
        selectedImagePath = path;
        document.getElementById('filePathDisplay').innerText = path;
    }
};

document.getElementById("startBtn").onclick = () => {
    const token = document.getElementById("accessToken").value.trim();
    const message = document.getElementById("postText").value.trim();

    if (!token) {
        alert("Error: Page Access Token is required!");
        return;
    }
    if (!message && !selectedImagePath) {
        alert("Error: You must provide a message or an image.");
        return;
    }

    document.getElementById("startBtn").disabled = true;
    document.getElementById("logBox").textContent = "Starting...\n";
    
    ipcRenderer.send('start-post', { token, message, imagePath: selectedImagePath });
};

ipcRenderer.on('log', (event, msg) => {
    const logBox = document.getElementById("logBox");
    logBox.textContent += `[${new Date().toLocaleTimeString()}] ${msg}\n`;
    logBox.scrollTop = logBox.scrollHeight;
});
