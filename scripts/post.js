const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs-extra');
const FacebookClient = require('../src/services/FacebookClient');
require('dotenv').config();

let mainWindow;
function createWindow() {
    mainWindow = new BrowserWindow({ width: 1000, height: 800, webPreferences: { nodeIntegration: true, contextIsolation: false } });
    mainWindow.loadFile(path.join(__dirname, '../gui/main.html'));
}
app.whenReady().then(createWindow);

ipcMain.handle('get-config', () => ({ defaultToken: process.env.FB_PAGE_TOKEN || '' }));
ipcMain.handle('select-dir', async () => { 
    const res = await dialog.showOpenDialog(mainWindow, { properties: ['openDirectory'] });
    return res.filePaths[0] || null;
});

ipcMain.on('start-post', async (event, { token, dirPath, manualText }) => {
    const sendLog = (msg) => event.sender.send('log', msg);
    const finalToken = token || process.env.FB_PAGE_TOKEN;

    try {
        const client = new FacebookClient(finalToken);
        sendLog('🔐 Validating Token...');
        const page = await client.validateToken();
        sendLog(`✅ Authenticated: ${page.name}`);

        sendLog('🔍 Fetching Groups...');
        const groups = await client.getGroups();
        sendLog(`✅ Found ${groups.length} groups.`);

        const files = await fs.readdir(dirPath);
        const images = files.filter(f => /\.(jpg|jpeg|png|gif|webp)$/i.test(f)).map(f => path.join(dirPath, f));
        
        if (images.length === 0) return sendLog('❌ No images found.');

        let caption = manualText;
        const descPath = path.join(dirPath, 'description.txt');
        if (await fs.pathExists(descPath)) caption = await fs.readFile(descPath, 'utf-8');

        sendLog(`📸 Found ${images.length} images to post.`);

        for (const [i, group] of groups.entries()) {
            sendLog(`[${i+1}/${groups.length}] Posting to ${group.name}...`);
            try {
                await client.postImages(group.id, images, caption);
                sendLog(`✅ Success: ${group.name}`);
            } catch (e) {
                sendLog(`❌ Failed: ${group.name} - ${e.message}`);
            }
            if (i < groups.length - 1) {
                const delay = Math.floor(Math.random() * (90000 - 30000 + 1) + 30000);
                sendLog(`⏳ Waiting ${Math.round(delay/1000)}s...`);
                await FacebookClient.sleep(delay);
            }
        }
        sendLog('🎉 Done!');
    } catch (e) {
        sendLog(`🔥 Error: ${e.message}`);
    }
});
