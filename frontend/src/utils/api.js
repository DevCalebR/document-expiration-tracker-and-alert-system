const API_BASE_URL = 'http://127.0.0.1:8000';

let authToken = null;

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
    
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Login failed');
    }
    
    const data = await response.json();
    setAuthToken(data.access_token);
    return data;
  },

  async register(userData) {
    const response = await fetch(`${API_BASE_URL}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Registration failed');
    }
    return data;
  },

  async verifyEmail(username, token) {
    const response = await fetch(`${API_BASE_URL}/auth/verify-email`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, token })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || 'Verification failed');
    }
    return data;
  },
  
  async logout() {
    const token = getAuthToken();
    if (token) {
      await fetch(`${API_BASE_URL}/auth/logout`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });
    }
    setAuthToken(null);
  },
  
  async uploadFile(file) {
    const token = getAuthToken();
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await fetch(`${API_BASE_URL}/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`
      },
      body: formData
    });
    
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }
    
    return response.json();
  },
  
  async processFiles(filenames) {
    const token = getAuthToken();
    const queryString = filenames.map(f => `filenames=${encodeURIComponent(f)}`).join('&');
    
    const response = await fetch(`${API_BASE_URL}/process?${queryString}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    if (!response.ok) {
      throw new Error('Processing failed');
    }
    
    return response.json();
  },

  async extractText(filename) {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/extract-text?filename=${encodeURIComponent(filename)}`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error('Failed to extract text');
    }
    return response.json();
  },

  async deleteFile(filename) {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/files/${encodeURIComponent(filename)}`, {
      method: 'DELETE',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Delete failed');
    }
    return response.json();
  },

  async analyzeWithAI(results) {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/ai/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ results })
    });
    
    return response.json();
  },

  async getAuditLogs() {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/audit/logs`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    
    return response.json();
  },

  async getCloudFiles(provider) {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/cloud/${provider}/files`, {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });
    if (!response.ok) {
      throw new Error('Failed to fetch cloud files');
    }
    return response.json();
  },

  async importCloudFiles(provider, fileIds) {
    const token = getAuthToken();
    const response = await fetch(`${API_BASE_URL}/cloud/${provider}/import`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      },
      body: JSON.stringify({ provider, file_ids: fileIds })
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Import failed');
    }
    return response.json();
  }
};
