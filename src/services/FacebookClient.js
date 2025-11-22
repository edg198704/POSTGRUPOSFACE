const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');

class FacebookClient {
    constructor(accessToken) {
        if (!accessToken) throw new Error("Page Access Token is required");
        this.accessToken = accessToken;
        this.baseUrl = 'https://graph.facebook.com/v19.0';
        this.axios = axios.create({
            baseURL: this.baseUrl,
            params: { access_token: this.accessToken }
        });
    }

    async getPageGroups() {
        try {
            // Fetches groups the Page belongs to or manages
            const response = await this.axios.get('/me/groups', {
                params: { fields: 'id,name,privacy', limit: 100 }
            });
            return response.data.data || [];
        } catch (error) {
            console.error('Error fetching groups:', error.response ? error.response.data : error.message);
            throw new Error('Failed to fetch groups. Check Token Permissions.');
        }
    }

    async postToGroup(groupId, message, imagePath = null) {
        try {
            if (imagePath) {
                // Post Photo with Caption
                const formData = new FormData();
                const imageBuffer = await fs.readFile(imagePath);
                const blob = new Blob([imageBuffer]);
                
                // Note: In Node.js environment with Axios, we use specific form-data handling or direct binary upload
                // For simplicity and robustness in Node, we post binary directly to the source url if possible, 
                // but Graph API prefers multipart/form-data for local files. 
                // However, a simpler approach for this snippet is using a public URL or binary stream.
                // Let's use the binary upload endpoint for robustness:
                
                const fileStream = fs.createReadStream(imagePath);
                const res = await this.axios.post(`/${groupId}/photos`, fileStream, {
                    params: { caption: message },
                    headers: { 'Content-Type': 'multipart/form-data' }
                });
                return res.data;
            } else {
                // Post Text Only
                const res = await this.axios.post(`/${groupId}/feed`, { message });
                return res.data;
            }
        } catch (error) {
            const errMsg = error.response ? JSON.stringify(error.response.data) : error.message;
            throw new Error(`Failed to post to ${groupId}: ${errMsg}`);
        }
    }

    static async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = FacebookClient;
