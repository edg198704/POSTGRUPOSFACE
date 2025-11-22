const { ipcRenderer } = require('electron');

window.onload = async () => {
    const config = await ipcRenderer.invoke('get-config');
    if (config.defaultToken) document.getElementById('accessToken').value = config.defaultToken;
};

document.getElementById('previewBtn').onclick = () => {
    const files = document.getElementById('imageInput').files;
    const text = document.getElementById('postText').value;
    
    if (files.length === 0) return alert("Select at least one image.");

    const grid = document.getElementById('previewGrid');
    grid.innerHTML = '';
    document.getElementById('previewCaption').innerText = text;

    Array.from(files).forEach(file => {
        const img = document.createElement('img');
        img.src = URL.createObjectURL(file);
        grid.appendChild(img);
    });

    document.getElementById('previewContainer').style.display = 'block';
    document.getElementById('startBtn').disabled = false;
};

document.getElementById('startBtn').onclick = () => {
    const token = document.getElementById('accessToken').value.trim();
    const text = document.getElementById('postText').value;
    const fileList = document.getElementById('imageInput').files;
    const imagePaths = Array.from(fileList).map(f => f.path);

    if (!token) return alert('Token required');

    const btn = document.getElementById('startBtn');
    btn.disabled = true;
    btn.innerText = 'Running...';

    ipcRenderer.send('start-post', { token, imagePaths, manualText: text });
};

ipcRenderer.on('log', (event, msg) => {
    const logBox = document.getElementById('logBox');
    logBox.textContent += `[${newjw Date().toLocaleTimeString()}] ${msg}\n`;
    logBox.scrollTop = logBox.scrollHeight;
});
