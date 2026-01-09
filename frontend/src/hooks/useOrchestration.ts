/**
 * useOrchestration hook
 * Manages orchestration workflow state and polling
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { orchestrationService, OrchestrationStatus } from '@/services/orchestrationService';
import { useSessionStore } from '@/stores';
import {
  isMockMode,
  createMockOrchestrationStatus,
  mockArtifacts,
  mockBlockNodes,
  mockMindMapNodes,
} from '@/mocks';
import type { Artifact, OrchestrationRequest } from '@/types';

interface UseOrchestrationOptions {
  pollingInterval?: number;
  autoStart?: boolean;
}

interface UseOrchestrationReturn {
  // State
  status: OrchestrationStatus | null;
  isRunning: boolean;
  isCompleted: boolean;
  isFailed: boolean;
  error: string | null;
  artifacts: Artifact[];

  // Actions
  start: (request: OrchestrationRequest) => Promise<void>;
  cancel: () => Promise<void>;
  reset: () => void;
  fetchArtifacts: () => Promise<void>;
}

/**
 * Hook for managing orchestration workflow
 */
export function useOrchestration(
  sessionId: string | null,
  options: UseOrchestrationOptions = {}
): UseOrchestrationReturn {
  const { pollingInterval = 2000 } = options;

  // State
  const [status, setStatus] = useState<OrchestrationStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [artifacts, setArtifacts] = useState<Artifact[]>([]);

  // Refs for polling
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const mockStepRef = useRef(0);

  // Store actions
  const setOrchestrationProgress = useSessionStore((state) => state.setOrchestrationProgress);
  const updateOrchestrationProgress = useSessionStore((state) => state.updateOrchestrationProgress);

  // Derived state
  const isRunning = status?.status === 'in_progress' || status?.status === 'started';
  const isCompleted = status?.status === 'completed';
  const isFailed = status?.status === 'failed' || status?.status === 'cancelled';

  /**
   * Stop polling
   */
  const stopPolling = useCallback(() => {
    if (pollingRef.current) {
      clearInterval(pollingRef.current);
      pollingRef.current = null;
    }
  }, []);

  /**
   * Poll for status updates (mock or real)
   */
  const pollStatus = useCallback(async () => {
    if (!sessionId) return;

    try {
      let newStatus: OrchestrationStatus;

      if (isMockMode()) {
        // Simulate progress in mock mode
        mockStepRef.current = Math.min(mockStepRef.current + 1, 4);
        newStatus = createMockOrchestrationStatus(sessionId, mockStepRef.current);

        // Simulate delay
        await new Promise((resolve) => setTimeout(resolve, 500));
      } else {
        newStatus = await orchestrationService.getStatus(sessionId);
      }

      setStatus(newStatus);

      // Update store
      updateOrchestrationProgress(sessionId, {
        status: newStatus.status,
        currentAgent: newStatus.current_step,
        completedSteps: Array(newStatus.tasks_completed).fill('step'),
      });

      // Stop polling if completed or failed
      if (newStatus.status === 'completed' || newStatus.status === 'failed' || newStatus.status === 'cancelled') {
        stopPolling();

        if (newStatus.status === 'completed') {
          // Fetch artifacts on completion
          await fetchArtifactsInternal();
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to get status';
      setError(errorMessage);
      stopPolling();
    }
  }, [sessionId, stopPolling, updateOrchestrationProgress]);

  /**
   * Fetch artifacts
   */
  const fetchArtifactsInternal = useCallback(async () => {
    if (!sessionId) return;

    try {
      let artifactList: Artifact[];

      if (isMockMode()) {
        artifactList = mockArtifacts.filter((a) => a.session_id === sessionId);
        // If no artifacts for this session, return all mock artifacts
        if (artifactList.length === 0) {
          artifactList = mockArtifacts;
        }
      } else {
        artifactList = await orchestrationService.getArtifacts(sessionId);
      }

      setArtifacts(artifactList);
    } catch (err) {
      console.error('Failed to fetch artifacts:', err);
    }
  }, [sessionId]);

  /**
   * Start orchestration
   */
  const start = useCallback(async (request: OrchestrationRequest) => {
    if (!sessionId) {
      setError('No session ID provided');
      return;
    }

    try {
      setError(null);
      mockStepRef.current = 0;

      // Initialize status
      const initialStatus: OrchestrationStatus = {
        session_id: sessionId,
        status: 'started',
        progress_percentage: 0,
        current_step: 'Initializing',
        tasks_completed: 0,
        tasks_total: 4,
        artifacts_generated: 0,
      };
      setStatus(initialStatus);

      // Initialize store
      setOrchestrationProgress(sessionId, {
        sessionId,
        status: 'started',
        currentAgent: 'analysis',
        completedSteps: [],
        totalSteps: 4,
        artifacts: [],
      });

      if (!isMockMode()) {
        // Start real orchestration
        await orchestrationService.start(request);
      }

      // Start polling
      pollingRef.current = setInterval(pollStatus, pollingInterval);
      pollStatus(); // Initial poll
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to start orchestration';
      setError(errorMessage);
      setStatus((prev) => prev ? { ...prev, status: 'failed', error: errorMessage } : null);
    }
  }, [sessionId, pollingInterval, pollStatus, setOrchestrationProgress]);

  /**
   * Cancel orchestration
   */
  const cancel = useCallback(async () => {
    if (!sessionId) return;

    try {
      stopPolling();

      if (!isMockMode()) {
        await orchestrationService.cancel(sessionId);
      }

      setStatus((prev) => prev ? { ...prev, status: 'cancelled' } : null);
      updateOrchestrationProgress(sessionId, { status: 'failed', error: 'Cancelled by user' });
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to cancel';
      setError(errorMessage);
    }
  }, [sessionId, stopPolling, updateOrchestrationProgress]);

  /**
   * Reset state
   */
  const reset = useCallback(() => {
    stopPolling();
    setStatus(null);
    setError(null);
    setArtifacts([]);
    mockStepRef.current = 0;
  }, [stopPolling]);

  /**
   * Public fetch artifacts
   */
  const fetchArtifacts = useCallback(async () => {
    await fetchArtifactsInternal();
  }, [fetchArtifactsInternal]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    status,
    isRunning,
    isCompleted,
    isFailed,
    error,
    artifacts,
    start,
    cancel,
    reset,
    fetchArtifacts,
  };
}

/**
 * Hook for getting mock data in development
 */
export function useMockData() {
  return {
    isMockMode: isMockMode(),
    mockArtifacts,
    mockBlockNodes,
    mockMindMapNodes,
  };
}

export default useOrchestration;
