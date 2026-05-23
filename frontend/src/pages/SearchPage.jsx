import React, { useState } from 'react';
import SearchBar from '../components/SearchBar';
import ResultsList from '../components/ResultsList';
import Loader from '../components/Loader';
import ErrorBanner from '../components/ErrorBanner';
import { searchPapers } from '../services/api';

const SearchPage = () => {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (query) => {
    setLoading(true);
    setError('');
    setPapers([]);

    try {
      // searchPapers returns the full RecommendationResponse; extract .papers
      const response = await searchPapers(query);
      setPapers(response.papers ?? []);
    } catch (err) {
      setError(err.message || 'Failed to fetch recommendations. Try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-5xl mx-auto px-4 py-8">
      <h1 className="text-3xl font-bold mb-6">Semantic Academic Paper Recommender</h1>
      <SearchBar onSearch={handleSearch} />
      {loading && <Loader />}
      {error && <ErrorBanner message={error} />}
      <ResultsList papers={papers} />
    </div>
  );
};

export default SearchPage;