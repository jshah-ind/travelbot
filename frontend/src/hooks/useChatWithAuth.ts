import { useState, useCallback, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { chatHistoryService, ChatSession, ChatMessage } from '../services/chatHistoryService';
import { travelService } from '../services/travelService';

interface ChatMessageLocal {
  id: string;
  content: string;
  sender: 'user' | 'agent';
  timestamp: Date;
  data?: any;
  flights?: any[];
  suggestions?: string[];
}

export const useChatWithAuth = () => {
  const { isAuthenticated, user } = useAuth();
  const [messages, setMessages] = useState<ChatMessageLocal[]>([
    {
      id: '1',
      content: "Hello! I'm your travel assistant. I can help you search for flights, find accommodations, and answer any travel-related questions. How can I assist you today?",
      sender: 'agent',
      timestamp: new Date(),
      suggestions: [
        'Search flights from Delhi to Mumbai',
        'Find flights for next week',
        'Show me flight options'
      ]
    }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentSession, setCurrentSession] = useState<ChatSession | null>(null);
  const [isInitialized, setIsInitialized] = useState(false);

  // Initialize or load chat session (ChatGPT-like behavior)
  useEffect(() => {
    const initializeSession = async () => {
      if (isAuthenticated && !isInitialized) {
        try {
          console.log('🔄 Initializing chat session...');
          
          // Try to recover existing session from localStorage
          const savedSessionId = localStorage.getItem('current_chat_session_id');
          
          if (savedSessionId) {
            try {
              // Try to load the saved session
              const session = await chatHistoryService.getSession(savedSessionId);
              setCurrentSession(session);
              localStorage.setItem('current_chat_session_id', session.session_id);
              console.log('✅ Recovered existing session:', session.session_id);
              
                        // Load messages for the recovered session
          console.log('🔄 About to load messages for recovered session:', session.session_id);
          await loadSessionMessages(session);
          console.log('✅ Finished loading messages for recovered session');
            } catch (error) {
              console.log('❌ Failed to recover session, clearing localStorage:', error);
              localStorage.removeItem('current_chat_session_id');
              // Show initial greeting for failed session recovery
              setMessages([{
                id: '1',
                content: "Hello! I'm your travel assistant. I can help you search for flights, find accommodations, and answer any travel-related questions. How can I assist you today?",
                sender: 'agent',
                timestamp: new Date(),
                suggestions: [
                  'Search flights from Delhi to Mumbai',
                  'Find flights for next week',
                  'Show me flight options'
                ]
              }]);
            }
          } else {
            // No saved session - show initial greeting without creating session
            console.log('ℹ️ No saved session. Session will be created on first message.');
            setMessages([{
              id: '1',
              content: "Hello! I'm your travel assistant. I can help you search for flights, find accommodations, and answer any travel-related questions. How can I assist you today?",
              sender: 'agent',
              timestamp: new Date(),
              suggestions: [
                'Search flights from Delhi to Mumbai',
                'Find flights for next week',
                'Show me flight options'
              ]
            }]);
          }
        } catch (error) {
          console.error('Failed to initialize chat session:', error);
        }
      }
    };

    // Only initialize if we haven't initialized yet
    if (isAuthenticated && !isInitialized) {
      setIsInitialized(true);
      initializeSession();
    }
  }, [isAuthenticated, isInitialized]);

  // Load existing messages if session exists
  const loadSessionMessages = useCallback(async (sessionOverride?: ChatSession) => {
    const sessionToUse = sessionOverride || currentSession;
    
    if (sessionToUse && isAuthenticated) {
      try {
        console.log('🔄 Loading messages for session:', sessionToUse.session_id);
        const response = await chatHistoryService.getMessages(sessionToUse.session_id);
        console.log('📨 Loaded messages:', response.messages.length);
        console.log('📨 Raw messages from API:', response.messages);
        
        if (response.messages.length > 0) {
          console.log('📨 First message structure:', response.messages[0]);
          console.log('📨 Message fields:', Object.keys(response.messages[0]));
          
          const loadedMessages: ChatMessageLocal[] = response.messages.map((msg: ChatMessage) => {
            console.log('📨 Processing message:', msg);
            return {
              id: msg.id.toString(),
              content: msg.message_text,
              sender: msg.message_type === 'user' ? 'user' : 'agent',
              timestamp: new Date(msg.created_at),
              data: msg.response_data,
              flights: msg.response_data?.flights || null,
              suggestions: msg.response_data?.suggestions || null
            };
          });

          console.log('📝 Processed loaded messages:', loadedMessages.length);
          console.log('📝 Final processed messages:', loadedMessages);
          setMessages(loadedMessages);
          console.log('✅ setMessages called with:', loadedMessages.length, 'messages');
          
          // Test if messages were set correctly
          setTimeout(() => {
            console.log('🎯 Messages state after setMessages:', messages.length, 'messages');
          }, 100);
        } else {
          console.log('ℹ️ No messages found for session, showing initial greeting');
          // Show initial greeting for empty sessions
          setMessages([{
            id: '1',
            content: "Hello! I'm your travel assistant. I can help you search for flights, find accommodations, and answer any travel-related questions. How can I assist you today?",
            sender: 'agent',
            timestamp: new Date(),
            suggestions: [
              'Search flights from Delhi to Mumbai',
              'Find flights for next week',
              'Show me flight options'
            ]
          }]);
        }
      } catch (error) {
        console.error('❌ Failed to load session messages:', error);
        // Show initial greeting on error
        setMessages([{
          id: '1',
          content: "Hello! I'm your travel assistant. I can help you search for flights, find accommodations, and answer any travel-related questions. How can I assist you today?",
          sender: 'agent',
          timestamp: new Date(),
          suggestions: [
            'Search flights from Delhi to Mumbai',
            'Find flights for next week',
            'Show me flight options'
          ]
        }]);
      }
    } else {
      console.log('⚠️ Cannot load messages - no session or not authenticated:', { 
        hasSession: !!sessionToUse, 
        isAuthenticated 
      });
    }
  }, [isAuthenticated]);

  // Auto-load messages when currentSession changes
  useEffect(() => {
    if (currentSession && isAuthenticated && isInitialized) {
      console.log('🔄 Auto-loading messages for session change:', currentSession.session_id);
      loadSessionMessages(currentSession);
    }
  }, [currentSession, isAuthenticated, isInitialized, loadSessionMessages]);

  // Debug: Watch messages state changes
  useEffect(() => {
    console.log('🎯 Messages state changed:', messages.length, 'messages');
    console.log('🎯 Messages content:', messages);
  }, [messages]);

  // Cleanup session on logout
  useEffect(() => {
    if (!isAuthenticated) {
      // Clear session data when user logs out
      setCurrentSession(null);
      setIsInitialized(false);
      setMessages([{
        id: '1',
        content: "Hello! I'm your travel assistant. I can help you search for flights, find accommodations, and answer any travel-related questions. How can I assist you today?",
        sender: 'agent',
        timestamp: new Date(),
        suggestions: [
          'Search flights from Delhi to Mumbai',
          'Find flights for next week',
          'Show me flight options'
        ]
      }]);
      localStorage.removeItem('current_chat_session_id');
      console.log('🧹 Cleared session data on logout');
    }
  }, [isAuthenticated]);

  const saveMessageToHistory = async (message: string, messageType: 'user' | 'assistant', responseData?: any, sessionOverride?: any) => {
    const sessionToUse = sessionOverride || currentSession;
    
    console.log('🔍 saveMessageToHistory called with:', { 
      message: message.substring(0, 50) + '...', 
      messageType, 
      hasSession: !!sessionToUse,
      sessionId: sessionToUse?.session_id,
      isAuthenticated 
    });
    
    if (sessionToUse && isAuthenticated) {
      try {
        console.log('💾 Saving message to history:', { 
          message: message.substring(0, 50) + '...', 
          messageType, 
          sessionId: sessionToUse.session_id,
          responseData: responseData ? 'present' : 'none'
        });
        
        const result = await chatHistoryService.addMessage({
          session_id: sessionToUse.session_id,
          content: message,
          message_type: messageType,
          response_data: responseData
        });
        
        console.log('✅ Message saved successfully:', result);
        // Refresh messages after saving
        await loadSessionMessages(sessionToUse);
      } catch (error) {
        console.error('❌ Failed to save message to history:', error);
        console.error('❌ Error details:', {
          error: error instanceof Error ? error.message : String(error),
          stack: error instanceof Error ? error.stack : undefined
        });
      }
    } else {
      console.log('⚠️ Cannot save message - no session or not authenticated:', { 
        hasSession: !!sessionToUse, 
        isAuthenticated,
        sessionId: sessionToUse?.session_id
      });
    }
  };

  const sendMessage = useCallback(async (content: string) => {
    // Add user message immediately
    const userMessage: ChatMessageLocal = {
      id: Date.now().toString(),
      content,
      sender: 'user',
      timestamp: new Date(),
    };
    
    setMessages(prev => [...prev, userMessage]);
    setIsLoading(true);
    setError(null);

    try {
      let sessionToUse = currentSession;
      
      // Auto-create session if none exists (ChatGPT-like behavior)
      if (!currentSession && isAuthenticated) {
        console.log('🆕 No session exists, creating one automatically for first message');
        const newSession = await createNewSession('Travel Chat Session');
        console.log('✅ New session created:', newSession?.session_id);
        // Ensure we have the session before saving message
        if (!newSession) {
          throw new Error('Failed to create new session');
        }
        sessionToUse = newSession;
      }

      // Save user message to history
      console.log('💾 About to save user message, session to use:', sessionToUse?.session_id);
      if (sessionToUse) {
        await saveMessageToHistory(content, 'user', undefined, sessionToUse);
      } else {
        console.error('❌ No session available for saving message');
      }

      console.log('🚀 Sending message to travel service:', content);
      console.log('📍 Current session:', currentSession?.session_id);

      // Send to travel service with session context and timeout
      const response = await Promise.race([
        travelService.searchFlightsNaturalLanguage(
          content,
          currentSession?.session_id
        ),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Request timeout after 180 seconds. Please try again in a moment.')), 180000)
        )
      ]) as any;

      console.log('✅ Travel service response:', response);
      console.log('🔍 Response data structure:', JSON.stringify(response, null, 2));

      let agentContent = '';
      let responseData = null;
      let flights = null;
      let suggestions = null;

      if (response.status === 'success') {
        console.log('✅ Success response detected');
        console.log('🔍 response.data:', response.data);
        console.log('🔍 response.response:', response.response);

        // Handle ConversationResponse structure (flights in response.response)
        const flightData = response.response?.flights || response.data?.flights;
        const searchInfo = response.response?.search_info || response.data?.search_info;

        console.log('🔍 flightData:', flightData);
        console.log('🔍 searchInfo:', searchInfo);

        if (flightData && flightData.length > 0) {
          console.log('✅ Flights found:', flightData.length);
          console.log('🔍 First flight object:', flightData[0]);
          console.log('🔍 Flight object keys:', Object.keys(flightData[0] || {}));
          agentContent = `I found ${flightData.length} flight options for you. Here are the available flights:`;
          flights = flightData;
          responseData = {
            flights: flightData,
            search_info: searchInfo,
            ...response.response,
            ...response.data
          };
          console.log('✅ Set flights variable:', flights);
          console.log('✅ Set responseData:', responseData);
        } else if (response.response?.message || response.data?.message) {
          agentContent = response.response?.message || response.data?.message;
          responseData = response.response || response.data;
        } else {
          agentContent = "I've processed your request. Let me know if you need any specific information about flights.";
        }
      } else if (response.status === 'error') {
        agentContent = response.error || "I'm sorry, I couldn't process your request. Please try again.";
        if (response.suggestions) {
          suggestions = response.suggestions;
        }
      } else {
        agentContent = "I've received your request. How else can I help you with your travel plans?";
      }

      // Add agent response
      const agentMessage: ChatMessageLocal = {
        id: (Date.now() + 1).toString(),
        content: agentContent,
        sender: 'agent',
        timestamp: new Date(),
        data: responseData,
        flights: flights,
        suggestions: suggestions
      };

      console.log('🎯 Final agent message object:', agentMessage);
      console.log('🎯 Agent message flights:', agentMessage.flights);
      console.log('🎯 Agent message data:', agentMessage.data);

      setMessages(prev => {
        const newMessages = [...prev, agentMessage];
        console.log('🎯 Updated messages array length:', newMessages.length);
        console.log('🎯 Last message in array:', newMessages[newMessages.length - 1]);
        console.log('🎯 Last message flights:', newMessages[newMessages.length - 1].flights);
        return newMessages;
      });

      // Save agent response to history
      if (sessionToUse) {
        await saveMessageToHistory(agentContent, 'assistant', responseData, sessionToUse);
      } else {
        console.error('❌ No session available for saving agent message');
      }

    } catch (err) {
      console.error('❌ Error in sendMessage:', err);
      const errorMsg = err instanceof Error ? err.message : 'An error occurred';
      setError(errorMsg);

      // Add error message with more details
      const errorMessage: ChatMessageLocal = {
        id: (Date.now() + 1).toString(),
        content: `I'm sorry, I encountered an error: ${errorMsg}. Please try again in a moment.`,
        sender: 'agent',
        timestamp: new Date(),
      };

      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [currentSession, isAuthenticated]);

  const handleQuickAction = useCallback(async (action: string) => {
    await sendMessage(action);
  }, [sendMessage]);

  const createNewSession = useCallback(async (title?: string) => {
    if (!isAuthenticated) return;

    try {
      console.log('🆕 Creating new session with title:', title);
      const session = await chatHistoryService.createSession({
        title: title || 'New Travel Chat',
        description: 'Travel planning conversation',
        session_type: 'travel'
      });
      
      setCurrentSession(session);
      // Save session ID to localStorage
      localStorage.setItem('current_chat_session_id', session.session_id);
      
      // Reset messages to initial state
      setMessages([{
        id: '1',
        content: "Hello! I'm your travel assistant. How can I help you with your travel plans today?",
        sender: 'agent',
        timestamp: new Date(),
        suggestions: [
          'Search flights from Delhi to Mumbai',
          'Find flights for next week',
          'Show me flight options'
        ]
      }]);
      
      console.log('✅ New session created and set:', session.session_id);
      return session;
    } catch (error) {
      console.error('❌ Failed to create new session:', error);
      throw error;
    }
  }, [isAuthenticated]);

  const clearCurrentSession = useCallback(() => {
    console.log('🧹 Clearing current session');
    setCurrentSession(null);
    localStorage.removeItem('current_chat_session_id');
    setMessages([{
      id: '1',
      content: "Hello! I'm your travel assistant. I can help you search for flights, find accommodations, and answer any travel-related questions. How can I assist you today?",
      sender: 'agent',
      timestamp: new Date(),
      suggestions: [
        'Search flights from Delhi to Mumbai',
        'Find flights for next week',
        'Show me flight options'
      ]
    }]);
  }, []);

  const forceNewSession = useCallback(async () => {
    console.log('🆕 Forcing new session creation');
    clearCurrentSession();
    // This will trigger the useEffect to create a new session
  }, [clearCurrentSession]);

  const loadSession = useCallback(async (sessionId: string) => {
    if (!isAuthenticated) {
      console.log('⚠️ Cannot load session - not authenticated');
      return;
    }

    try {
      console.log('🔄 Loading session:', sessionId);
      
      // Load session data first
      const session = await chatHistoryService.getSession(sessionId);
      console.log('✅ Session loaded:', session);
      
      // Set session and save to localStorage
      setCurrentSession(session);
      localStorage.setItem('current_chat_session_id', session.session_id);
      console.log('✅ Session set, messages will be loaded by useEffect');
      
      return session;
    } catch (error) {
      console.error('❌ Failed to load session:', error);
      console.error('❌ Error details:', {
        sessionId,
        isAuthenticated,
        error: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined
      });
      throw error;
    }
  }, [isAuthenticated, loadSessionMessages]);

  return {
    messages,
    isLoading,
    error,
    currentSession,
    sendMessage,
    handleQuickAction,
    createNewSession,
    clearCurrentSession,
    forceNewSession,
    loadSession,
    isAuthenticated
  };
};
