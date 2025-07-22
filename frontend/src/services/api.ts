const API_BASE_URL = 'http://localhost:8000'; // Your flight search API

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
      const response = await fetch(url, config);
      console.log(`🔍 API: Response status: ${response.status}, ok: ${response.ok}`);

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