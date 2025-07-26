import React, { useState } from 'react';
import { ExternalLink, Users, Calendar, Sparkles, Copy, Share, Bookmark } from 'lucide-react';
import toast from 'react-hot-toast';

const PaperCard = ({ paper, rank, onBookmark }) => {
  const [expanded, setExpanded] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);

  const getSourceBadge = (source) => {
    const badges = {
      'arxiv': { color: 'bg-red-100 text-red-800 border-red-200', label: 'arXiv' },
      'semantic_scholar': { color: 'bg-blue-100 text-blue-800 border-blue-200', label: 'Semantic Scholar' },
    };
    return badges[source] || { color: 'bg-gray-100 text-gray-800 border-gray-200', label: source };
  };

  const badge = getSourceBadge(paper.source);
  const relevanceScore = paper.relevance_score ? Math.round(paper.relevance_score * 100) : null;

  const copyToClipboard = async (text, type) => {
    try {
      await navigator.clipboard.writeText(text);
      toast.success(`${type} copied to clipboard!`);
    } catch (err) {
      toast.error('Failed to copy to clipboard');
    }
  };

  const sharePaper = async () => {
    if (navigator.share && paper.url) {
      try {
        await navigator.share({
          title: paper.title,
          text: paper.abstract.substring(0, 200) + '...',
          url: paper.url,
        });
      } catch (err) {
        copyToClipboard(paper.url, 'Paper URL');
      }
    } else {
      copyToClipboard(paper.url, 'Paper URL');
    }
  };

  const handleBookmark = () => {
    setBookmarked(!bookmarked);
    onBookmark?.(paper, !bookmarked);
    toast.success(bookmarked ? 'Removed from bookmarks' : 'Added to bookmarks');
  };

  return (
    <article className="bg-white rounded-xl shadow-lg border border-gray-100 hover:shadow-xl transition-all duration-300 overflow-hidden group">
      <div className="p-6">
        {/* Header */}
        <header className="flex items-start justify-between mb-4">
          <div className="flex items-start space-x-3 flex-1">
            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-r from-blue-600 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
              #{rank}
            </div>
            <div className="flex-1 min-w-0">
              <h3 className="text-lg font-semibold text-gray-900 leading-tight mb-2 group-hover:text-blue-600 transition-colors">
                {paper.title}
              </h3>
              <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
                <span className={`px-2 py-1 rounded-full text-xs font-medium border ${badge.color}`}>
                  {badge.label}
                </span>
                {relevanceScore && (
                  <span className="px-2 py-1 bg-green-100 text-green-800 border border-green-200 rounded-full text-xs font-medium">
                    {relevanceScore}% match
                  </span>
                )}
                {paper.published && (
                  <div className="flex items-center space-x-1">
                    <Calendar className="h-3 w-3" />
                    <span>{paper.published}</span>
                  </div>
                )}
                {paper.citation_count && (
                  <span className="text-xs text-gray-500">
                    {paper.citation_count} citations
                  </span>
                )}
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <button
              onClick={handleBookmark}
              className={`p-2 rounded-lg transition-colors ${
                bookmarked
                  ? 'text-yellow-600 bg-yellow-50 hover:bg-yellow-100'
                  : 'text-gray-400 hover:text-yellow-600 hover:bg-gray-50'
              }`}
              title={bookmarked ? 'Remove bookmark' : 'Bookmark paper'}
            >
              <Bookmark className="h-4 w-4" fill={bookmarked ? 'currentColor' : 'none'} />
            </button>

            <button
              onClick={sharePaper}
              className="p-2 text-gray-400 hover:text-blue-600 hover:bg-gray-50 rounded-lg transition-colors"
              title="Share paper"
            >
              <Share className="h-4 w-4" />
            </button>

            {paper.url && (
              <a
                href={paper.url}
                target="_blank"
                rel="noopener noreferrer"
                className="p-2 text-gray-400 hover:text-blue-600 hover:bg-gray-50 rounded-lg transition-colors"
                title="Open paper"
              >
                <ExternalLink className="h-4 w-4" />
              </a>
            )}
          </div>
        </header>

        {/* Authors */}
        {paper.authors && paper.authors.length > 0 && (
          <div className="flex items-center space-x-2 mb-3 text-sm text-gray-600">
            <Users className="h-4 w-4 flex-shrink-0" />
            <div className="flex flex-wrap items-center gap-1">
              {paper.authors.slice(0, 3).map((author, index) => (
                <span key={index}>
                  {author}
                  {index < Math.min(paper.authors.length, 3) - 1 && ', '}
                </span>
              ))}
              {paper.authors.length > 3 && (
                <span className="text-gray-400 ml-1">
                  +{paper.authors.length - 3} more
                </span>
              )}
            </div>
          </div>
        )}

        {/* AI Explanation */}
        {paper.explanation && (
          <div className="mb-4 p-3 bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border border-purple-200">
            <div className="flex items-start space-x-2">
              <Sparkles className="h-4 w-4 text-purple-600 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <p className="text-sm text-purple-800 leading-relaxed">
                  {paper.explanation}
                </p>
                <button
                  onClick={() => copyToClipboard(paper.explanation, 'Explanation')}
                  className="mt-2 text-xs text-purple-600 hover:text-purple-800 flex items-center space-x-1"
                >
                  <Copy className="h-3 w-3" />
                  <span>Copy explanation</span>
                </button>
              </div>
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
              className="mt-2 text-blue-600 hover:text-blue-800 font-medium text-sm transition-colors"
            >
              {expanded ? 'Show less' : 'Show more'}
            </button>
          )}
        </div>

        {/* Footer Actions */}
        <footer className="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
          <div className="flex items-center space-x-4 text-xs text-gray-500">
            <span>ID: {paper.id}</span>
            {paper.pdf_url && (
              <a
                href={paper.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-red-600 hover:text-red-800 font-medium"
              >
                PDF
              </a>
            )}
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => copyToClipboard(paper.title, 'Title')}
              className="px-2 py-1 text-xs text-gray-600 hover:text-gray-800 hover:bg-gray-50 rounded transition-colors"
            >
              Copy Title
            </button>

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
        </footer>
      </div>
    </article>
  );
};

export default PaperCard;
