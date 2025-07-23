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

  // Initialize auth state with improved session validation
  useEffect(() => {
    const initializeAuth = async () => {
      try {
        setIsLoading(true);
        console.log('🔄 AuthContext: Initializing authentication...');
        
        // Use the new validateSession method which handles token refresh
        const validatedUser = await authService.validateSession();
        
        if (validatedUser) {
          console.log('✅ AuthContext: Session validated successfully');
          setUser(validatedUser);
        } else {
          console.log('ℹ️ AuthContext: No valid session found');
          setUser(null);
        }
      } catch (error) {
        console.error('❌ AuthContext: Auth initialization failed:', error);
        setUser(null);
      } finally {
        setIsLoading(false);
        console.log('✅ AuthContext: Auth initialization completed');
      }
    };

    initializeAuth();
  }, []);

  const signin = async (data: LoginRequest) => {
    try {
      setIsLoading(true);
      console.log('🔄 AuthContext: Signing in...');
      const response = await authService.signin(data);
      
      if (response.status === 'success' && response.data) {
        console.log('✅ AuthContext: Signin successful');
        setUser(response.data.user);
      } else {
        throw new Error(response.message || 'Signin failed');
      }
    } catch (error) {
      console.error('❌ AuthContext: Signin error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (data: SignupRequest) => {
    try {
      setIsLoading(true);
      console.log('🔄 AuthContext: Signing up...');
      const response = await authService.signup(data);
      
      if (response.status === 'success' && response.data) {
        console.log('✅ AuthContext: Signup successful');
        setUser(response.data.user);
      } else {
        throw new Error(response.message || 'Signup failed');
      }
    } catch (error) {
      console.error('❌ AuthContext: Signup error:', error);
      throw error;
    } finally {
      setIsLoading(false);
    }
  };

  const signout = async () => {
    try {
      setIsLoading(true);
      console.log('🔄 AuthContext: Signing out...');
      await authService.signout();
      setUser(null);
      console.log('✅ AuthContext: Signout successful');
    } catch (error) {
      console.error('❌ AuthContext: Signout error:', error);
      // Clear user state even if API call fails
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const refreshUser = async () => {
    try {
      console.log('🔄 AuthContext: Refreshing user...');
      const validatedUser = await authService.validateSession();
      
      if (validatedUser) {
        console.log('✅ AuthContext: User refreshed successfully');
        setUser(validatedUser);
      } else {
        console.log('ℹ️ AuthContext: User refresh failed - signing out');
        setUser(null);
      }
    } catch (error) {
      console.error('❌ AuthContext: Refresh user failed:', error);
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
