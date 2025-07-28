import React, { useState } from 'react';

interface TestFlight {
  id: string;
  airline: string;
  flight_number: string;
  price: number;
  duration: string;
  departure_time: string;
  is_direct: boolean;
}

const SortFilterTest: React.FC = () => {
  const [sortBy, setSortBy] = useState<'price' | 'duration' | 'departure'>('price');
  const [airlineFilter, setAirlineFilter] = useState('');
  const [showOnlyDirect, setShowOnlyDirect] = useState(false);

  // Test data
  const testFlights: TestFlight[] = [
    {
      id: '1',
      airline: 'AI',
      flight_number: 'AI2941',
      price: 5891,
      duration: 'PT2H15M',
      departure_time: '16:50',
      is_direct: true
    },
    {
      id: '2',
      airline: '6E',
      flight_number: '6E345',
      price: 3800,
      duration: 'PT1H55M',
      departure_time: '14:15',
      is_direct: true
    },
    {
      id: '3',
      airline: 'SG',
      flight_number: 'SG123',
      price: 4200,
      duration: 'PT2H30M',
      departure_time: '18:00',
      is_direct: false
    },
    {
      id: '4',
      airline: 'AI',
      flight_number: 'AI2420',
      price: 6200,
      duration: 'PT2H20M',
      departure_time: '14:55',
      is_direct: true
    }
  ];

  // Parse duration helper
  const parseDuration = (duration: string): number => {
    const match = duration?.match(/PT(?:(\d+)H)?(?:(\d+)M)?/);
    if (!match) return 0;
    const hours = parseInt(match[1] || '0');
    const minutes = parseInt(match[2] || '0');
    return hours * 60 + minutes;
  };

  // Airline mapping
  const airlineNames: Record<string, string> = {
    'AI': 'Air India',
    '6E': 'IndiGo',
    'SG': 'SpiceJet'
  };

  // Process flights
  let processedFlights = [...testFlights];

  // Filter by direct flights
  if (showOnlyDirect) {
    processedFlights = processedFlights.filter(f => f.is_direct);
  }

  // Filter by airline
  if (airlineFilter.trim()) {
    const filterLower = airlineFilter.toLowerCase();
    processedFlights = processedFlights.filter(f => {
      const airlineName = airlineNames[f.airline] || f.airline;
      return airlineName.toLowerCase().includes(filterLower) || 
             f.airline.toLowerCase().includes(filterLower) ||
             f.flight_number.toLowerCase().includes(filterLower);
    });
  }

  // Sort
  processedFlights.sort((a, b) => {
    switch (sortBy) {
      case 'price':
        return a.price - b.price;
      case 'duration':
        return parseDuration(a.duration) - parseDuration(b.duration);
      case 'departure':
        return a.departure_time.localeCompare(b.departure_time);
      default:
        return 0;
    }
  });

  const formatDuration = (duration: string): string => {
    const totalMinutes = parseDuration(duration);
    const hours = Math.floor(totalMinutes / 60);
    const minutes = totalMinutes % 60;
    return `${hours}h ${minutes}m`;
  };

  return (
    <div className="p-6 bg-white rounded-lg shadow">
      <h2 className="text-xl font-bold mb-4">Sort & Filter Test</h2>
      
      {/* Controls */}
      <div className="flex flex-wrap items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <select 
            value={sortBy} 
            onChange={(e) => setSortBy(e.target.value as 'price' | 'duration' | 'departure')}
            className="border rounded px-3 py-1 text-sm"
          >
            <option value="price">Sort by Price</option>
            <option value="duration">Sort by Duration</option>
            <option value="departure">Sort by Departure</option>
          </select>
        </div>

        {/* <div className="flex items-center gap-2">
          <input 
            type="text"
            placeholder="Filter by airline..."
            value={airlineFilter}
            onChange={(e) => setAirlineFilter(e.target.value)}
            className="border rounded px-3 py-1 text-sm w-48"
          />
          {airlineFilter && (
            <button
              onClick={() => setAirlineFilter('')}
              className="text-gray-500 hover:text-gray-700 text-sm"
            >
              ✕
            </button>
          )}
        </div> */}

        <label className="flex items-center gap-2 text-sm">
          <input 
            type="checkbox" 
            checked={showOnlyDirect}
            onChange={(e) => setShowOnlyDirect(e.target.checked)}
            className="rounded"
          />
          Direct flights only
        </label>
      </div>

      {/* Active Filters */}
      {(showOnlyDirect || airlineFilter) && (
        <div className="bg-blue-50 p-3 rounded-lg border border-blue-200 mb-4">
          <div className="text-sm text-blue-800">
            <span className="font-medium">Active filters:</span>
            {showOnlyDirect && <span className="ml-2 bg-blue-200 px-2 py-1 rounded">Direct flights only</span>}
            {airlineFilter && <span className="ml-2 bg-blue-200 px-2 py-1 rounded">Airline: {airlineFilter}</span>}
          </div>
        </div>
      )}

      {/* Results */}
      <div className="space-y-2">
        <div className="text-sm text-gray-600 mb-2">
          Showing {processedFlights.length} of {testFlights.length} flights
        </div>
        
        {processedFlights.map((flight) => (
          <div key={flight.id} className="p-3 bg-gray-100 rounded flex justify-between items-center">
            <div>
              <div className="font-medium">
                {airlineNames[flight.airline] || flight.airline} {flight.flight_number}
              </div>
              <div className="text-sm text-gray-600">
                {flight.departure_time} • {formatDuration(flight.duration)} • {flight.is_direct ? 'Direct' : '1 stop'}
              </div>
            </div>
            <div className="text-right">
              <div className="font-bold">₹{flight.price}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SortFilterTest; 