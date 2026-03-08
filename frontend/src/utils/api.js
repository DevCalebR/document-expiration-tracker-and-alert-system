export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export const API_ORIGIN = new URL(API_BASE_URL).origin;

let authToken = null;

const buildAuthHeaders = (headers = {}) => {
  const token = getAuthToken();
  return token ? { ...headers, Authorization: `Bearer ${token}` } : headers;
};

const encodePathSegments = (value) =>
  value
    .split('/')
    .map((segment) => encodeURIComponent(segment))
    .join('/');

const parseResponse = async (response, fallbackMessage) => {
  let data = null;
  const contentType = response.headers.get('content-type') || '';

  if (contentType.includes('application/json')) {
    data = await response.json();
  } else {
    const text = await response.text();
    data = text ? { detail: text } : null;
  }

  if (!response.ok) {
    throw new Error(data?.detail || data?.message || fallbackMessage);
  }

  return data;
};

const requestJson = async (path, options = {}, fallbackMessage = 'Request failed') => {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: buildAuthHeaders(options.headers || {})
  });
  return parseResponse(response, fallbackMessage);
};

export const setAuthToken = (token) => {
  authToken = token;
  if (token) {
    localStorage.setItem('auth_token', token);
  } else {
    localStorage.removeItem('auth_token');
  }
};

export const getAuthToken = () => {
  if (!authToken) {
    authToken = localStorage.getItem('auth_token');
  }
  return authToken;
};

export const api = {
  async login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await fetch(`${API_BASE_URL}/auth/token`, {
      method: 'POST',
      body: formData
    });
    const data = await parseResponse(response, 'Login failed');
    setAuthToken(data.access_token);
    return data;
  },

  async getCurrentUser() {
    return requestJson('/auth/me', {}, 'Failed to load current user');
  },

  async register(userData) {
    return requestJson(
      '/auth/register',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(userData)
      },
      'Registration failed'
    );
  },

  async verifyEmail(username, token) {
    return requestJson(
      '/auth/verify-email',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, token })
      },
      'Verification failed'
    );
  },

  async logout() {
    const token = getAuthToken();
    if (token) {
      try {
        await fetch(`${API_BASE_URL}/auth/logout`, {
          method: 'POST',
          headers: buildAuthHeaders()
        });
      } catch (_error) {
        // Best-effort logout on the client.
      }
    }
    setAuthToken(null);
  },

  async getFiles() {
    return requestJson('/files', {}, 'Failed to load files');
  },

  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: buildAuthHeaders(),
      body: formData
    });
    return parseResponse(response, 'Upload failed');
  },

  async processFilesAsync(filenames) {
    return requestJson(
      '/process/async',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filenames })
      },
      'Failed to enqueue processing job'
    );
  },

  async processFiles(filenames) {
    const queryString = filenames.map((filename) => `filenames=${encodeURIComponent(filename)}`).join('&');
    return requestJson(`/process?${queryString}`, {}, 'Processing failed');
  },

  async getJobStatus(jobId) {
    return requestJson(`/jobs/${encodeURIComponent(jobId)}`, {}, 'Failed to load job status');
  },

  async extractText(filename) {
    return requestJson(
      `/extract-text?filename=${encodeURIComponent(filename)}`,
      {},
      'Failed to extract text'
    );
  },

  async deleteFile(filename) {
    return requestJson(
      `/files/${encodePathSegments(filename)}`,
      { method: 'DELETE' },
      'Delete failed'
    );
  },

  async analyzeWithAI(results) {
    return requestJson(
      '/ai/analyze',
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ results })
      },
      'AI analysis failed'
    );
  },

  async getAuditLogs() {
    return requestJson('/audit/logs', {}, 'Failed to fetch audit logs');
  },

  async getAdminStatus() {
    return requestJson('/admin/status', {}, 'Failed to fetch system status');
  },

  async runAlerts() {
    return requestJson('/admin/alerts/run', { method: 'POST' }, 'Failed to trigger alerts');
  },

  async sendTestEmail() {
    return requestJson('/admin/test-email', { method: 'POST' }, 'Failed to send test email');
  },

  async getCloudProviders() {
    return requestJson('/cloud/providers', {}, 'Failed to fetch cloud providers');
  },

  async getCloudAuthUrl(provider) {
    return requestJson(`/cloud/${provider}/auth-url`, {}, 'Failed to start cloud authentication');
  },

  async getCloudFiles(provider) {
    return requestJson(`/cloud/${provider}/files`, {}, 'Failed to fetch cloud files');
  },

  async importCloudFiles(provider, files) {
    return requestJson(
      `/cloud/${provider}/import`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          provider,
          files: files.map((file) => ({ id: file.id, name: file.name }))
        })
      },
      'Import failed'
    );
  },

  async disconnectCloudProvider(provider) {
    return requestJson(
      `/cloud/${provider}/connection`,
      { method: 'DELETE' },
      'Failed to disconnect cloud provider'
    );
  },

  async getExpiringSoon(days = 7) {
    return requestJson(
      `/documents/expiring-soon?days=${encodeURIComponent(days)}`,
      {},
      'Failed to fetch expiring documents'
    );
  }
};
