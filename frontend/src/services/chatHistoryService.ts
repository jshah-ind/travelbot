import { apiClient } from './api';
import { authService } from './authService';

export interface ChatSession {
  id: number;
  session_id: string;
  user_id: number;
  title: string;
  session_type: string;
  created_at: string;
  updated_at?: string;
  is_active: boolean;
  total_messages: number;
}

export interface ChatMessage {
  id: number;
  message_id: string;
  session_id: number;
  user_id: number;
  message_text: string;
  message_type: 'user' | 'assistant' | 'system';
  created_at: string;
  is_edited: boolean;
  response_data?: any;
  processing_time?: number;
}

export interface CreateSessionRequest {
  title: string;
  description?: string;
  session_type?: string;
}

export interface CreateMessageRequest {
  session_id?: string;
  content: string;  // Changed from message_text to content
  message_type?: 'user' | 'assistant' | 'system';
  response_data?: any;
}

export interface APIResponse<T = any> {
  status: string;
  message: string;
  data?: T;
}

export interface SessionsResponse {
  sessions: ChatSession[];
  total_count: number;
  page: number;
  page_size: number;
}

export interface MessagesResponse {
  messages: ChatMessage[];
  session_id: string;
  count: number;
}

class ChatHistoryService {
  // Get authorization headers
  private getAuthHeaders(): Record<string, string> {
    return authService.getAuthHeaders();
  }

  // Create new chat session
  async createSession(data: CreateSessionRequest): Promise<ChatSession> {
    try {
      const response = await apiClient.post<APIResponse<{ session: ChatSession }>>(
        '/chat/sessions',
        data,
        this.getAuthHeaders()
      );

      if (response.status === 'success' && response.data) {
        return response.data.session;
      }

      throw new Error('Failed to create chat session');
    } catch (error) {
      console.error('Create session failed:', error);
      throw error;
    }
  }

  // Get user's chat sessions
  async getSessions(page: number = 1, pageSize: number = 20): Promise<SessionsResponse> {
    try {
      const response = await apiClient.get<APIResponse<SessionsResponse>>(
        `/chat/sessions?page=${page}&page_size=${pageSize}`,
        this.getAuthHeaders()
      );

      if (response.status === 'success' && response.data) {
        return response.data;
      }

      throw new Error('Failed to get chat sessions');
    } catch (error) {
      console.error('Get sessions failed:', error);
      throw error;
    }
  }

  // Get specific session by ID
  async getSession(sessionId: string): Promise<ChatSession> {
    try {
      const response = await apiClient.get<APIResponse<{ session: ChatSession }>>(
        `/chat/sessions/${sessionId}`,
        this.getAuthHeaders()
      );

      if (response.status === 'success' && response.data) {
        return response.data.session;
      }

      throw new Error('Failed to get chat session');
    } catch (error) {
      console.error('Get session failed:', error);
      throw error;
    }
  }

  // Update session
  async updateSession(sessionId: string, data: Partial<CreateSessionRequest>): Promise<ChatSession> {
    try {
      const response = await apiClient.post<APIResponse<{ session: ChatSession }>>(
        `/chat/sessions/${sessionId}`,
        data,
        this.getAuthHeaders()
      );

      if (response.status === 'success' && response.data) {
        return response.data.session;
      }

      throw new Error('Failed to update chat session');
    } catch (error) {
      console.error('Update session failed:', error);
      throw error;
    }
  }

  // Delete session
  async deleteSession(sessionId: string): Promise<void> {
    try {
      const response = await apiClient.post<APIResponse>(
        `/chat/sessions/${sessionId}/delete`,
        {},
        this.getAuthHeaders()
      );

      if (response.status !== 'success') {
        throw new Error('Failed to delete chat session');
      }
    } catch (error) {
      console.error('Delete session failed:', error);
      throw error;
    }
  }

  // Add message to session
  async addMessage(data: CreateMessageRequest): Promise<ChatMessage> {
    try {
      console.log('📤 Sending addMessage request:', {
        url: '/chat/messages',
        data: {
          ...data,
          content: data.content ? data.content.substring(0, 50) + '...' : 'empty'
        },
        headers: this.getAuthHeaders()
      });
      
      const response = await apiClient.post<APIResponse<{ message: ChatMessage }>>(
        '/chat/messages',
        data,
        this.getAuthHeaders()
      );

      console.log('📥 addMessage response:', response);

      if (response.status === 'success' && response.data) {
        console.log('✅ Message added successfully:', response.data.message);
        return response.data.message;
      }

      console.error('❌ addMessage failed - invalid response:', response);
      throw new Error('Failed to add message');
    } catch (error) {
      console.error('❌ Add message failed:', error);
      throw error;
    }
  }

  // Get messages for a session
  async getMessages(sessionId: string, page: number = 1, pageSize: number = 50): Promise<MessagesResponse> {
    try {
      const response = await apiClient.get<APIResponse<MessagesResponse>>(
        `/chat/sessions/${sessionId}/messages?page=${page}&page_size=${pageSize}`,
        this.getAuthHeaders()
      );

      if (response.status === 'success' && response.data) {
        return response.data;
      }

      throw new Error('Failed to get messages');
    } catch (error) {
      console.error('Get messages failed:', error);
      throw error;
    }
  }

  // Search messages
  async searchMessages(query: string, sessionId?: string): Promise<ChatMessage[]> {
    try {
      const params = new URLSearchParams({ q: query });
      if (sessionId) {
        params.append('session_id', sessionId);
      }

      const response = await apiClient.get<APIResponse<{ messages: ChatMessage[] }>>(
        `/chat/messages/search?${params.toString()}`,
        this.getAuthHeaders()
      );

      if (response.status === 'success' && response.data) {
        return response.data.messages;
      }

      throw new Error('Failed to search messages');
    } catch (error) {
      console.error('Search messages failed:', error);
      throw error;
    }
  }

  // Get recent sessions (for quick access)
  async getRecentSessions(limit: number = 5): Promise<ChatSession[]> {
    try {
      const response = await this.getSessions(1, limit);
      return response.sessions;
    } catch (error) {
      console.error('Get recent sessions failed:', error);
      return [];
    }
  }

  // Create session with first message
  async createSessionWithMessage(title: string, message: string): Promise<{ session: ChatSession; message: ChatMessage }> {
    try {
      // Create session first
      const session = await this.createSession({ title });

      // Add initial message
      const messageData = await this.addMessage({
        session_id: session.session_id,
        content: message,  // Changed from message_text to content
        message_type: 'user'
      });

      return { session, message: messageData };
    } catch (error) {
      console.error('Create session with message failed:', error);
      throw error;
    }
  }
}

export const chatHistoryService = new ChatHistoryService();
