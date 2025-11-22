const axios = require('axios');
const fs = require('fs-extra');
const FormData = require('form-data');

class FacebookClient {
    constructor(accessToken) {
        if (!accessToken) throw new Error("Page Access Token is required.");
        this.accessToken = accessToken;
        this.baseUrl = 'https://graph.facebook.com/v19.0';
    }

    /**
     * Fetches all groups the Page is a member of.
     * Requires 'groups_access_member_info' permission.
     */
    async getGroups() {
        try {
            const response = await axios.get(`${this.baseUrl}/me/groups`, {
                params: {
                    access_token: this.accessToken,
                    fields: 'id,name,privacy',
                    limit: 100
                }
            });
            return response.data.data || [];
        } catch (error) {
            this.handleError(error, 'fetching groups');
        }
    }

    /**
     * Posts a photo with a caption to a specific group.
     * Requires 'publish_to_groups' permission.
     */
    async postPhoto(groupId, imagePath, message) {
        try {
            const form = new FormData();
            form.append('source', fs.createReadStream(imagePath));
            if (message) form.append('caption', message);
            form.append('access_token', this.accessToken);

            const response = await axios.post(`${this.baseUrl}/${groupId}/photos`, form, {
                headers: form.getHeaders()
            });
            return response.data;
        } catch (error) {
            this.handleError(error, `posting to group ${groupId}`);
        }
    }

    handleError(error, context) {
        const msg = error.response?.data?.error?.message || error.message;
        throw new Error(`Error ${context}: ${msg}`);
    }

    static async sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

module.exports = FacebookClient;
