const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const FacebookClient = require('../src/services/FacebookClient');
require('dotenv').config();

let mainWindow;

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1000,
        height: 800,
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

// IPC: Provide Config to Renderer (Secure Token Handling)
ipcMain.handle('get-config', () => {
    return {
        defaultToken: process.env.FB_PAGE_TOKEN || ''
    };
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
    
    // Use Env var if token not provided in UI, or prefer UI if provided
    const finalToken = token || process.env.FB_PAGE_TOKEN;

    if (!finalToken) return sendLog('❌ Error: Access Token is missing (Check .env or Input).');
    if (!dirPath) return sendLog('❌ Error: No content directory selected.');

    try {
        sendLog('🚀 Initializing Facebook Client...');
        const client = new FacebookClient(finalToken);

        // 0. Validate Token
        sendLog('🔐 Validating Page Access Token...');
        const pageInfo = await client.validateToken();
        sendLog(`✅ Authenticated as Page: ${pageInfo.name} (ID: ${pageInfo.id})`);

        // 1. Fetch Groups
        sendLog('🔍 Fetching ALL joined groups (this may take a moment)...');
        const groups = await client.getGroups();
        sendLog(`✅ Found ${groups.length} groups.`);

        if (groups.length === 0) {
            return sendLog('⚠️ No groups found. Ensure the Page has joined groups.');
        }

        // 2. Load Content
        const files = await fs.readdir(dirPath);
        // Filter for common image formats
        const images = files.filter(f => /\.(jpg|jpeg|png|gif|bmp|webp)$/i.test(f));
        
        if (images.length === 0) {
            return sendLog('❌ No valid images found in the selected directory.');
        }

        // Check for description.txt override
        let finalMessage = manualText;
        const descFile = path.join(dirPath, 'description.txt');
        if (await fs.pathExists(descFile)) {
            finalMessage = await fs.readFile(descFile, 'utf-8');
            sendLog('mb Loaded description from description.txt');
        }

        // We pick the first image for now (could be randomized or looped in future versions)
        const imageToPost = path.join(dirPath, images[0]);
        sendLog(`📸 Selected Image: ${images[0]}`);

        // 3. Posting Loop
        sendLog('qc Starting Auto-Post Cycle...');
        
        for (const [index, group] of groups.entries()) {
            const progress = `[${index + 1}/${groups.length}]`;
            sendLog(`${progress} Posting to: ${group.name}...`);
            
            try {
                await client.postPhoto(group.id, imageToPost, finalMessage);
                sendLog(`✅ Published successfully to ${group.name}`);
            } catch (err) {
                sendLog(`❌ Failed to post to ${group.name}: ${err.message}`);
            }

            // Safety Delay (Randomized between 30s and 90s)
            if (index < groups.length - 1) {
                const minDelay = 30000;
                const maxDelay = 90000;
                const delay = Math.floor(Math.random() * (maxDelay - minDelay + 1) + minDelay);
                sendLog(`⏳ Waiting ${Math.round(delay/1000)}s to avoid rate limits...`);
                await FacebookClient.sleep(delay);
            }
        }

        sendLog('🎉 Automation Cycle Complete!');

    } catch (error) {
        sendLog(`🔥 Critical Error: ${error.message}`);
    }
});
