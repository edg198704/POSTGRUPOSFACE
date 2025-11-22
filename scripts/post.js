const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs-extra');
require('dotenv').config();
const FacebookClient = require('../src/services/FacebookClient');

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 900,
        height: 700,
        webPreferences: {
            nodeIntegration: true,
            contextIsolation: false // Allowed for internal automation tools
        }
    });

    mainWindow.loadFile(path.join(__dirname, '../gui/main.html'));
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') app.quit();
});

// --- Automation Logic ---

ipcMain.on('start-post', async (event, config) => {
    const { token, message, imagePath } = config;
    const sender = event.sender;

    sender.send('log', '🚀 Initializing Facebook Graph API Client...');

    try {
        const fb = new FacebookClient(token);
        
        sender.send('log', '🔍 Scanning for Groups...');
        const groups = await fb.getPageGroups();
        sender.send('log', `✅ Found ${groups.length} groups.`);

        if (groups.length === 0) {
            sender.send('log', '⚠️ No groups found. Ensure the Page is a member of groups.');
            return;
        }

        let successCount = 0;
        let failCount = 0;

        for (const [index, group] of groups.entries()) {
            sender.send('log', `⏳ [${index + 1}/${groups.length}] Posting to: ${group.name}...`);
            
            try {
                await fb.postToGroup(group.id, message, imagePath);
                sender.send('log', `✅ Success: ${group.name}`);
                successCount++;
            } catch (err) {
                sender.send('log', `❌ Failed: ${group.name} - ${err.message}`);
                failCount++;
            }

            // Safety Delay (Rate Limiting)
            const delay = Math.floor(Math.random() * 5000) + 5000; // 5-10 seconds
            sender.send('log', `zzZ Sleeping for ${delay/1000}s...`);
            await FacebookClient.sleep(delay);
        }

        sender.send('log', `🏁 Operation Complete. Success: ${successCount}, Failed: ${failCount}`);

    } catch (error) {
        sender.send('log', `⛔CRITICAL ERROR: ${error.message}`);
    }
});

// Helper to select file via native dialog if needed
ipcMain.handle('select-file', async () => {
    const result = await dialog.showOpenDialog({ properties: ['openFile'], filters: [{ name: 'Images', extensions: ['jpg', 'png', 'jpeg'] }] });
    return result.filePaths[0];
});
