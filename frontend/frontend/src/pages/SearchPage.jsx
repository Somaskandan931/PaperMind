import React, { useState } from 'react';
import SearchBar from '../components/SearchBar';
import ResultsList from '../components/ResultsList';
import Loader from '../components/Loader';
import ErrorBanner from '../components/ErrorBanner';
import { getRecommendations } from '../services/api';

const SearchPage = () => {
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSearch = async (query) => {
    setLoading(true);
    setError('');
    setPapers([]);

    try {
      const response = await getRecommendations(query);
      setPapers(response);
    } catch (err) {
      setError('Failed to fetch recommendations. Try again.');
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
