const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const FacebookClient = require('../src/services/FacebookClient');
require('dotenv').config();

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 750,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false,
            backgroundThrottling: false
        }
    });
    mainWindow.loadFile(path.join(__dirname, '../gui/main.html'));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

// IPC: Handle Directory Selection
ipcMain.handle('select-dir', async () => {
    const result = await dialog.showOpenDialog(mainWindow, {
        properties: ['openDirectory']
    });
    return result.filePaths[0] || null;
});

// IPC: Start Automation Logic
ipcMain.on('start-post', async (event, { token, dirPath, manualText }) => {
    const sendLog = (msg) => event.sender.send('log', msg);
    
    if (!token) return sendLog('❌ Error: Access Token is missing.');
    if (!dirPath) return sendLog('❌ Error: No content directory selected.');

    try {
        sendLog('🚀 Initializing Facebook Client...');
        const client = new FacebookClient(token);

        // 1. Fetch Groups
        sendLog('🔍 Fetching joined groups...');
        const groups = await client.getGroups();
        sendLog(`✅ Found ${groups.length} groups.`);

        if (groups.length === 0) {
            return sendLog('⚠️ No groups found. Check permissions.');
        }

        // 2. Load Content
        const files = await fs.readdir(dirPath);
        const images = files.filter(f => /\.(jpg|jpeg|png|gif)$/i.test(f));
        
        if (images.length === 0) {
            return sendLog('❌ No images found in the selected directory.');
        }

        // Check for description.txt override
        let finalMessage = manualText;
        const descFile = path.join(dirPath, 'description.txt');
        if (await fs.pathExists(descFile)) {
            finalMessage = await fs.readFile(descFile, 'utf-8');
            sendLog('mb Loaded description from description.txt');
        }

        const imageToPost = path.join(dirPath, images[0]);
        sendLog(`📸 Selected Image: ${images[0]}`);

        // 3. Posting Loop
        for (const [index, group] of groups.entries()) {
            sendLog(`[${index + 1}/${groups.length}] Posting to: ${group.name}...`);
            
            try {
                await client.postPhoto(group.id, imageToPost, finalMessage);
                sendLog(`✅ Published successfully to ${group.name}`);
            } catch (err) {
                sendLog(`❌ Failed: ${err.message}`);
            }

            // Safety Delay (30-60 seconds) to avoid spam filters
            if (index < groups.length - 1) {
                const delay = Math.floor(Math.random() * (60000 - 30000 + 1) + 30000);
                sendLog(`⏳ Waiting ${Math.round(delay/1000)}s to avoid rate limits...`);
                await FacebookClient.sleep(delay);
            }
        }

        sendLog('🎉 Automation Cycle Complete!');

    } catch (error) {
        sendLog(`🔥 Critical Error: ${error.message}`);
    }
});
