import React from 'react';

const PaperCard = ({ paper }) => {
  return (
    <div className="border rounded p-4 shadow-sm hover:shadow-md transition">
      <h3 className="text-lg font-semibold">{paper.title}</h3>
      <p className="text-sm text-gray-600 mb-2">by {paper.authors?.join(', ')}</p>
      <p className="text-sm mb-2 line-clamp-4">{paper.abstract}</p>
      {paper.explanation && (
        <p className="mt-3 text-sm text-blue-700 italic">AI Insight: {paper.explanation}</p>
      )}
      <a
        href={paper.url}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-3 inline-block text-sm text-blue-600 hover:underline"
      >
        View Full Paper
      </a>
    </div>
  );
};

export default PaperCard;
