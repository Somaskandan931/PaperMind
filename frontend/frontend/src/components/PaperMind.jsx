import React, { useState, useCallback, useRef } from 'react';
import { Search, Upload, FileText, ExternalLink, Users, Calendar, Sparkles, Loader2, AlertCircle, CheckCircle, Trash2, Download } from 'lucide-react';

const API_BASE_URL = 'http://localhost:8000';

const PaperMind = () => {
  const [query, setQuery] = useState('');
  const [papers, setPapers] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [searchStats, setSearchStats] = useState(null);
  const [uploadStatus, setUploadStatus] = useState('');
  const fileInputRef = useRef(null);

  const searchPapers = useCallback(async (searchQuery = query) => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError('');

    try {
      const response = await fetch(`${API_BASE_URL}/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: searchQuery,
          max_results: 15,
          sources: ['semantic_scholar', 'arxiv']
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Search failed');
      }

      const data = await response.json();
      setPapers(data.papers);
      setSearchStats({
        total: data.total_found,
        processingTime: data.processing_time,
        query: data.query
      });
    } catch (err) {
      setError(err.message);
      setPapers([]);
    } finally {
      setLoading(false);
    }
  }, [query]);

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setLoading(true);
    setUploadStatus('Processing document...');
    setError('');

    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch(`${API_BASE_URL}/upload-document`, {
        method: 'POST',
        body: formData
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Upload failed');
      }

      const data = await response.json();
      setPapers(data.recommendations.papers);
      setSearchStats({
        total: data.recommendations.total_found,
        processingTime: data.recommendations.processing_time,
        query: data.extracted_terms
      });
      setUploadStatus(`Successfully analyzed "${file.name}"`);
      setQuery(data.extracted_terms);
    } catch (err) {
      setError(err.message);
      setUploadStatus('');
    } finally {
      setLoading(false);
    }
  };

  const clearResults = () => {
    setPapers([]);
    setQuery('');
    setSearchStats(null);
    setError('');
    setUploadStatus('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const exportResults = () => {
    const exportData = {
      query: searchStats?.query || query,
      searchDate: new Date().toISOString(),
      totalResults: papers.length,
      papers: papers.map(paper => ({
        title: paper.title,
        authors: paper.authors,
        abstract: paper.abstract,
        url: paper.url,
        source: paper.source,
        published: paper.published,
        relevanceScore: paper.relevance_score
      }))
    };

    const blob = new Blob([JSON.stringify(exportData, null, 2)], {
      type: 'application/json'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `papermind_results_${new Date().toISOString().split('T')[0]}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-gradient-to-r from-blue-600 to-purple-600 rounded-lg">
                <Sparkles className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-600 to-purple-600 bg-clip-text text-transparent">
                  PaperMind
                </h1>
                <p className="text-sm text-gray-600">AI-Powered Research Discovery</p>
              </div>
            </div>

            {papers.length > 0 && (
              <div className="flex items-center space-x-2">
                <button
                  onClick={exportResults}
                  className="flex items-center space-x-2 px-3 py-2 text-sm bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                >
                  <Download className="h-4 w-4" />
                  <span>Export</span>
                </button>
                <button
                  onClick={clearResults}
                  className="flex items-center space-x-2 px-3 py-2 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
                >
                  <Trash2 className="h-4 w-4" />
                  <span>Clear</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Search Section */}
        <div className="mb-8">
          <div className="bg-white rounded-2xl shadow-xl border border-gray-100 p-6">
            <div className="space-y-6">
              {/* Text Search */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Research Query
                </label>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
                  <input
                    type="text"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && searchPapers()}
                    placeholder="Enter research topic, keywords, or specific questions..."
                    className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
                    disabled={loading}
                  />
                </div>
              </div>

              {/* Action Buttons */}
              <div className="flex flex-col sm:flex-row gap-4">
                <button
                  onClick={() => searchPapers()}
                  disabled={loading || !query.trim()}
                  className="flex-1 flex items-center justify-center space-x-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white py-3 px-6 rounded-lg font-semibold disabled:opacity-50 disabled:cursor-not-allowed hover:from-blue-700 hover:to-purple-700 transition-all duration-200 transform hover:scale-[1.02]"
                >
                  {loading ? (
                    <Loader2 className="h-5 w-5 animate-spin" />
                  ) : (
                    <Search className="h-5 w-5" />
                  )}
                  <span>{loading ? 'Searching...' : 'Search Papers'}</span>
                </button>

                <div className="flex-1">
                  <input
                    type="file"
                    ref={fileInputRef}
                    onChange={handleFileUpload}
                    accept=".txt,.pdf,.md"
                    className="hidden"
                    disabled={loading}
                  />
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    disabled={loading}
                    className="w-full flex items-center justify-center space-x-2 bg-white text-gray-700 py-3 px-6 rounded-lg font-semibold border-2 border-gray-300 disabled:opacity-50 hover:border-blue-500 hover:text-blue-600 transition-all duration-200"
                  >
                    <Upload className="h-5 w-5" />
                    <span>Upload Document</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Status Messages */}
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 rounded-lg p-4 flex items-start space-x-3">
            <AlertCircle className="h-5 w-5 text-red-500 mt-0.5 flex-shrink-0" />
            <div className="text-red-700">{error}</div>
          </div>
        )}

        {uploadStatus && (
          <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4 flex items-start space-x-3">
            <CheckCircle className="h-5 w-5 text-green-500 mt-0.5 flex-shrink-0" />
            <div className="text-green-700">{uploadStatus}</div>
          </div>
        )}

        {/* Search Statistics */}
        {searchStats && (
          <div className="mb-6 bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex flex-wrap items-center gap-4 text-sm text-blue-700">
              <span className="font-medium">Query: "{searchStats.query}"</span>
              <span>•</span>
              <span>{searchStats.total} papers found</span>
              <span>•</span>
              <span>Processed in {searchStats.processingTime}s</span>
            </div>
          </div>
        )}

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center py-12">
            <div className="text-center">
              <Loader2 className="h-8 w-8 animate-spin text-blue-600 mx-auto mb-4" />
              <p className="text-gray-600">Finding relevant research papers...</p>
            </div>
          </div>
        )}

        {/* Results */}
        {papers.length > 0 && !loading && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">
                Research Papers ({papers.length})
              </h2>
            </div>

            <div className="grid gap-6">
              {papers.map((paper, index) => (
                <PaperCard key={paper.id || index} paper={paper} rank={index + 1} />
              ))}
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && papers.length === 0 && !error && (
          <div className="text-center py-12">
            <FileText className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Discover Research Papers
            </h3>
            <p className="text-gray-600 max-w-md mx-auto">
              Enter a research query or upload a document to find semantically similar academic papers using AI-powered search.
            </p>
          </div>
        )}
      </main>
    </div>
  );
};

