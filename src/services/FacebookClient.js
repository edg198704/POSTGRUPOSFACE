const axios = require('axios');
const fs = require('fs-extra');
const FormData = require('form-data');
const cheerio = require('cheerio');
const path = require('path');

class FacebookClient {
    constructor(accessToken) {
        this.accessToken = accessToken;
        this.baseUrl = 'https://graph.facebook.com/v19.0';
        this.axios = axios.create({ baseURL: this.baseUrl, timeout: 120000 });
    }

    async validateToken() {
        const response = await this.axios.get('/me', { params: { access_token: this.accessToken, fields: 'id,name' } });
        return response.data;
    }

    async getGroups() {
        try {
            return await this._getGroupsApi();
        } catch (error) {
            console.warn("API Failed, trying cookies...", error.message);
            return await this._getGroupsViaCookies();
        }
    }

    async _getGroupsApi() {
        let allGroups = [];
        let nextUrl = `${this.baseUrl}/me/groups?fields=id,name&limit=50&access_token=${this.accessToken}`;
        while (nextUrl) {
            const response = await axios.get(nextUrl);
            if (response.data.data) allGroups = allGroups.concat(response.data.data);
            nextUrl = response.data.paging?.next || null;
        }
        return allGroups;
    }

    async _getGroupsViaCookies() {
        const cookiePath = path.join(__dirname, '../../config/cookies.json');
        if (!await fs.pathExists(cookiePath)) throw new Error("API failed and cookies.json not found.");
        
        const cookies = await fs.readJson(cookiePath);
        const cookieString = cookies.map(c => `${c.name}=${c.value}`).join('; ');
        
        const response = await axios.get('https://mbasic.facebook.com/groups/?seemore', {
            headers: { 
                'Cookie': cookieString,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        });

        const $ = cheerio.load(response.data);
        const groups = [];
        $('a[href*="/groups/"]').each((i, el) => {
            const href = $(el).attr('href');
            const name = $(el).text();
            const match = href.match(/\/groups\/(\d+)/);
            if (match && name) {
                groups.push({ id: match[1], name: name.trim() });
            }
        });
        
        // Deduplicate
        return [...new Map(groups.map(item => [item.id, item])).values()];
    }

    async postImages(groupId, imagePaths, caption) {
        // 1. Upload Unpublished
        const mediaIds = [];
        for (const imgPath of imagePaths) {
            const form = new FormData();
            form.append('access_token', this.accessToken);
            form.append('source', fs.createReadStream(imgPath));
            form.append('published', 'false');
            
            const res = await this.axios.post(`/${groupId}/photos`, form, { headers: form.getHeaders() });
            mediaIds.push(res.data.id);
        }

        // 2. Attach to Feed
        const feedForm = {
            access_token: this.accessToken,
            attached_media: JSON.stringify(mediaIds.map(id => ({ media_fbid: id })))
        };
        if (caption) feedForm.message = caption;

        const response = await this.axios.post(`/${groupId}/feed`, feedForm);
        return response.data;
    }

    static async sleep(ms) { return new Promise(r => setTimeout(r, ms)); }
}
module.exports = FacebookClient;
