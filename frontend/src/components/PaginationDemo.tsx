import React, { useState } from 'react';

interface PaginationDemoProps {
  totalItems: number;
  itemsPerPage?: number;
}

const PaginationDemo: React.FC<PaginationDemoProps> = ({ 
  totalItems, 
  itemsPerPage = 10 
}) => {
  const [displayedItems, setDisplayedItems] = useState(itemsPerPage);
  
  const hasMoreItems = displayedItems < totalItems;
  const remainingItems = totalItems - displayedItems;
  
  const handleShowMore = () => {
    setDisplayedItems(prev => Math.min(prev + itemsPerPage, totalItems));
  };
  
  const handleShowAll = () => {
    setDisplayedItems(totalItems);
  };
  
  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">Pagination Demo</h2>
      
      <div className="mb-4">
        <p>Showing {displayedItems} of {totalItems} items</p>
      </div>
      
      {/* Simulated items */}
      <div className="space-y-2 mb-6">
        {Array.from({ length: displayedItems }, (_, i) => (
          <div key={i} className="p-3 bg-gray-100 rounded">
            Item {i + 1}
          </div>
        ))}
      </div>
      
      {/* Show More Button */}
      {hasMoreItems && (
        <div className="flex justify-center gap-4">
          <button
            onClick={handleShowMore}
            className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
          >
            Show More ({remainingItems} remaining)
          </button>
          
          {totalItems > 20 && (
            <button
              onClick={handleShowAll}
              className="bg-gray-600 text-white px-4 py-2 rounded hover:bg-gray-700"
            >
              Show All
            </button>
          )}
        </div>
      )}
      
      {!hasMoreItems && (
        <p className="text-center text-gray-600">All items displayed</p>
      )}
    </div>
  );
};

export default PaginationDemo; 