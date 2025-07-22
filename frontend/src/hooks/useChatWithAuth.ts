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

  // Initialize or load chat session
  useEffect(() => {
    const initializeSession = async () => {
      if (isAuthenticated && !currentSession) {
        try {
          // Create a new session for this chat
          const session = await chatHistoryService.createSession({
            title: 'Travel Chat Session',
            description: 'New travel planning conversation',
            session_type: 'travel'
          });
          setCurrentSession(session);
        } catch (error) {
          console.error('Failed to create chat session:', error);
        }
      }
    };

    initializeSession();
  }, [isAuthenticated, currentSession]);

  // Load existing messages if session exists
  const loadSessionMessages = async () => {
    if (currentSession && isAuthenticated) {
      try {
        const response = await chatHistoryService.getMessages(currentSession.session_id);
        if (response.messages.length > 0) {
          const loadedMessages: ChatMessageLocal[] = response.messages.map((msg: ChatMessage) => ({
            id: msg.message_id,
            content: msg.message_text,
            sender: msg.message_type === 'user' ? 'user' : 'agent',
            timestamp: new Date(msg.created_at),
            data: msg.response_data
          }));

          // Keep the initial greeting and add loaded messages
          setMessages(prev => [prev[0], ...loadedMessages]);
        }
      } catch (error) {
        console.error('Failed to load session messages:', error);
      }
    }
  };

  useEffect(() => {
    loadSessionMessages();
  }, [currentSession, isAuthenticated]);

  const saveMessageToHistory = async (message: string, messageType: 'user' | 'assistant', responseData?: any) => {
    if (currentSession && isAuthenticated) {
      try {
        await chatHistoryService.addMessage({
          session_id: currentSession.session_id,
          content: message,  // Changed from message_text to content
          message_type: messageType,
          response_data: responseData
        });
        // Refresh messages after saving
        await loadSessionMessages();
      } catch (error) {
        console.error('Failed to save message to history:', error);
      }
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
      // Save user message to history
      await saveMessageToHistory(content, 'user');

      console.log('🚀 Sending message to travel service:', content);
      console.log('📍 Current session:', currentSession?.session_id);

      // Send to travel service with session context and timeout
      const response = await Promise.race([
        travelService.searchFlightsNaturalLanguage(
          content,
          currentSession?.session_id
        ),
        new Promise((_, reject) =>
          setTimeout(() => reject(new Error('Request timeout after 30 seconds')), 30000)
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
      await saveMessageToHistory(agentContent, 'assistant', responseData);

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
      const session = await chatHistoryService.createSession({
        title: title || 'New Travel Chat',
        description: 'Travel planning conversation',
        session_type: 'travel'
      });
      
      setCurrentSession(session);
      
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
      
      return session;
    } catch (error) {
      console.error('Failed to create new session:', error);
      throw error;
    }
  }, [isAuthenticated]);

  const loadSession = useCallback(async (sessionId: string) => {
    if (!isAuthenticated) return;

    try {
      const session = await chatHistoryService.getSession(sessionId);
      const response = await chatHistoryService.getMessages(sessionId);
      
      setCurrentSession(session);
      
      const loadedMessages: ChatMessageLocal[] = response.messages.map((msg: ChatMessage) => ({
        id: msg.message_id,
        content: msg.message_text,
        sender: msg.message_type === 'user' ? 'user' : 'agent',
        timestamp: new Date(msg.created_at),
        data: msg.response_data
      }));
      
      setMessages(loadedMessages);
      
      return session;
    } catch (error) {
      console.error('Failed to load session:', error);
      throw error;
    }
  }, [isAuthenticated]);

  return {
    messages,
    isLoading,
    error,
    currentSession,
    sendMessage,
    handleQuickAction,
    createNewSession,
    loadSession,
    isAuthenticated
  };
};
