import { apiClient } from './api';

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

  // Get current user profile
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
    try {
      const refreshToken = this.getRefreshToken();
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await apiClient.post<APIResponse<AuthTokens>>('/auth/refresh', {
        refresh_token: refreshToken
      });

      if (response.status === 'success' && response.data) {
        // Update stored access token
        localStorage.setItem(this.TOKEN_KEY, response.data.access_token);
        return response.data;
      }

      throw new Error('Token refresh failed');
    } catch (error) {
      console.error('Token refresh failed:', error);
      // Clear auth data if refresh fails
      this.clearAuthData();
      throw error;
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
