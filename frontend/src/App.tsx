import React from 'react';
import Sidebar from './components/Sidebar';
import ChatHeader from './components/ChatHeader';
import ChatInterface from './components/ChatInterface';
import { AuthProvider } from './contexts/AuthContext';

function App() {
  return (
    <AuthProvider>
      <div className="h-screen bg-gray-50 flex">
        {/* Sidebar - Hidden on mobile, visible on desktop */}
        <div className="hidden lg:block">
          <Sidebar />
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col min-w-0">
          <ChatHeader />
          <div className="flex-1 min-h-0">
            <ChatInterface />
          </div>
        </div>
      </div>
    </AuthProvider>
  );
}

export default App;