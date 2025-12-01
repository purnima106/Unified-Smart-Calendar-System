import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

// Request interceptor
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor
api.interceptors.response.use(
  (response) => {
    console.log(`API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.status, error.response?.data);
    
    // Don't redirect for check-auth endpoint as 401 is expected when not logged in
    if (error.response?.status === 401 && !error.config.url.includes('/check-auth')) {
      // Redirect to login if unauthorized (but only in production)
      if (process.env.NODE_ENV === 'production') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  checkAuth: () => api.get('/auth/check-auth'),
  googleLogin: () => api.get('/auth/login/google'),
  microsoftLogin: () => api.get('/auth/login/microsoft'),
  logout: () => api.get('/auth/logout'),
  getUserProfile: () => api.get('/auth/user/profile'),
  getUserConnections: () => api.get('/auth/user/connections'),
  listAllConnections: () => api.get('/auth/user/connections/list'),
  removeConnection: (connectionId) => api.delete(`/auth/user/connections/${connectionId}`),
  toggleConnection: (connectionId) => api.post(`/auth/user/connections/${connectionId}/toggle`),
};

// Calendar API
export const calendarAPI = {
  // Existing methods
  getEvents: (params = {}) => api.get('/calendar/events', { params }),
  syncGoogle: () => api.post('/calendar/sync/google'),
  syncMicrosoft: () => api.post('/calendar/sync/microsoft'),
  syncAll: () => api.post('/calendar/sync/all'),
  syncBidirectional: () => api.post('/calendar/sync/bidirectional'),

  createEvent: (eventData) => api.post('/calendar/create-event', eventData),
  getConflicts: (params = {}) => api.get('/calendar/conflicts', { params }),
  findFreeSlots: (params) => api.get('/calendar/free-slots', { params }),
  getFreeSlots: (params) => api.get('/calendar/free-slots', { params }), // Alias for findFreeSlots
  suggestMeetingTime: (params) => api.post('/calendar/suggest-meeting', params),
  suggestMeeting: (params) => api.post('/calendar/suggest-meeting', params), // Alias for suggestMeetingTime
  getSummary: (params = {}) => api.get('/calendar/summary', { params }),
  
  // New methods added for enhanced functionality
  testConnection: () => api.get('/calendar/test'),
  createSampleEvents: () => api.post('/calendar/create-sample-events'),
  clearEvents: () => api.delete('/calendar/clear-events'),
};

// Health API
export const healthAPI = {
  check: () => api.get('/health'),
};

// Utility function for direct fetch calls (fallback)
export const directFetch = {
  get: async (endpoint, params = {}) => {
    const url = new URL(`${API_BASE_URL}${endpoint}`);
    Object.keys(params).forEach(key => url.searchParams.append(key, params[key]));
    
    const response = await fetch(url.toString(), {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    
    return response.json();
  },
  
  post: async (endpoint, data = {}) => {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(data)
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    
    return response.json();
  },
  
  delete: async (endpoint) => {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ error: 'Unknown error' }));
      throw new Error(errorData.error || `HTTP ${response.status}`);
    }
    
    return response.json();
  }
};

export default api;