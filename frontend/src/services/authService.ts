import { apiClient, setAuthServiceReference } from './api';

export interface User {
  id: number;
  user_id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface SignupRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface AuthResponse {
  status: string;
  message: string;
  data: {
    user: User;
    tokens: AuthTokens;
  };
}

export interface APIResponse<T = any> {
  status: string;
  message: string;
  data?: T;
}

class AuthService {
  private readonly TOKEN_KEY = 'travel_agent_token';
  private readonly REFRESH_TOKEN_KEY = 'travel_agent_refresh_token';
  private readonly USER_KEY = 'travel_agent_user';
  private refreshPromise: Promise<AuthTokens> | null = null;

  constructor() {
    // Set reference in API client to avoid circular imports
    setAuthServiceReference(this);
  }

  // Get stored token
  getToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY);
  }

  // Get stored refresh token
  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  // Get stored user
  getUser(): User | null {
    const userStr = localStorage.getItem(this.USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
  }

  // Store authentication data
  private storeAuthData(tokens: AuthTokens, user: User): void {
    localStorage.setItem(this.TOKEN_KEY, tokens.access_token);
    localStorage.setItem(this.REFRESH_TOKEN_KEY, tokens.refresh_token);
    localStorage.setItem(this.USER_KEY, JSON.stringify(user));
  }

  // Clear authentication data
  private clearAuthData(): void {
    localStorage.removeItem(this.TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    localStorage.removeItem(this.USER_KEY);
  }

  // Check if user is authenticated
  isAuthenticated(): boolean {
    const token = this.getToken();
    const user = this.getUser();
    return !!(token && user);
  }

  // Get authorization headers
  getAuthHeaders(): Record<string, string> {
    const token = this.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  // Sign up new user
  async signup(data: SignupRequest): Promise<AuthResponse> {
    try {
      console.log('🔍 Frontend: Making signup request with data:', data);
      console.log('🔍 Frontend: Data type:', typeof data);
      console.log('🔍 Frontend: Data keys:', Object.keys(data));
      console.log('🔍 Frontend: JSON stringified data:', JSON.stringify(data));
      const response = await apiClient.post<AuthResponse>('/auth/signup', data);
      console.log('🔍 Frontend: Received signup response:', response);

      if (response.status === 'success' && response.data) {
        this.storeAuthData(response.data.tokens, response.data.user);
      }

      return response;
    } catch (error) {
      console.error('🔍 Frontend: Signup failed with error:', error);
      throw error;
    }
  }

  // Sign in user
  async signin(data: LoginRequest): Promise<AuthResponse> {
    try {
      const response = await apiClient.post<AuthResponse>('/auth/signin', data);
      
      if (response.status === 'success' && response.data) {
        this.storeAuthData(response.data.tokens, response.data.user);
      }
      
      return response;
    } catch (error) {
      console.error('Signin failed:', error);
      throw error;
    }
  }

  // Sign out user
  async signout(): Promise<void> {
    try {
      // Call logout endpoint if available
      const token = this.getToken();
      if (token) {
        await apiClient.post('/auth/logout', {}, this.getAuthHeaders());
      }
    } catch (error) {
      console.error('Logout API call failed:', error);
      // Continue with local logout even if API call fails
    } finally {
      this.clearAuthData();
    }
  }

  // Get current user profile with automatic token refresh
  async getCurrentUser(): Promise<User> {
    try {
      const response = await apiClient.get<APIResponse<{ user: User }>>(
        '/auth/me', 
        this.getAuthHeaders()
      );
      
      if (response.status === 'success' && response.data) {
        // Update stored user data
        localStorage.setItem(this.USER_KEY, JSON.stringify(response.data.user));
        return response.data.user;
      }
      
      throw new Error('Failed to get user profile');
    } catch (error) {
      console.error('Get current user failed:', error);
      throw error;
    }
  }

  // Refresh access token
  async refreshToken(): Promise<AuthTokens> {
    // If there's already a refresh in progress, return that promise
    if (this.refreshPromise) {
      return this.refreshPromise;
    }

    this.refreshPromise = this._performTokenRefresh();
    
    try {
      const result = await this.refreshPromise;
      return result;
    } finally {
      this.refreshPromise = null;
    }
  }

  private async _performTokenRefresh(): Promise<AuthTokens> {
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      console.log('🔄 AuthService: Attempting to refresh token...');
      
      // Make direct fetch call to avoid circular refresh
      const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://0.0.0.0:8000'}/auth/refresh`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          refresh_token: refreshToken
        })
      });

      if (!response.ok) {
        throw new Error(`Token refresh failed: ${response.status}`);
      }

      const data = await response.json();
      console.log('✅ AuthService: Token refresh response:', data);

      if (data.status === 'success' && data.data) {
        // Update stored access token
        localStorage.setItem(this.TOKEN_KEY, data.data.access_token);
        // Also update refresh token if provided
        if (data.data.refresh_token) {
          localStorage.setItem(this.REFRESH_TOKEN_KEY, data.data.refresh_token);
        }
        console.log('✅ AuthService: Token refreshed successfully');
        return data.data;
      }

      throw new Error('Token refresh failed: Invalid response');
    } catch (error) {
      console.error('❌ AuthService: Token refresh failed:', error);
      // Clear auth data if refresh fails
      this.clearAuthData();
      throw error;
    }
  }

  // Validate current session and try to refresh if needed
  async validateSession(): Promise<User | null> {
    try {
      const token = this.getToken();
      const user = this.getUser();
      
      if (!token || !user) {
        return null;
      }

      // Try to get current user (this will auto-refresh token if needed)
      const currentUser = await this.getCurrentUser();
      return currentUser;
    } catch (error) {
      console.error('Session validation failed:', error);
      
      // Try to refresh token if we have a refresh token
      const refreshToken = this.getRefreshToken();
      if (refreshToken) {
        try {
          console.log('🔄 AuthService: Attempting session recovery via token refresh...');
          await this.refreshToken();
          // Try to get user again after refresh
          const currentUser = await this.getCurrentUser();
          return currentUser;
        } catch (refreshError) {
          console.error('❌ AuthService: Session recovery failed:', refreshError);
          this.clearAuthData();
          return null;
        }
      }
      
      // No refresh token available, clear auth data
      this.clearAuthData();
      return null;
    }
  }

  // Update user profile
  async updateProfile(data: Partial<User>): Promise<User> {
    try {
      const response = await apiClient.post<APIResponse<{ user: User }>>(
        '/auth/profile', 
        data, 
        this.getAuthHeaders()
      );
      
      if (response.status === 'success' && response.data) {
        // Update stored user data
        localStorage.setItem(this.USER_KEY, JSON.stringify(response.data.user));
        return response.data.user;
      }
      
      throw new Error('Profile update failed');
    } catch (error) {
      console.error('Profile update failed:', error);
      throw error;
    }
  }
}

export const authService = new AuthService();
