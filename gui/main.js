const { ipcRenderer } = require('electron');

document.getElementById("startBtn").onclick = () => {
    const text = document.getElementById("postText").value;
    const imageFile = document.getElementById("imageFile").files[0] ? document.getElementById("imageFile").files[0].path : null;
    ipcRenderer.send('start-post', { text, imageFile });
};

ipcRenderer.on('log', (event, msg) => {
    const logBox = document.getElementById("logBox");
    logBox.textContent += msg + "\n";
    logBox.scrollTop = logBox.scrollHeight;
});
