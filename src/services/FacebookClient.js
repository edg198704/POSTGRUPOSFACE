const axios = require('axios');
const fs = require('fs-extra');
const FormData = require('form-data');

class FacebookClient {
    constructor(accessToken) {
        if (!accessToken) throw new Error("Page Access Token is required");
        this.accessToken = accessToken;
        this.baseUrl = 'https://graph.facebook.com/v19.0';
        this.axios = axios.create({
            baseURL: this.baseUrl
        });
    }

    /**
     * Fetches groups the Page is a member of.
     * Endpoint: /me/groups
     */
    async getJoinedGroups() {
        try {
            const response = await this.axios.get('/me/groups', {
                params: {
                    access_token: this.accessToken,
                    fields: 'id,name,privacy',
                    limit: 100
                }
            });
            return response.data.data || [];
        } catch (error) {
            this.handleError(error, 'Fetching Groups');
        }
    }

    /**
     * Posts a photo to a specific group.
     * Endpoint: /{group_id}/photos
     * Requires multipart/form-data
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
                headers: form.getHeaders()
            });

            return response.data;
        } catch (error) {
            this.handleError(error, `Posting to Group ${groupId}`);
        }
    }

    handleError(error, context) {
        const msg = error.response 
            ? JSON.stringify(error.response.data.error) 
            : error.message;
        console.error(`[${context}] Error:`, msg);
        throw new Error(`FB API Error [${context}]: ${msg}`);
    }

    static async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = FacebookClient;
