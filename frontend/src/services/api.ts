const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://104.225.217.245:8000'; // Your flight search API

// Import authService to handle token refresh
let authService: any = null;

// Function to set authService reference (to avoid circular imports)
export const setAuthServiceReference = (service: any) => {
  authService = service;
};

export const apiClient = {
  async request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
    const url = `${API_BASE_URL}${endpoint}`;

    // Build headers separately to avoid any spread issues
    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    // Add any additional headers
    if (options.headers) {
      Object.assign(headers, options.headers);
    }

    const config: RequestInit = {
      ...options,
      headers,
    };

    console.log(`🔍 API: Making ${options.method || 'GET'} request to ${url}`);
    console.log(`🔍 API: Request config:`, config);
    console.log(`🔍 API: Request body:`, config.body);
    console.log(`🔍 API: Request headers:`, config.headers);

    try {
      // Create AbortController for timeout
      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 180000); // 180 seconds timeout
      
      const response = await fetch(url, {
        ...config,
        signal: controller.signal
      });
      
      clearTimeout(timeoutId);
      console.log(`🔍 API: Response status: ${response.status}, ok: ${response.ok}`);

      // Handle 401 Unauthorized - try to refresh token
      if (response.status === 401 && authService) {
        console.log('🔄 API: Received 401, attempting token refresh...');
        try {
          await authService.refreshToken();
          console.log('✅ API: Token refreshed successfully, retrying request...');
          
          // Update headers with new token
          const newHeaders = { ...headers };
          const authHeaders = authService.getAuthHeaders();
          Object.assign(newHeaders, authHeaders);
          
          // Retry the request with new token
          const retryConfig: RequestInit = {
            ...options,
            headers: newHeaders,
          };
          
          const retryResponse = await fetch(url, retryConfig);
          console.log(`🔍 API: Retry response status: ${retryResponse.status}, ok: ${retryResponse.ok}`);
          
          if (!retryResponse.ok) {
            const errorData = await retryResponse.json().catch(() => ({}));
            console.log(`🔍 API: Retry error response data:`, errorData);
            throw new Error(errorData.detail || errorData.error || errorData.message || `API Error: ${retryResponse.status}`);
          }
          
          const retryResponseData = await retryResponse.json();
          console.log(`🔍 API: Retry success response data:`, retryResponseData);
          return retryResponseData;
          
        } catch (refreshError) {
          console.error('❌ API: Token refresh failed:', refreshError);
          // If refresh fails, the authService will handle clearing auth data
          throw new Error('Session expired. Please login again.');
        }
      }

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        console.log(`🔍 API: Error response data:`, errorData);

        // Handle FastAPI validation errors (422)
        if (response.status === 422 && errorData.detail) {
          if (Array.isArray(errorData.detail)) {
            // Multiple validation errors
            const messages = errorData.detail.map((err: any) => err.msg || err.message).join(', ');
            console.log(`🔍 API: Validation error messages:`, messages);
            throw new Error(messages);
          } else if (typeof errorData.detail === 'string') {
            console.log(`🔍 API: Single validation error:`, errorData.detail);
            throw new Error(errorData.detail);
          }
        }

        // Handle other API errors
        const errorMessage = errorData.detail || errorData.error || errorData.message || `API Error: ${response.status}`;
        console.log(`🔍 API: Final error message:`, errorMessage);
        throw new Error(errorMessage);
      }

      const responseData = await response.json();
      console.log(`🔍 API: Success response data:`, responseData);
      return responseData;
    } catch (error) {
      console.error('🔍 API: Request failed with error:', error);
      
      // Handle timeout specifically
      if (error instanceof Error && error.name === 'AbortError') {
        throw new Error('Request timeout after 180 seconds. Please try again in a moment.');
      }
      
      throw error;
    }
  },

  get<T>(endpoint: string, headers?: Record<string, string>): Promise<T> {
    return this.request<T>(endpoint, { method: 'GET', headers: headers || {} });
  },

  post<T>(endpoint: string, data?: any, headers?: Record<string, string>): Promise<T> {
    const requestOptions: RequestInit = {
      method: 'POST',
      headers: headers || {},
    };

    if (data) {
      requestOptions.body = JSON.stringify(data);
    }

    return this.request<T>(endpoint, requestOptions);
  }
};