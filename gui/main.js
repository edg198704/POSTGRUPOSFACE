const { ipcRenderer } = require('electron');

// Handle Directory Selection
document.getElementById('selectDirBtn').onclick = async () => {
    const path = await ipcRenderer.invoke('select-dir');
    if (path) {
        document.getElementById('dirPath').value = path;
    }
};

// Handle Start Button
document.getElementById('startBtn').onclick = () => {
    const token = document.getElementById('accessToken').value.trim();
    const dirPath = document.getElementById('dirPath').value;
    const manualText = document.getElementById('postText').value;

    if (!token) return alert('Please enter a Page Access Token');
    if (!dirPath) return alert('Please select a content directory');

    // Disable button to prevent double click
    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.innerText = 'Running...';
    btn.classList.add('disabled');

    ipcRenderer.send('start-post', { token, dirPath, manualText });
};

// Handle Logs
ipcRenderer.on('log', (event, msg) => {
    const logBox = document.getElementById('logBox');
    const timestamp = new Date().toLocaleTimeString();
    logBox.textContent += `[${timestamp}] ${msg}\n`;
    logBox.scrollTop = logBox.scrollHeight;
});
