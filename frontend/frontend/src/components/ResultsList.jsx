import React from 'react';
import PaperCard from './PaperCard';

const ResultsList = ({ papers, selectedIds = new Set(), onToggle = () => {} }) => {
  if (papers.length === 0) {
    return <p className="text-center text-gray-500 py-8">No results found.</p>;
  }

  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
      {papers.map((paper, idx) => (
        <PaperCard
          key={paper.id || idx}
          paper={paper}
          rank={idx + 1}
          selected={selectedIds.has(paper.id)}
          onToggle={() => onToggle(paper.id)}
        />
      ))}
    </div>
  );
};

export default ResultsList;