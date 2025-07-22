// src/components/ChatInterface.tsx
import React, { useState, useRef, useEffect } from 'react';
import { Send, Loader, User, Bot } from 'lucide-react';
import { useChatWithAuth } from '../hooks/useChatWithAuth';
import EnhancedFlightDisplay from './EnhancedFlightDisplay';
import { MonthSearchConfirmation } from './MonthSearchConfirmation';
import { MonthSearchProgress } from './MonthSearchProgress';

const ChatInterface: React.FC = () => {
  const {
    messages,
    isLoading,
    error,
    currentSession,
    sendMessage,
    handleQuickAction,
    isAuthenticated
  } = useChatWithAuth();

  const [inputValue, setInputValue] = useState('');
  
  // ✅ NEW: Month search state
  const [showMonthWarning, setShowMonthWarning] = useState(false);
  const [isMonthSearching, setIsMonthSearching] = useState(false);
  const [monthSearchInfo, setMonthSearchInfo] = useState<any>(null);
  const [searchProgress, setSearchProgress] = useState({
    current: 0,
    total: 0,
    currentDate: '',
    flightsFound: 0
  });
  
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // ✅ NEW: Month detection function
  const detectMonthSearch = (query: string): { isMonth: boolean; monthName?: string; estimatedDates?: number } => {
    const queryLower = query.toLowerCase();
    
    // Check for explicit month keywords first
    const monthKeywords = ['next month', 'this month', 'entire month', 'whole month', 'full month'];
    
    for (const keyword of monthKeywords) {
      if (queryLower.includes(keyword)) {
        return { 
          isMonth: true, 
          monthName: keyword.includes('next') ? 'Next Month' : 
                     keyword.includes('this') ? 'This Month' : 'Month',
          estimatedDates: 12 
        };
      }
    }
    
    // ✅ IMPROVED: More flexible month name detection
    const monthNames = ['january', 'february', 'march', 'april', 'may', 'june', 
                       'july', 'august', 'september', 'october', 'november', 'december'];
    
    for (const month of monthNames) {
      // Check for various month patterns
      const monthPatterns = [
        `flights in ${month}`,
        `flights for ${month}`, 
        `flights during ${month}`,
        `in ${month}`,
        `for ${month}`,           // ✅ This will catch "for July"
        `during ${month}`,
        `throughout ${month}`,
        `${month} flights`,
        `all of ${month}`,
        `entire ${month}`
      ];
      
      // Check if any pattern matches
      const hasMonthPattern = monthPatterns.some(pattern => queryLower.includes(pattern));
      
      // ✅ EXCLUDE specific date patterns
      const specificDatePatterns = [
        new RegExp(`\\d{1,2}\\s+${month}`),        // "15 july"
        new RegExp(`${month}\\s+\\d{1,2}`),        // "july 15"
        new RegExp(`\\d{1,2}(st|nd|rd|th)\\s+${month}`), // "15th july"
        new RegExp(`${month}\\s+\\d{1,2}(st|nd|rd|th)`)  // "july 15th"
      ];
      
      const hasSpecificDate = specificDatePatterns.some(pattern => pattern.test(queryLower));
      
      // Only return month search if it has month patterns AND no specific dates
      if (hasMonthPattern && !hasSpecificDate) {
        return { 
          isMonth: true, 
          monthName: month.charAt(0).toUpperCase() + month.slice(1),
          estimatedDates: 12 
        };
      }
    }
    
    return { isMonth: false };
  };

  // ✅ UPDATED: Modified handleSendMessage function
  const handleSendMessage = async () => {
    if (!inputValue.trim() || isLoading) return;

    // ✅ NEW: Check for month search before sending
    const monthDetection = detectMonthSearch(inputValue);

    if (monthDetection.isMonth) {
      setMonthSearchInfo({
        monthName: monthDetection.monthName,
        estimatedDates: monthDetection.estimatedDates,
        originalQuery: inputValue
      });
      setShowMonthWarning(true);
      return; // Don't send the message yet
    }

    // Regular message sending logic using the new auth hook
    const messageText = inputValue;
    setInputValue('');

    try {
      await sendMessage(messageText);
    } catch (error) {
      console.error('Error sending message:', error);
    }
  };



  // ✅ NEW: Month search handlers
  const handleMonthSearchConfirm = async () => {
    setShowMonthWarning(false);
    setIsMonthSearching(true);
    
    // Reset progress
    setSearchProgress({ current: 0, total: 12, currentDate: '', flightsFound: 0 });
    
    // Start the actual search
    await sendMonthSearch(monthSearchInfo.originalQuery);
    
    setIsMonthSearching(false);
  };

  const sendMonthSearch = async (query: string) => {
    // Simulate progress updates (you can make this real by polling your backend)
    simulateProgress();

    try {
      // Send the actual search request using the new hook
      await sendMessage(query);
    } catch (error) {
      console.error('Error in month search:', error);
    }
  };

  const simulateProgress = () => {
    let current = 0;
    const total = 12;
    
    const interval = setInterval(() => {
      current++;
      setSearchProgress(prev => ({
        current,
        total,
        currentDate: `2025-07-${String(current + 1).padStart(2, '0')}`,
        flightsFound: prev.flightsFound + Math.floor(Math.random() * 4) + 1
      }));
      
      if (current >= total) {
        clearInterval(interval);
      }
    }, 2500); // Update every 2.5 seconds
  };



  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const renderMessage = (message: any) => {
    const isUser = message.sender === 'user';

    return (
      <div key={message.id} className={`mb-6 ${isUser ? 'flex justify-end' : 'flex justify-start'}`}>
        <div className={`max-w-4xl ${isUser ? 'order-2' : 'order-1'}`}>
          {/* Avatar */}
          <div className={`flex items-start space-x-3 ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
              isUser ? 'bg-blue-500' : 'bg-gray-100'
            }`}>
              {isUser ? (
                <User className="w-4 h-4 text-white" />
              ) : (
                <Bot className="w-4 h-4 text-gray-600" />
              )}
            </div>

            {/* Message bubble */}
            <div className={`
              rounded-lg px-4 py-3 mb-2 flex-1
              ${isUser
                ? 'bg-blue-500 text-white max-w-md ml-auto'
                : 'bg-white border border-gray-200 shadow-sm'
              }
            `}>
              {isUser ? (
                <div className="whitespace-pre-wrap">{message.content}</div>
              ) : (
                <>
                  {/* Bot message content */}
                  {(() => {
                    console.log('🎯 Rendering message:', message.id, 'at', new Date().toISOString());
                    console.log('🎯 Message object keys:', Object.keys(message));
                    console.log('🎯 Message flights:', message.flights);
                    console.log('🎯 Message flights type:', typeof message.flights);
                    console.log('🎯 Message flights length:', message.flights?.length);
                    console.log('🎯 Message data:', message.data);
                    console.log('🎯 Message data flights:', message.data?.flights);
                    console.log('🎯 Has flights?', message.flights && message.flights.length > 0);
                    console.log('🎯 Has data flights?', message.data?.flights && message.data.flights.length > 0);
                    return null;
                  })()}
                  {((message.flights && message.flights.length > 0) || (message.data?.flights && message.data.flights.length > 0)) ? (
                    <div>
                      {/* Brief text summary */}
                      <div className="mb-4 text-gray-800">
                        <div className="whitespace-pre-wrap">{message.content}</div>
                      </div>

                      {/* Enhanced flight display */}
                      <EnhancedFlightDisplay
                        flightData={message.flights || message.data?.flights || []}
                        searchInfo={message.data?.search_info}
                      />
                    </div>
                  ) : (
                    <div className="whitespace-pre-wrap text-gray-800">{message.content}</div>
                  )}
                </>
              )}
            </div>
          </div>

          {/* Suggestions */}
          {!isUser && message.suggestions && message.suggestions.length > 0 && (
            <div className="mt-3 space-y-2 ml-11">
              <p className="text-sm font-medium text-gray-600">Suggestions:</p>
              <div className="flex flex-wrap gap-2">
                {message.suggestions.map((suggestion, index) => (
                  <button
                    key={index}
                    onClick={() => handleQuickAction(suggestion)}
                    className="text-sm bg-blue-50 hover:bg-blue-100 text-blue-700 rounded-lg px-3 py-1 transition-colors border border-blue-200"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Timestamp */}
          <div className={`text-xs text-gray-500 mt-1 ${isUser ? 'text-right' : 'text-left'}`}>
            {message.timestamp.toLocaleTimeString()}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-screen max-w-6xl mx-auto bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 p-4 shadow-sm">
        <h1 className="text-xl font-semibold text-gray-800">Travel Assistant</h1>
        <p className="text-sm text-gray-600">Find flights, accommodations, and travel information</p>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map(renderMessage)}
        
        {isLoading && (
          <div className="flex justify-start mb-6">
            <div className="flex items-start space-x-3">
              <div className="w-8 h-8 rounded-full bg-gray-100 flex items-center justify-center flex-shrink-0">
                <Bot className="w-4 h-4 text-gray-600" />
              </div>
              <div className="bg-white border border-gray-200 rounded-lg px-4 py-3 shadow-sm">
                <div className="flex items-center gap-2 text-gray-600">
                  <Loader className="animate-spin" size={16} />
                  <span className="text-sm">Thinking...</span>
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="bg-white border-t border-gray-200 p-4 shadow-lg">
        <div className="flex gap-2 max-w-4xl mx-auto">
          <textarea
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask me about flights, hotels, or travel planning..."
            className="flex-1 border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
            rows={1}
            style={{ minHeight: '40px', maxHeight: '120px' }}
          />
          <button
            onClick={handleSendMessage}
            disabled={isLoading || !inputValue.trim()}
            className="bg-blue-500 text-white p-2 rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send size={20} />
          </button>
        </div>
      </div>

      {/* ✅ NEW: Month Search Warning Modal */}
      {showMonthWarning && monthSearchInfo && (
        <MonthSearchConfirmation
          onConfirm={handleMonthSearchConfirm}
          onCancel={() => setShowMonthWarning(false)}
          monthName={monthSearchInfo.monthName}
          estimatedDates={monthSearchInfo.estimatedDates}
        />
      )}

      {/* ✅ NEW: Month Search Progress */}
      <MonthSearchProgress
        currentDate={searchProgress.current}
        totalDates={searchProgress.total}
        monthName={monthSearchInfo?.monthName || 'Next Month'}
        currentSearchDate={searchProgress.currentDate}
        flightsFound={searchProgress.flightsFound}
        isVisible={isMonthSearching}
      />
    </div>
  );
};

export default ChatInterface;