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

  // POST /recommend
  async searchPapers(query, maxResults = 15, sources = ['semantic_scholar', 'arxiv']) {
    return this.request('/recommend', {
      method: 'POST',
      body: JSON.stringify({
        text: query,
        max_results: maxResults,
        sources,
      }),
    });
  }

  // Alias used by SearchPage.jsx
  async getRecommendations(query, maxResults = 15) {
    const data = await this.searchPapers(query, maxResults);
    return data.papers ?? [];
  }

  // POST /upload-document
  async uploadDocument(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${this.baseURL}/upload-document`, {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type here — browser sets it with the correct boundary
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `Upload failed: ${response.status}`);
    }

    return response.json();
  }

  // POST /ask
  async askQuestion(question, papers, topK = 8) {
    return this.request('/ask', {
      method: 'POST',
      body: JSON.stringify({
        question,
        paper_ids: papers.map(p => p.id),
        session_papers: papers.map(p => ({
          id: p.id,
          title: p.title,
          abstract: p.abstract,
          authors: p.authors,
          url: p.url,
          published: p.published,
        })),
        top_k: topK,
      }),
    });
  }

  // GET /stats
  async getStats() {
    return this.request('/stats');
  }

  // GET /api/jobs
  async getJobs() {
    return this.request('/api/jobs');
  }
}

export const apiService = new ApiService();
export const { searchPapers, getRecommendations, uploadDocument, askQuestion, getStats, getJobs } = apiService;
export default apiService;