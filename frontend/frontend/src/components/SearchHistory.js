import React, { useState, useEffect } from 'react';
import { History, Search, Trash2, Clock } from 'lucide-react';

const SearchHistory = ({ onSelectQuery }) => {
  const [history, setHistory] = useState([]);
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    const savedHistory = localStorage.getItem('papermind_search_history');
    if (savedHistory) {
      setHistory(JSON.parse(savedHistory));
    }
  }, []);

  const addToHistory = (query) => {
    const newHistory = [
      { query, timestamp: Date.now() },
      ...history.filter(item => item.query !== query)
    ].slice(0, 10); // Keep only last 10 searches

    setHistory(newHistory);
    localStorage.setItem('papermind_search_history', JSON.stringify(newHistory));
  };

  const clearHistory = () => {
    setHistory([]);
    localStorage.removeItem('papermind_search_history');
  };

  const formatTime = (timestamp) => {
    const now = Date.now();
    const diff = now - timestamp;
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  // Expose addToHistory function to parent
  React.useImperativeHandle(React.forwardRef((props, ref) => ({
    addToHistory
  })), [history]);

  if (history.length === 0) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-2 px-3 py-2 text-sm text-gray-600 hover:text-gray-900 border border-gray-300 rounded-lg hover:border-gray-400 transition-colors"
      >
        <History className="h-4 w-4" />
        <span>History</span>
      </button>

      {isOpen && (
        <div className="absolute top-full mt-2 w-80 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
          <div className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="font-medium text-gray-900">Recent Searches</h3>
              <button
                onClick={clearHistory}
                className="text-gray-400 hover:text-red-600 transition-colors"
                title="Clear history"
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>

            <div className="space-y-2 max-h-64 overflow-y-auto">
              {history.map((item, index) => (
                <button
                  key={index}
                  onClick={() => {
                    onSelectQuery(item.query);
                    setIsOpen(false);
                  }}
                  className="w-full flex items-center justify-between p-2 text-left hover:bg-gray-50 rounded-lg transition-colors group"
                >
                  <div className="flex items-center space-x-2 flex-1 min-w-0">
                    <Search className="h-4 w-4 text-gray-400 flex-shrink-0" />
                    <span className="text-sm text-gray-700 truncate">
                      {item.query}
                    </span>
                  </div>
                  <div className="flex items-center space-x-1 text-xs text-gray-500">
                    <Clock className="h-3 w-3" />
                    <span>{formatTime(item.timestamp)}</span>
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SearchHistory;