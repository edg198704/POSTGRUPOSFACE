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
        const res = await this.axios.get('/me', { params: { access_token: this.accessToken, fields: 'id,name' } });
        return res.data;
    }

    async getGroups() {
        try {
            return await this._getGroupsApi();
        } catch (e) {
            console.warn("API Failed, attempting cookie scrape...");
            return await this._getGroupsViaCookies();
        }
    }

    async _getGroupsApi() {
        let groups = [];
        let nextUrl = `${this.baseUrl}/me/groups?fields=id,name&limit=50&access_token=${this.accessToken}`;
        while (nextUrl) {
            const res = await axios.get(nextUrl);
            if (res.data.data) groups = groups.concat(res.data.data);
            nextUrl = res.data.paging?.next || null;
        }
        return groups;
    }

    async _getGroupsViaCookies() {
        const cookiePath = path.join(__dirname, '../../config/cookies.json');
        if (!fs.existsSync(cookiePath)) throw new Error("cookies.json missing");
        
        const cookies = await fs.readJson(cookiePath);
        const cookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');
        
        const res = await axios.get('https://mbasic.facebook.com/groups/?seemore', {
            headers: { 
                'Cookie': cookieStr,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        });

        const $ = cheerio.load(res.data);
        const groups = [];
        const seen = new Set();

        $('a[href*="/groups/"]').each((i, el) => {
            const href = $(el).attr('href');
            try {
                const idMatch = href.match(/\/groups\/(\d+)/);
                if (idMatch && !seen.has(idMatch[1])) {
                    groups.push({ id: idMatch[1], name: $(el).text().trim() });
                    seen.add(idMatch[1]);
                }
            } catch (e) {}
        });
        return groups;
    }

    async postImages(groupId, imagePaths, caption) {
        const mediaIds = [];
        // 1. Upload unpublished
        for (const imgPath of imagePaths) {
            const form = new FormData();
            form.append('access_token', this.accessToken);
            form.append('source', fs.createReadStream(imgPath));
            form.append('published', 'false');
            const res = await this.axios.post(`/${groupId}/photos`, form, { headers: form.getHeaders() });
            mediaIds.push(res.data.id);
        }

        // 2. Publish Feed
        if (mediaIds.length === 0) return;
        const attached_media = mediaIds.map(id => ({ media_fbid: id }));
        
        const res = await this.axios.post(`/${groupId}/feed`, {
            access_token: this.accessToken,
            message: caption,
            attached_media: JSON.stringify(attached_media)
        });
        return res.data;
    }

    static async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = FacebookClient;
