/**
 * Session service
 * Handles session CRUD operations and orchestration
 */

import { apiClient, apiRequest } from './api';
import type {
  Session,
  SessionCreate,
  SessionUpdate,
  OrchestrationRequest,
  OrchestrationResponse,
  RequirementAnalysisRequest,
  AnalysisResponse,
  Task,
} from '@/types';

const SESSIONS_ENDPOINT = '/v1/sessions';

/**
 * Session service methods
 */
export const sessionService = {
  /**
   * Get all sessions with optional pagination
   */
  async getSessions(params?: {
    page?: number;
    limit?: number;
    status?: string;
  }): Promise<Session[]> {
    const response = await apiClient.get<Session[]>(SESSIONS_ENDPOINT, { params });
    return response.data;
  },

  /**
   * Get a single session by ID
   */
  async getSession(sessionId: string): Promise<Session> {
    return apiRequest<Session>('GET', `${SESSIONS_ENDPOINT}/${sessionId}`);
  },

  /**
   * Create a new session
   */
  async createSession(data: SessionCreate): Promise<Session> {
    return apiRequest<Session>('POST', SESSIONS_ENDPOINT, data);
  },

  /**
   * Update an existing session
   */
  async updateSession(sessionId: string, data: SessionUpdate): Promise<Session> {
    return apiRequest<Session>('PUT', `${SESSIONS_ENDPOINT}/${sessionId}`, data);
  },

  /**
   * Delete a session
   */
  async deleteSession(sessionId: string): Promise<void> {
    await apiRequest<void>('DELETE', `${SESSIONS_ENDPOINT}/${sessionId}`);
  },

  /**
   * Start requirement analysis for a session
   */
  async analyzeRequirements(
    sessionId: string,
    data: RequirementAnalysisRequest
  ): Promise<AnalysisResponse> {
    return apiRequest<AnalysisResponse>(
      'POST',
      `${SESSIONS_ENDPOINT}/${sessionId}/analyze`,
      data
    );
  },

  /**
   * Start full orchestration workflow
   */
  async startOrchestration(data: OrchestrationRequest): Promise<OrchestrationResponse> {
    return apiRequest<OrchestrationResponse>('POST', `${SESSIONS_ENDPOINT}/orchestrate`, data);
  },

  /**
   * Get session tasks
   */
  async getSessionTasks(sessionId: string): Promise<Task[]> {
    return apiRequest<Task[]>('GET', `${SESSIONS_ENDPOINT}/${sessionId}/tasks`);
  },
};

export default sessionService;
