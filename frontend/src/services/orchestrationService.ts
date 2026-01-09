/**
 * Orchestration service
 * Handles workflow orchestration and status monitoring
 */

import { apiRequest } from './api';
import type {
  OrchestrationRequest,
  OrchestrationResponse,
  Artifact,
  WorkflowStatus,
} from '@/types';

const ORCHESTRATION_ENDPOINT = '/v1/orchestration';

/**
 * Orchestration status response
 */
export interface OrchestrationStatus {
  session_id: string;
  status: WorkflowStatus;
  progress_percentage: number;
  current_step: string;
  estimated_completion_minutes?: number;
  tasks_completed: number;
  tasks_total: number;
  artifacts_generated: number;
  error?: string;
}

/**
 * Orchestration service methods
 */
export const orchestrationService = {
  /**
   * Start a new orchestration workflow
   */
  async start(data: OrchestrationRequest): Promise<OrchestrationResponse> {
    return apiRequest<OrchestrationResponse>('POST', ORCHESTRATION_ENDPOINT, data);
  },

  /**
   * Get orchestration status
   */
  async getStatus(sessionId: string): Promise<OrchestrationStatus> {
    return apiRequest<OrchestrationStatus>('GET', `${ORCHESTRATION_ENDPOINT}/${sessionId}/status`);
  },

  /**
   * Cancel orchestration
   */
  async cancel(sessionId: string): Promise<{ message: string }> {
    return apiRequest<{ message: string }>(
      'POST',
      `${ORCHESTRATION_ENDPOINT}/${sessionId}/cancel`
    );
  },

  /**
   * Get artifact by ID
   */
  async getArtifact(sessionId: string, artifactId: string): Promise<Artifact> {
    return apiRequest<Artifact>(
      'GET',
      `${ORCHESTRATION_ENDPOINT}/${sessionId}/artifacts/${artifactId}`
    );
  },

  /**
   * Get all artifacts for a session
   */
  async getArtifacts(sessionId: string): Promise<Artifact[]> {
    return apiRequest<Artifact[]>('GET', `${ORCHESTRATION_ENDPOINT}/${sessionId}/artifacts`);
  },

  /**
   * Poll for orchestration completion
   * Returns a promise that resolves when orchestration is complete
   */
  async waitForCompletion(
    sessionId: string,
    options: {
      pollingInterval?: number;
      maxAttempts?: number;
      onProgress?: (status: OrchestrationStatus) => void;
    } = {}
  ): Promise<OrchestrationStatus> {
    const { pollingInterval = 2000, maxAttempts = 150, onProgress } = options;

    let attempts = 0;

    return new Promise((resolve, reject) => {
      const poll = async () => {
        try {
          const status = await this.getStatus(sessionId);

          if (onProgress) {
            onProgress(status);
          }

          if (status.status === 'completed') {
            resolve(status);
            return;
          }

          if (status.status === 'failed' || status.status === 'cancelled') {
            reject(new Error(status.error || `Orchestration ${status.status}`));
            return;
          }

          attempts++;
          if (attempts >= maxAttempts) {
            reject(new Error('Orchestration timed out'));
            return;
          }

          setTimeout(poll, pollingInterval);
        } catch (error) {
          reject(error);
        }
      };

      poll();
    });
  },
};

export default orchestrationService;
