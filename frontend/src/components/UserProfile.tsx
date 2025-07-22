import React, { useState } from 'react';
import { User, LogOut, Settings, MessageSquare, Calendar } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';

interface UserProfileProps {
  isOpen: boolean;
  onClose: () => void;
}

const UserProfile: React.FC<UserProfileProps> = ({ isOpen, onClose }) => {
  const { user, signout } = useAuth();
  const [isSigningOut, setIsSigningOut] = useState(false);

  if (!isOpen || !user) return null;

  const handleSignOut = async () => {
    setIsSigningOut(true);
    try {
      await signout();
      onClose();
    } catch (error) {
      console.error('Sign out failed:', error);
    } finally {
      setIsSigningOut(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    });
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Profile</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            ✕
          </button>
        </div>

        {/* Profile Content */}
        <div className="p-6">
          {/* User Avatar and Basic Info */}
          <div className="flex items-center space-x-4 mb-6">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center">
              <User className="w-8 h-8 text-blue-600" />
            </div>
            <div>
              <h3 className="text-lg font-semibold text-gray-900">
                {user.full_name || user.username}
              </h3>
              <p className="text-gray-600">{user.email}</p>
              <div className="flex items-center space-x-2 mt-1">
                <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                  user.is_active 
                    ? 'bg-green-100 text-green-800' 
                    : 'bg-gray-100 text-gray-800'
                }`}>
                  {user.is_active ? 'Active' : 'Inactive'}
                </span>
                {user.is_verified && (
                  <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                    Verified
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* User Details */}
          <div className="space-y-4 mb-6">
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Username</span>
              <span className="font-medium">{user.username}</span>
            </div>
            
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">User ID</span>
              <span className="font-mono text-sm text-gray-500">{user.user_id}</span>
            </div>
            
            <div className="flex items-center justify-between py-2 border-b border-gray-100">
              <span className="text-gray-600">Member since</span>
              <span className="text-sm">{formatDate(user.created_at)}</span>
            </div>
            
            {user.last_login && (
              <div className="flex items-center justify-between py-2 border-b border-gray-100">
                <span className="text-gray-600">Last login</span>
                <span className="text-sm">{formatDate(user.last_login)}</span>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="space-y-2 mb-6">
            <h4 className="text-sm font-medium text-gray-900 mb-3">Quick Actions</h4>
            
            <button className="w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-gray-50 rounded-lg transition-colors">
              <MessageSquare className="w-5 h-5 text-gray-400" />
              <span className="text-gray-700">View Chat History</span>
            </button>
            
            <button className="w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-gray-50 rounded-lg transition-colors">
              <Calendar className="w-5 h-5 text-gray-400" />
              <span className="text-gray-700">Travel Preferences</span>
            </button>
            
            <button className="w-full flex items-center space-x-3 px-4 py-3 text-left hover:bg-gray-50 rounded-lg transition-colors">
              <Settings className="w-5 h-5 text-gray-400" />
              <span className="text-gray-700">Account Settings</span>
            </button>
          </div>

          {/* Sign Out Button */}
          <button
            onClick={handleSignOut}
            disabled={isSigningOut}
            className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-red-50 text-red-600 hover:bg-red-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <LogOut className="w-5 h-5" />
            <span>{isSigningOut ? 'Signing out...' : 'Sign Out'}</span>
          </button>
        </div>
      </div>
    </div>
  );
};

export default UserProfile;
