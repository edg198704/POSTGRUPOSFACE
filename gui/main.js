const { ipcRenderer } = require('electron');
const fs = require('fs');
const path = require('path');

window.onload = async () => {
    const config = await ipcRenderer.invoke('get-config');
    if (config.defaultToken) document.getElementById('accessToken').value = config.defaultToken;
};

document.getElementById('selectDirBtn').onclick = async () => {
    const path = await ipcRenderer.invoke('select-dir');
    if (path) document.getElementById('dirPath').value = path;
};

// Preview Logic
document.getElementById('previewBtn').onclick = () => {
    const dirPath = document.getElementById('dirPath').value;
    const manualText = document.getElementById('postText').value;
    
    if (!dirPath) return alert('Select a directory first');

    fs.readdir(dirPath, (err, files) => {
        if (err) return alert('Error reading directory');
        const images = files.filter(f => /\.(jpg|jpeg|png|gif|webp)$/i.test(f));
        
        if (images.length === 0) return alert('No images found');

        // Show Preview UI
        document.getElementById('previewSection').style.display = 'block';
        document.getElementById('previewBtn').style.display = 'none';
        document.getElementById('previewCaption').innerText = manualText || "(Using description.txt if available)";
        
        const imgContainer = document.getElementById('previewImages');
        imgContainer.innerHTML = '';
        images.forEach(img => {
            const el = document.createElement('img');
            el.src = path.join(dirPath, img);
            el.style.height = '100px';
            imgContainer.appendChild(el);
        });
    });
};

// Confirm & Start
document.getElementById('confirmBtn').onclick = () => {
    const token = document.getElementById('accessToken').value.trim();
    const dirPath = document.getElementById('dirPath').value;
    const manualText = document.getElementById('postText').value;

    if (!token) return alert('Token required');

    document.getElementById('confirmBtn').disabled = true;
    document.getElementById('confirmBtn').innerText = 'Running...';
    
    ipcRenderer.send('start-post', { token, dirPath, manualText });
};

ipcRenderer.on('log', (event, msg) => {
    const logBox = document.getElementById('logBox');
    logBox.textContent += `[${new Date().toLocaleTimeString()}] ${msg}\n`;
    logBox.scrollTop = logBox.scrollHeight;
});
