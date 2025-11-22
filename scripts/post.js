const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
const FacebookClient = require('../src/services/FacebookClient');
require('dotenv').config();

let mainWindow;
function createWindow() {
    mainWindow = new BrowserWindow({ width: 1000, height: 800, webPreferences: { nodeIntegration: true, contextIsolation: false } });
    mainWindow.loadFile(path.join(__dirname, '../gui/main.html'));
}
app.whenReady().then(createWindow);

ipcMain.handle('get-config', () => ({ defaultToken: process.env.FB_PAGE_TOKEN || '' }));

ipcMain.on('start-post', async (event, { token, imagePaths, manualText }) => {
    const sendLog = (msg) => event.sender.send('log', msg);
    
    try {
        sendLog('🚀 Initializing...');
        const client = new FacebookClient(token);
        
        sendLog('🔐 Validating Token...');
        await client.validateToken();
        
        sendLog('🔍 Fetching Groups...');
        const groups = await client.getGroups();
        sendLog(`✅ Found ${groups.length} groups.`);
        
        if (groups.length === 0) return sendLog('⚠️ No groups found.');

        for (const [index, group] of groups.entries()) {
            sendLog(`[${index+1}/${groups.length}] Posting to ${group.name}...`);
            try {
                await client.postImages(group.id, imagePaths, manualText);
                sendLog('✅ Success!');
            } catch (err) {
                sendLog(`❌ Failed: ${err.message}`);
            }
            
            if (index < groups.length - 1) {
                const delay = Math.floor(Math.random() * (60000 - 30000 + 1) + 30000);
                sendLog(`⏳ Waiting ${Math.round(delay/1000)}s...`);
                await FacebookClient.sleep(delay);
            }
        }
        sendLog('🎉 Done!');
    } catch (error) {
        sendLog(`🔥 Error: ${error.message}`);
    }
});