const PaperCard = ({ paper, rank }) => {
  const [expanded, setExpanded] = useState(false);

  const getSourceBadge = (source) => {
    const badges = {
      'arxiv': { color: 'bg-red-100 text-red-800', label: 'arXiv' },
      'semantic_scholar': { color: 'bg-blue-100 text-blue-800', label: 'Semantic Scholar' },
      'test': { color: 'bg-gray-100 text-gray-800', label: 'Test' }
    };
    return badges[source] || { color: 'bg-gray-100 text-gray-800', label: source };
  };

  const badge = getSourceBadge(paper.source);
  const relevanceScore = paper.relevance_score ? Math.round(paper.relevance_score * 100) : null;

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-all duration-300 overflow-hidden">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-start justify-between mb-4">
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
              {rank}
            </div>
            <div className="flex-1">
              <h3 className="text-lg font-semibold text-gray-900 leading-tight mb-2">
                {paper.title}
              </h3>
              <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
                <span className={`px-2 py-1 rounded-full text-xs font-medium ${badge.color}`}>
                  {badge.label}
                </span>
                {relevanceScore && (
                  <span className="px-2 py-1 bg-green-100 text-green-800 rounded-full text-xs font-medium">
                    {relevanceScore}% match
                  </span>
                )}
                {paper.published && (
                  <div className="flex items-center space-x-1">
                    <Calendar className="h-3 w-3" />
                    <span>{paper.published}</span>
                  </div>
                )}
              </div>
            </div>
          </div>

          {paper.url && (
            <a
              href={paper.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-shrink-0 p-2 text-gray-400 hover:text-blue-600 transition-colors"
              title="Open paper"
            >
              <ExternalLink className="h-5 w-5" />
            </a>
          )}
        </div>

        {/* Authors */}
        {paper.authors && paper.authors.length > 0 && (
          <div className="flex items-center space-x-2 mb-3 text-sm text-gray-600">
            <Users className="h-4 w-4" />
            <span>{paper.authors.slice(0, 3).join(', ')}</span>
            {paper.authors.length > 3 && (
              <span className="text-gray-400">+{paper.authors.length - 3} more</span>
            )}
          </div>
        )}

        {/* AI Explanation */}
        {paper.explanation && (
          <div className="mb-4 p-3 bg-purple-50 rounded-lg border border-purple-200">
            <div className="flex items-start space-x-2">
              <Sparkles className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
              <p className="text-sm text-purple-800 leading-relaxed">
                {paper.explanation}
              </p>
            </div>
          </div>
        )}

        {/* Abstract */}
        <div className="text-sm text-gray-700 leading-relaxed">
          <p className={expanded ? '' : 'line-clamp-3'}>
            {paper.abstract}
          </p>
          {paper.abstract && paper.abstract.length > 300 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 text-blue-600 hover:text-blue-800 font-medium text-sm"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>

        {/* Actions */}
        <div className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <span>ID: {paper.id}</span>
            {paper.citation_count && (
              <span>{paper.citation_count} citations</span>
            )}
          </div>

          {paper.url && (
            <a
              href={paper.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center space-x-2 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
            >
              <span>Read Paper</span>
              <ExternalLink className="h-3 w-3" />
            </a>
          )}
        </div>
      </div>
    </div>
  );
};

export default PaperMind;