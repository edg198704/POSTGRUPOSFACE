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
        
        let url = 'https://mbasic.facebook.com/groups/?seemore';
        const groups = [];
        const seenIds = new Set();
        let lastResponseData = '';

        // 3. FIX HEADERS
        const headers = { 
            'Cookie': cookieString,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Upgrade-Insecure-Requests': '1'
        };

        while (url) {
            try {
                const response = await axios.get(url, { headers });
                lastResponseData = response.data;

                if (response.request.res.responseUrl.includes('login') || response.request.res.responseUrl.includes('checkpoint')) {
                     await fs.writeFile('debug_mbasic_response.html', lastResponseData);
                     throw new Error("Cookies expired or checkpoint hit. See debug_mbasic_response.html");
                }

                const $ = cheerio.load(response.data);
                
                // 1. IMPLEMENT ROBUST SCRAPING (Regex > CSS)
                $('a[href*="/groups/"]').each((i, el) => {
                    const href = $(el).attr('href');
                    const name = $(el).text().trim();
                    
                    // Regex to find ID or Alias
                    const match = href.match(/\/groups\/([^/?&]+)/);
                    if (match && name) {
                        const id = match[1];
                        // Filter invalid IDs
                        if (!['create', 'search', 'joines', 'feed', 'category'].includes(id.toLowerCase())) {
                            if (!seenIds.has(id)) {
                                groups.push({ id, name });
                                seenIds.add(id);
                            }
                        }
                    }
                });

                // Pagination
                const nextHref = $('a:contains("See more")').attr('href');
                if (nextHref) {
                    url = nextHref.startsWith('http') ? nextHref : 'https://mbasic.facebook.com' + nextHref;
                    await new Promise(r => setTimeout(r, 2000)); // Polite delay
                } else {
                    url = null;
                }
            } catch (e) {
                console.error("Scraping error:", e.message);
                break;
            }
        }
        
        if (groups.length === 0) {
            // 2. ADD DEBUGGING (HTML Dump)
            await fs.writeFile('debug_mbasic_response.html', lastResponseData);
            throw new Error("No groups found. Raw HTML saved to 'debug_mbasic_response.html'. Check if logged in.");
        }
        
        return groups;
    }

    async postImages(groupId, imagePaths, caption) {
        const mediaIds = [];
        for (const imgPath of imagePaths) {
            const form = new FormData();
            form.append('access_token', this.accessToken);
            form.append('source', fs.createReadStream(imgPath));
            form.append('published', 'false');
            
            const res = await this.axios.post(`/${groupId}/photos`, form, { headers: form.getHeaders() });
            mediaIds.push(res.data.id);
        }

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
