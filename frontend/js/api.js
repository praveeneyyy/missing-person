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

  async getSightings(status = '') {
    const params = status ? `?status=${status}` : '';
    return this.request(`/sightings${params}`);
  },

  async getSighting(id) {
    return this.request(`/sightings/${id}`);
  },

  async lookupReceipt(receiptNo) {
    return this.request(`/sightings/lookup/${encodeURIComponent(receiptNo)}`);
  },

  // Review & Candidate Endpoints
  async getPendingCandidates() {
    return this.request('/candidates/pending');
  },

  async submitReview(candidateId, disposition, rationale, nextSteps = '') {
    return this.request(`/candidates/${candidateId}/reviews`, {
      method: 'POST',
      body: JSON.stringify({ disposition, rationale, next_steps: nextSteps })
    });
  },

  // Dashboard & Maps
  async getDashboardStats() {
    return this.request('/dashboard/stats');
  },

  async getMapPoints() {
    return this.request('/map/points');
  },

  async getAuditLogs(limit = 50) {
    return this.request(`/audit?limit=${limit}`);
  },

  async getBenchmark() {
    return this.request('/benchmark');
  },

  async getNotifications() {
    return this.request('/notifications');
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
  }
};
