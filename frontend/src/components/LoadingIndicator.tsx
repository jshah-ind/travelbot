import React, { useState, useEffect } from 'react';
import { Loader, Clock, AlertCircle } from 'lucide-react';

interface LoadingIndicatorProps {
  isLoading: boolean;
  message?: string;
  showTimeoutWarning?: boolean;
}

const LoadingIndicator: React.FC<LoadingIndicatorProps> = ({ 
  isLoading, 
  message = "Processing your request...", 
  showTimeoutWarning = true 
}) => {
  const [elapsedTime, setElapsedTime] = useState(0);
  const [showWarning, setShowWarning] = useState(false);

  useEffect(() => {
    if (!isLoading) {
      setElapsedTime(0);
      setShowWarning(false);
      return;
    }

    const interval = setInterval(() => {
      setElapsedTime(prev => {
        const newTime = prev + 1;
        // Show warning after 30 seconds
        if (newTime >= 30 && showTimeoutWarning) {
          setShowWarning(true);
        }
        return newTime;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [isLoading, showTimeoutWarning]);

  if (!isLoading) return null;

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="flex justify-start mb-6">
      <div className="flex items-start space-x-3">
        <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
          <Loader className="w-4 h-4 text-gray-600 animate-spin" />
        </div>
        <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm min-w-[300px]">
          <div className="flex items-center gap-2 text-gray-600 mb-2">
            <Clock className="w-4 h-4" />
            <span className="text-sm font-medium">{message}</span>
          </div>
          
          {/* Progress bar */}
          <div className="w-full bg-gray-200 rounded-full h-2 mb-2">
            <div 
              className="bg-blue-500 h-2 rounded-full transition-all duration-1000"
              style={{ 
                width: `${Math.min((elapsedTime / 180) * 100, 100)}%` 
              }}
            />
          </div>
          
          {/* Time elapsed */}
          <div className="flex justify-between items-center text-xs text-gray-500">
            <span>Time elapsed: {formatTime(elapsedTime)}</span>
            <span>Max timeout: 3:00</span>
          </div>
          
          {/* Warning message */}
          {showWarning && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded-md">
              <div className="flex items-center gap-2 text-yellow-700">
                <AlertCircle className="w-4 h-4" />
                <span className="text-xs">
                  This is taking longer than usual. Complex searches may take up to 3 minutes.
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default LoadingIndicator; 