/**
 * Agent service
 * Handles agent management and A2A task operations
 */

import { apiRequest } from './api';
import type {
  Agent,
  AgentCard,
  A2ATask,
  A2ATaskRequest,
  A2ATaskResponse,
  SystemHealth,
} from '@/types';

const AGENTS_ENDPOINT = '/v1/agents';
const A2A_ENDPOINT = '/v1/a2a';

/**
 * Agent service methods
 */
export const agentService = {
  /**
   * Get all registered agents
   */
  async getAgents(): Promise<Agent[]> {
    return apiRequest<Agent[]>('GET', AGENTS_ENDPOINT);
  },

  /**
   * Get a single agent by ID
   */
  async getAgent(agentId: string): Promise<Agent> {
    return apiRequest<Agent>('GET', `${AGENTS_ENDPOINT}/${agentId}`);
  },

  /**
   * Register a new agent
   */
  async registerAgent(agentCard: AgentCard): Promise<Agent> {
    return apiRequest<Agent>('POST', `${AGENTS_ENDPOINT}/register`, agentCard);
  },

  /**
   * Get agent capabilities
   */
  async getAgentCapabilities(agentId: string): Promise<string[]> {
    const agent = await this.getAgent(agentId);
    return agent.capabilities;
  },

  /**
   * Check system health
   */
  async getSystemHealth(): Promise<SystemHealth> {
    return apiRequest<SystemHealth>('GET', `${AGENTS_ENDPOINT}/health`);
  },
};

/**
 * A2A Task service methods
 */
export const a2aService = {
  /**
   * Create a new A2A task
   */
  async createTask(request: A2ATaskRequest): Promise<A2ATaskResponse> {
    return apiRequest<A2ATaskResponse>('POST', `${A2A_ENDPOINT}/tasks`, request);
  },

  /**
   * Get task status
   */
  async getTaskStatus(taskId: string, agentUrl?: string): Promise<A2ATask> {
    const params = agentUrl ? { agent_url: agentUrl } : undefined;
    return apiRequest<A2ATask>('GET', `${A2A_ENDPOINT}/tasks/${taskId}`, undefined, { params });
  },

  /**
   * Update task
   */
  async updateTask(
    taskId: string,
    update: Partial<A2ATask>
  ): Promise<{ task_id: string; status: string; updated_at: string }> {
    return apiRequest('PUT', `${A2A_ENDPOINT}/tasks/${taskId}`, update);
  },

  /**
   * Cancel task
   */
  async cancelTask(taskId: string, agentUrl?: string): Promise<{ message: string }> {
    const params = agentUrl ? { agent_url: agentUrl } : undefined;
    return apiRequest('POST', `${A2A_ENDPOINT}/tasks/${taskId}/cancel`, undefined, { params });
  },

  /**
   * Retry failed task
   */
  async retryTask(taskId: string, agentUrl: string): Promise<{ message: string }> {
    return apiRequest('POST', `${A2A_ENDPOINT}/tasks/${taskId}/retry`, undefined, {
      params: { agent_url: agentUrl },
    });
  },

  /**
   * List all tasks
   */
  async listTasks(params?: {
    status?: string;
    agent_id?: string;
    session_id?: string;
    limit?: number;
    skip?: number;
  }): Promise<A2ATask[]> {
    return apiRequest<A2ATask[]>('GET', `${A2A_ENDPOINT}/tasks`, undefined, { params });
  },

  /**
   * List tasks for specific agent
   */
  async listAgentTasks(
    agentId: string,
    params?: { status?: string; limit?: number; skip?: number }
  ): Promise<A2ATask[]> {
    return apiRequest<A2ATask[]>('GET', `${A2A_ENDPOINT}/agents/${agentId}/tasks`, undefined, {
      params,
    });
  },
};

export default { agentService, a2aService };
