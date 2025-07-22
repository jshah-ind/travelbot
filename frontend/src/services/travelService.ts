// Enhanced travelService.ts - Using new flight search API with fallback
import { apiClient } from './api';
import { authService } from './authService';
import { chatHistoryService } from './chatHistoryService';

export const travelService = {
  // Parse natural language flight queries into structured parameters
  parseFlightQuery(query: string): any {
    const lowerQuery = query.toLowerCase();
    
    // Common city mappings
    const cityMappings: { [key: string]: string } = {
      'ahmedabad': 'Ahmedabad',
      'kochi': 'Kochi', 
      'mumbai': 'Mumbai',
      'delhi': 'Delhi',
      'bangalore': 'Bangalore',
      'chennai': 'Chennai',
      'kolkata': 'Kolkata',
      'hyderabad': 'Hyderabad'
    };
    
    // Extract origin and destination
    let origin = '';
    let destination = '';
    
    // Look for "from X to Y" pattern
    const fromToMatch = lowerQuery.match(/from\s+(\w+)\s+to\s+(\w+)/);
    if (fromToMatch) {
      origin = cityMappings[fromToMatch[1]] || fromToMatch[1];
      destination = cityMappings[fromToMatch[2]] || fromToMatch[2];
    } else {
      // Look for "X to Y" pattern
      const toMatch = lowerQuery.match(/(\w+)\s+to\s+(\w+)/);
      if (toMatch) {
        origin = cityMappings[toMatch[1]] || toMatch[1];
        destination = cityMappings[toMatch[2]] || toMatch[2];
      }
    }
    
    // Extract date
    let departure_date = '';
    if (lowerQuery.includes('tomorrow')) {
      const tomorrow = new Date();
      tomorrow.setDate(tomorrow.getDate() + 1);
      departure_date = tomorrow.toISOString().split('T')[0];
    } else if (lowerQuery.includes('today')) {
      departure_date = new Date().toISOString().split('T')[0];
    }
    
    // Extract class
    let travel_class = 'ECONOMY';
    if (lowerQuery.includes('business')) {
      travel_class = 'BUSINESS';
    } else if (lowerQuery.includes('first')) {
      travel_class = 'FIRST';
    }
    
    return {
      origin,
      destination,
      departure_date,
      travel_class,
      passengers: 1
    };
  },

  async searchFlightsNaturalLanguage(query: string, sessionId?: string): Promise<any> {
    try {
      console.log('🔍 Calling simple backend API with query:', query);

      // Validate input
      if (!query || typeof query !== 'string' || query.trim().length === 0) {
        throw new Error('Query cannot be empty');
      }

      // Use our simple backend's /search endpoint
      try {
        const user = authService.getUser();
        const isAuthenticated = authService.isAuthenticated();

        // AUTHENTICATION IS NOW REQUIRED
        if (!isAuthenticated) {
          throw new Error('Authentication required. Please sign up or login to search for flights.');
        }

        // Prepare search payload for our simple backend
        const searchPayload = {
          query: query.trim()
        };

        console.log('📤 Calling simple backend /search endpoint with payload:', searchPayload);

        // Prepare headers with authentication (now required)
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
          ...authService.getAuthHeaders()
        };

        const searchResponse = await Promise.race([
          fetch('http://localhost:8000/search', {
            method: 'POST',
            headers,
            body: JSON.stringify(searchPayload)
          }),
          new Promise((_, reject) =>
            setTimeout(() => reject(new Error('Search API timeout')), 120000) // 2 minutes for flight searches
          )
        ]) as Response;

        console.log('📡 Search Response Status:', searchResponse.status);

        if (searchResponse.ok) {
          const searchData = await searchResponse.json();
          console.log('✅ Search endpoint succeeded:', searchData);

          // Transform the response to match expected format
          if (searchData.status === 'success' && searchData.flights && searchData.flights.length > 0) {
            return {
              status: 'success',
              data: {
                flights: searchData.flights,
                message: searchData.message,
                search_info: searchData.search_info
              },
              source: 'simple_backend'
            };
          } else if (searchData.status === 'error') {
            throw new Error(searchData.message || 'Search failed');
          }
        } else {
          const errorText = await searchResponse.text();
          console.log('❌ Search endpoint failed:', errorText);
          throw new Error(`Search API returned ${searchResponse.status}: ${errorText}`);
        }

      } catch (searchError) {
        console.log('❌ Search endpoint error:', searchError);
        throw searchError;
      }

      // If search failed, use mock data as fallback
      console.log('🎭 Search failed, using mock data as fallback');
      return await this.getMockFlightResponse(query);
      
    } catch (error) {
      console.error('💥 Unexpected error in searchFlightsNaturalLanguage:', error);
      
      const errorMessage = error instanceof Error ? error.message : String(error);
      
      return {
        status: 'error',
        error: `Unexpected error: ${errorMessage}`,
        suggestions: [
          'Check your network connection',
          'Ensure API server is running',
          'Try again in a moment'
        ]
      };
    }
  },

  // Alternative method for testing
  async searchFlightsAlternative(query: string): Promise<any> {
    console.log('🔄 Using alternative search method for:', query);
    return this.searchFlightsNaturalLanguage(query);
  },

  // Mock response for testing when API is down
  async getMockFlightResponse(query: string): Promise<any> {
    console.log('🎭 Using mock response for:', query);

    const mockFlights = [
      {
        id: 'MOCK001',
        airline: 'Air India',
        flight_number: 'AI 131',
        origin: 'Delhi',
        destination: 'Mumbai',
        departure_time: '08:00',
        arrival_time: '10:30',
        duration: '2h 30m',
        price: '₹4,500',
        travel_class: 'Economy'
      },
      {
        id: 'MOCK002',
        airline: 'IndiGo',
        flight_number: '6E 345',
        origin: 'Delhi',
        destination: 'Mumbai',
        departure_time: '14:15',
        arrival_time: '16:45',
        duration: '2h 30m',
        price: '₹3,800',
        travel_class: 'Economy'
      }
    ];

    return {
      status: 'success',
      data: {
        flights: mockFlights,
        message: `Found ${mockFlights.length} mock flights for your query: "${query}". (Note: This is demo data as the live API is currently unavailable)`
      },
      source: 'mock_data'
    };
  },

  // Debug method to test server responsiveness
  async debugServerConnection(): Promise<any> {
    try {
      console.log('🔬 Testing server connection...');
      
      // Test health endpoint
      const healthTest = await fetch('http://localhost:8000/health');
      console.log('📡 Health endpoint status:', healthTest.status);
      
      if (healthTest.ok) {
        const healthData = await healthTest.json();
        console.log('📡 Health endpoint data:', healthData);
        return {
          status: 'success',
          health_check: healthData
        };
      }
      
      return {
        status: 'error',
        error: 'Health check failed'
      };
      
    } catch (error) {
      console.error('🔴 Server connection test failed:', error);
      const errorMessage = error instanceof Error ? error.message : String(error);
      return {
        error: errorMessage,
        suggestion: 'Server may not be running on port 8000'
      };
    }
  }
};
