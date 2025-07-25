import axios from 'axios';

const BASE_URL = 'http://localhost:8000';

export const getRecommendations = async (query) => {
  const res = await axios.post(`${BASE_URL}/recommend`, { query });
  return res.data.papers || [];
};

export const getExplanation = async (query, paper) => {
  const res = await axios.post(`${BASE_URL}/explain`, { query, paper });
  return res.data.explanation;
};
