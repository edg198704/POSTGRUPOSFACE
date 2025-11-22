const axios = require('axios');
const fs = require('fs-extra');
const FormData = require('form-data');

class FacebookClient {
    constructor(accessToken) {
        if (!accessToken) throw new Error("Page Access Token is required");
        this.accessToken = accessToken;
        this.baseUrl = 'https://graph.facebook.com/v19.0';
        this.axios = axios.create({
            baseURL: this.baseUrl,
            timeout: 120000 // 2 minutes for large uploads
        });
    }

    /**
     * Verifies the token and returns Page details.
     */
    async validateToken() {
        try {
            const response = await this.axios.get('/me', {
                params: { access_token: this.accessToken, fields: 'id,name,access_token' }
            });
            return response.data;
        } catch (error) {
            this.handleError(error, 'Token Validation');
        }
    }

    /**
     * Recursively fetches ALL groups the Page is a member of.
     * Handles Graph API pagination.
     */
    async getGroups() {
        let allGroups = [];
        let nextUrl = `/me/groups?fields=id,name,privacy&limit=50&access_token=${this.accessToken}`;

        try {
            while (nextUrl) {
                // If nextUrl is a full URL, we need to handle it carefully with axios or just use the path if possible.
                // However, axios.get(fullUrl) works if we override baseURL logic or just use a fresh call.
                // Simplest way: use a raw axios call for pagination URLs as they are absolute.
                const response = await axios.get(nextUrl);
                
                const data = response.data;
                if (data.data && data.data.length > 0) {
                    allGroups = allGroups.concat(data.data);
                }

                nextUrl = data.paging && data.paging.next ? data.paging.next : null;
            }
            return allGroups;
        } catch (error) {
            this.handleError(error, 'Fetching Groups');
        }
    }

    /**
     * Posts a photo to a specific group.
     */
    async postPhoto(groupId, imagePath, caption) {
        try {
            if (!await fs.pathExists(imagePath)) {
                throw new Error(`Image not found: ${imagePath}`);
            }

            const form = new FormData();
            form.append('access_token', this.accessToken);
            form.append('source', fs.createReadStream(imagePath));
            if (caption) {
                form.append('message', caption);
            }

            const response = await this.axios.post(`/${groupId}/photos`, form, {
                headers: {
                    ...form.getHeaders()
                }
            });

            return response.data;
        } catch (error) {
            this.handleError(error, `Posting to Group ${groupId}`);
        }
    }

    handleError(error, context) {
        let msg = error.message;
        if (error.response && error.response.data && error.response.data.error) {
            const fbError = error.response.data.error;
            msg = `[API Error ${fbError.code}] ${fbError.message} (Type: ${fbError.type})`;
        }
        console.error(`[${context}] ${msg}`);
        throw new Error(msg);
    }

    static async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = FacebookClient;
