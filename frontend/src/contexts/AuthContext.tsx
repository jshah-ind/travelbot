import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { authService, User, LoginRequest, SignupRequest } from '../services/authService';

interface AuthContextType {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  signin: (data: LoginRequest) => Promise<void>;
  signup: (data: SignupRequest) => Promise<void>;
  signout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const isAuthenticated = !!user && authService.isAuthenticated();

  // Initialize auth state
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setIsLoading(true);
        
        // Check if user is stored locally
        const storedUser = authService.getUser();
        const token = authService.getToken();
        
        if (storedUser && token) {
          try {
            // Verify token is still valid by fetching current user
            const currentUser = await authService.getCurrentUser();
            setUser(currentUser);
          } catch (error) {
            console.error('Token validation failed:', error);
            // Clear invalid auth data
            await authService.signout();
            setUser(null);
          }
        }
      } catch (error) {
        console.error('Auth initialization failed:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
      }
    };

    initializeAuth();
  }, []);

  const signin = async (data: LoginRequest) => {
    try {
      setIsLoading(true);
      const response = await authService.signin(data);
      
      if (response.status === 'success' && response.data) {
        setUser(response.data.user);
      } else {
        throw new Error(response.message || 'Signin failed');
      }
    } catch (error) {
      console.error('Signin error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (data: SignupRequest) => {
    try {
      setIsLoading(true);
      const response = await authService.signup(data);
      
      if (response.status === 'success' && response.data) {
        setUser(response.data.user);
      } else {
        throw new Error(response.message || 'Signup failed');
      }
    } catch (error) {
      console.error('Signup error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signout = async () => {
    try {
      setIsLoading(true);
      await authService.signout();
      setUser(null);
    } catch (error) {
      console.error('Signout error:', error);
      // Clear user state even if API call fails
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    try {
      if (authService.isAuthenticated()) {
        const currentUser = await authService.getCurrentUser();
        setUser(currentUser);
      }
    } catch (error) {
      console.error('Refresh user failed:', error);
      // If refresh fails, sign out user
      await signout();
    }
  };

  const value: AuthContextType = {
    user,
    isAuthenticated,
    isLoading,
    signin,
    signup,
    signout,
    refreshUser,
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};
