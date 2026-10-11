// API Client for Missing Person Platform
const API = {
  baseUrl: '/api/v1',

  getToken() {
    return localStorage.getItem('mp_auth_token') || '';
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('mp_auth_token', token);
    } else {
      localStorage.removeItem('mp_auth_token');
    }
  },

  getUser() {
    const u = localStorage.getItem('mp_auth_user');
    return u ? JSON.parse(u) : null;
  },

  setUser(user) {
    if (user) {
      localStorage.setItem('mp_auth_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('mp_auth_user');
    }
  },

  async request(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = options.headers || {};

    const token = this.getToken();
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    try {
      const response = await fetch(url, { ...options, headers });

      if (response.status === 401) {
        // Clear invalid token
        this.setToken('');
        this.setUser(null);
        window.dispatchEvent(new CustomEvent('auth-changed'));
        throw new Error('Session expired or unauthorized. Please log in.');
      }

      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || data.message || `Request failed with status ${response.status}`);
      }
      return data;
    } catch (err) {
      console.error(`API Error on [${options.method || 'GET'}] ${endpoint}:`, err);
      throw err;
    }
  },

  async requestRaw(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    const headers = options.headers || {};
    const token = this.getToken();
    if (token && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    const response = await fetch(url, { ...options, headers });
    if (!response.ok) {
      const errText = await response.text();
      throw new Error(errText || `Request failed with status ${response.status}`);
    }
    const text = await response.text();
    const checksum = response.headers.get('X-Audit-Checksum-SHA256') || '';
    const totalRecords = response.headers.get('X-Total-Records') || '';
    return { text, checksum, totalRecords, response };
  },

  // Auth Endpoints
  async login(username, password) {
    const res = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ username, password })
    });
    this.setToken(res.access_token);
    this.setUser(res.user);
    window.dispatchEvent(new CustomEvent('auth-changed'));
    return res;
  },

  async logout() {
    try {
      if (this.getToken()) {
        await this.request('/auth/logout', { method: 'POST' });
      }
    } catch (e) {
      // Ignore network errors on logout
    } finally {
      this.setToken('');
      this.setUser(null);
      window.dispatchEvent(new CustomEvent('auth-changed'));
    }
  },

  async getMe() {
    return this.request('/auth/me');
  },

  // Staff & RBAC Management (Admin Only)
  async getOfficers() {
    return this.request('/auth/users');
  },

  async provisionOfficer(officerData) {
    return this.request('/auth/users', {
      method: 'POST',
      body: JSON.stringify(officerData)
    });
  },

  async updateOfficerStatus(userId, isActive) {
    return this.request(`/auth/users/${userId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ is_active: isActive })
    });
  },

  // Cases Endpoints
  async getCases(status = '', search = '') {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (search) params.append('search', search);
    return this.request(`/cases?${params.toString()}`);
  },

  async getCase(id) {
    return this.request(`/cases/${id}`);
  },

  async createCase(caseData) {
    return this.request('/cases', {
      method: 'POST',
      body: JSON.stringify(caseData)
    });
  },

  async updateCase(id, updateData) {
    return this.request(`/cases/${id}`, {
      method: 'PUT',
      body: JSON.stringify(updateData)
    });
  },

  async addReferencePhoto(caseId, file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request(`/cases/${caseId}/references`, {
      method: 'POST',
      body: formData
    });
  },

  async updateCaseStatus(caseId, status, notes = '') {
    return this.request(`/cases/${caseId}/status`, {
      method: 'PUT',
      body: JSON.stringify({ status, notes })
    });
  },

  async getCaseBulletin(caseId) {
    return this.request(`/cases/${caseId}/bulletin`);
  },

  async getCaseTimeline(caseId) {
    return this.request(`/cases/${caseId}/timeline`);
  },

  async archiveCase(caseId) {
    return this.request(`/cases/${caseId}`, {
      method: 'DELETE'
    });
  },

  async deleteReferencePhoto(caseId, refId) {
    return this.request(`/cases/${caseId}/references/${refId}`, {
      method: 'DELETE'
    });
  },


  // Sightings Endpoints
  async submitSighting(formData) {
    return this.request('/sightings', {
      method: 'POST',
      body: formData
    });
  },

  async getSightings(status = '', search = '') {
    const params = new URLSearchParams();
    if (status) params.append('status', status);
    if (search) params.append('search', search);
    const qs = params.toString();
    return this.request(`/sightings${qs ? '?' + qs : ''}`);
  },

  async getSighting(id) {
    return this.request(`/sightings/${id}`);
  },

  async updateSightingStatus(id, status, rationale) {
    return this.request(`/sightings/${id}/status`, {
      method: 'PATCH',
      body: JSON.stringify({ status, rationale })
    });
  },

  async deleteSighting(id) {
    return this.request(`/sightings/${id}`, {
      method: 'DELETE'
    });
  },

  async lookupReceipt(receiptNo) {
    return this.request(`/sightings/lookup/${encodeURIComponent(receiptNo)}`);
  },

  // Review & Candidate Endpoints (Module 6)
  async getCandidates(params = {}) {
    const qs = new URLSearchParams();
    if (params.status) qs.append('status', params.status);
    if (params.minScore !== undefined && params.minScore !== null) qs.append('min_score', params.minScore);
    if (params.caseId) qs.append('case_id', params.caseId);
    if (params.sightingId) qs.append('sighting_id', params.sightingId);
    if (params.sortBy) qs.append('sort_by', params.sortBy);
    const query = qs.toString();
    return this.request(`/candidates${query ? '?' + query : ''}`);
  },

  async getPendingCandidates() {
    return this.request('/candidates/pending');
  },

  async getCandidateDetail(candidateId) {
    return this.request(`/candidates/${candidateId}`);
  },

  async getCandidateReviews(candidateId) {
    return this.request(`/candidates/${candidateId}/reviews`);
  },

  async getCandidateStats() {
    return this.request('/candidates/stats');
  },

  async submitReview(candidateId, disposition, rationale, nextSteps = '') {
    return this.request(`/candidates/${candidateId}/reviews`, {
      method: 'POST',
      body: JSON.stringify({ disposition, rationale, next_steps: nextSteps })
    });
  },

  async submitBatchReview(candidateIds, disposition, rationale, nextSteps = '') {
    return this.request('/candidates/batch-review', {
      method: 'POST',
      body: JSON.stringify({
        candidate_ids: candidateIds,
        disposition,
        rationale,
        next_steps: nextSteps
      })
    });
  },

  // Dashboard & Maps (Module 6)
  async getDashboardStats() {
    return this.request('/dashboard/stats');
  },

  async getMapPoints(minSimilarity = null, statusFilter = null, caseId = null) {
    const qs = new URLSearchParams();
    if (minSimilarity !== null && minSimilarity !== undefined) qs.append('min_similarity', minSimilarity);
    if (statusFilter) qs.append('status_filter', statusFilter);
    if (caseId) qs.append('case_id', caseId);
    const query = qs.toString();
    return this.request(`/map/points${query ? '?' + query : ''}`);
  },

  async getAuditLogs(params = {}) {
    if (typeof params === 'number') {
      return this.request(`/audit?limit=${params}`);
    }
    const qs = new URLSearchParams();
    if (params.limit) qs.append('limit', params.limit);
    if (params.offset) qs.append('offset', params.offset);
    if (params.action) qs.append('action', params.action);
    if (params.actor) qs.append('actor', params.actor);
    if (params.resource_type) qs.append('resource_type', params.resource_type);
    if (params.start_date) qs.append('start_date', params.start_date);
    if (params.end_date) qs.append('end_date', params.end_date);
    const query = qs.toString();
    return this.request(`/audit${query ? '?' + query : ''}`);
  },

  async getAuditLogsWithHeaders(params = {}) {
    const qs = new URLSearchParams();
    if (params.limit) qs.append('limit', params.limit);
    if (params.offset) qs.append('offset', params.offset);
    if (params.action) qs.append('action', params.action);
    if (params.actor) qs.append('actor', params.actor);
    if (params.resource_type) qs.append('resource_type', params.resource_type);
    if (params.start_date) qs.append('start_date', params.start_date);
    if (params.end_date) qs.append('end_date', params.end_date);
    const query = qs.toString();
    const url = `${this.baseUrl}/audit${query ? '?' + query : ''}`;
    const token = this.getToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const res = await fetch(url, { headers });
    const checksum = res.headers.get('X-Audit-Checksum-SHA256') || '';
    const totalCount = parseInt(res.headers.get('X-Total-Count') || '0', 10);
    const logs = await res.json();
    return { logs, checksum, totalCount };
  },

  async exportAuditLogs(format = 'csv', params = {}) {
    const qs = new URLSearchParams();
    qs.append('format', format);
    if (params.limit) qs.append('limit', params.limit);
    if (params.action) qs.append('action', params.action);
    if (params.actor) qs.append('actor', params.actor);
    if (params.resource_type) qs.append('resource_type', params.resource_type);
    if (params.start_date) qs.append('start_date', params.start_date);
    if (params.end_date) qs.append('end_date', params.end_date);
    return this.requestRaw(`/audit/export?${qs.toString()}`);
  },

  async getGovernanceReport() {
    return this.request('/audit/governance');
  },

  async getSecurityHealth() {
    return this.request('/system/security-health');
  },

  async getBenchmark() {
    return this.request('/benchmark');
  },

  async getNotifications(unreadOnly = false, limit = 50) {
    return this.request(`/notifications?unread_only=${unreadOnly}&limit=${limit}`);
  },

  async getUnreadNotificationCount() {
    return this.request('/notifications/unread-count');
  },

  async markNotificationRead(notificationId) {
    return this.request(`/notifications/${notificationId}/read`, {
      method: 'PUT'
    });
  },

  async markAllNotificationsRead() {
    return this.request('/notifications/read-all', {
      method: 'PUT'
    });
  },

  // Module 3: Face Processing Engine Endpoints
  async getFaceModels() {
    return this.request('/faces/models');
  },

  async analyzeFace(file) {
    const formData = new FormData();
    formData.append('file', file);
    return this.request('/faces/analyze', {
      method: 'POST',
      body: formData
    });
  },

  async compareFaces(file1, file2) {
    const formData = new FormData();
    formData.append('file1', file1);
    formData.append('file2', file2);
    return this.request('/faces/compare', {
      method: 'POST',
      body: formData
    });
  },

  // Module 5: AI Matching Engine & Candidate Retrieval Endpoints
  async getGalleryTelemetry() {
    return this.request('/match/gallery');
  },

  async searchGallery(file, topK = 5, minThreshold = 0.30) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('top_k', topK);
    formData.append('min_threshold', minThreshold);
    return this.request('/match/search', {
      method: 'POST',
      body: formData
    });
  },

  async simulateThreshold(threshold) {
    return this.request('/match/simulate-threshold', {
      method: 'POST',
      body: JSON.stringify({ threshold: parseFloat(threshold) })
    });
  }
};
