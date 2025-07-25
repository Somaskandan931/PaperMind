import React from 'react';
import PaperCard from './PaperCard';

const ResultsList = ({ papers }) => {
  if (papers.length === 0) {
    return <p>No results found.</p>;
  }

  return (
    <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-4">
      {papers.map((paper, idx) => (
        <PaperCard key={idx} paper={paper} />
      ))}
    </div>
  );
};

export default ResultsList;
