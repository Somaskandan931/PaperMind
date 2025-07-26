const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

class ApiService {
  constructor() {
    this.baseURL = API_BASE_URL;
  }

  async request(endpoint, options = {}) {
    const url = `${this.baseURL}${endpoint}`;
    const config = {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  async searchPapers(query, maxResults = 15, sources = ['semantic_scholar', 'arxiv']) {
    return this.request('/recommend', {
      method: 'POST',
      body: JSON.stringify({
        text: query,
        max_results: maxResults,
        sources: sources
      }),
    });
  }

  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    return this.