import React from 'react';
import EnhancedFlightDisplay from './EnhancedFlightDisplay';

const EmptyStateTest: React.FC = () => {
  // Test with empty flight data
  const emptyFlightData: any[] = [];
  const searchInfo = {
    search_date: '2025-07-29',
    origin: 'DEL',
    destination: 'BOM',
    passengers: 1,
    travel_class: 'ECONOMY'
  };

  return (
    <div className="p-6">
      <h2 className="text-xl font-bold mb-4">Empty State Test</h2>
      <EnhancedFlightDisplay 
        flightData={emptyFlightData} 
        searchInfo={searchInfo} 
      />
    </div>
  );
};

export default EmptyStateTest; 