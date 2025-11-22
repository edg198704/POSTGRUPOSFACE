const { ipcMain } = require('electron');
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

ipcMain.on('publicar', async (event, data) => {
    const browser = await chromium.launch({ headless: false });
    const page = await browser.newPage();

    // Cargar cookies
    const cookiesPath = path.resolve(__dirname, '../config/cookies.json');
    if(fs.existsSync(cookiesPath)){
        const cookies = JSON.parse(fs.readFileSync(cookiesPath, 'utf-8'));
        await page.context().addCookies(cookies);
    }

    // Ir a la página principal
    await page.goto('https://www.facebook.com/');
    await page.waitForTimeout(5000); // esperar login

    // Scraping de grupos de la página
    console.log("Obteniendo grupos automáticamente...");
    await page.goto('https://www.facebook.com/me/groups'); // página de grupos de la cuenta/página
    await page.waitForTimeout(5000);

    const grupos = await page.$$eval('a[href*="/groups/"]', links => {
        const ids = [];
        links.forEach(l => {
            const match = l.href.match(/\/groups\/(\d+)/);
            if(match) ids.push(match[1]);
        });
        return [...new Set(ids)]; // quitar duplicados
    });

    console.log("Grupos encontrados:", grupos);

    for(const grupo of grupos){
        try{
            await page.goto(`https://www.facebook.com/groups/${grupo}`);
            await page.waitForSelector('div[aria-label="Crear publicación"]', {timeout:15000});
            await page.click('div[aria-label="Crear publicación"]');

            const textareaSelector = 'div[aria-label="Escribe algo..."]';
            await page.waitForSelector(textareaSelector);
            await page.type(textareaSelector, data.texto, { delay: 20 });

            if(data.fotos.length>0){
                const inputFile = await page.$('input[type=file]');
                await inputFile.setInputFiles(data.fotos.map(f => path.resolve(f)));
            }

            const botonPublicar = 'div[aria-label="Publicar"]';
            await page.click(botonPublicar);
            console.log(`Publicado en grupo ${grupo}`);
            await page.waitForTimeout(5000);
        } catch(e){
            console.log(`Error publicando en grupo ${grupo}: ${e}`);
        }
    }

    await browser.close();
    console.log("Todas las publicaciones completadas ✅");
});