/**
 * Session store
 * Global state management for sessions and orchestration
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';
import type { Session, WorkflowStatus } from '@/types';

/**
 * Orchestration progress state for a single session
 */
export interface OrchestrationProgressItem {
  sessionId: string;
  status: WorkflowStatus | 'idle';
  currentAgent: string | null;
  completedSteps: string[];
  totalSteps: number;
  artifacts: string[];
  error?: string;
}

/**
 * Session store state
 */
export interface SessionState {
  // Sessions data as Record for easy lookup
  sessions: Record<string, Session>;
  currentSessionId: string | null;
  isLoadingSessions: boolean;
  sessionsError: string | null;

  // Orchestration state per session
  orchestrationProgress: Record<string, OrchestrationProgressItem>;
  isOrchestrating: boolean;

  // Recent sessions (for sidebar)
  recentSessionIds: string[];

  // Actions
  setSessions: (sessions: Session[]) => void;
  addSession: (session: Session) => void;
  updateSession: (sessionId: string, updates: Partial<Session>) => void;
  removeSession: (sessionId: string) => void;
  setCurrentSession: (sessionId: string | null) => void;
  setLoadingSessions: (isLoading: boolean) => void;
  setSessionsError: (error: string | null) => void;

  // Orchestration actions
  setOrchestrationProgress: (sessionId: string, progress: OrchestrationProgressItem) => void;
  updateOrchestrationProgress: (sessionId: string, updates: Partial<OrchestrationProgressItem>) => void;
  startOrchestration: (sessionId: string) => void;
  completeOrchestration: (sessionId: string) => void;
  failOrchestration: (sessionId: string, error: string) => void;
  resetOrchestration: (sessionId: string) => void;

  // Recent sessions actions
  addToRecentSessions: (sessionId: string) => void;
  clearRecentSessions: () => void;
}

/**
 * Session store
 */
export const useSessionStore = create<SessionState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        sessions: {},
        currentSessionId: null,
        isLoadingSessions: false,
        sessionsError: null,
        orchestrationProgress: {},
        isOrchestrating: false,
        recentSessionIds: [],

        // Session actions
        setSessions: (sessions) =>
          set({
            sessions: sessions.reduce((acc, session) => {
              acc[session.id] = session;
              return acc;
            }, {} as Record<string, Session>),
            sessionsError: null,
          }),

        addSession: (session) =>
          set((state) => ({
            sessions: { ...state.sessions, [session.id]: session },
          })),

        updateSession: (sessionId, updates) =>
          set((state) => {
            const existing = state.sessions[sessionId];
            if (!existing) return state;
            return {
              sessions: {
                ...state.sessions,
                [sessionId]: { ...existing, ...updates },
              },
            };
          }),

        removeSession: (sessionId) =>
          set((state) => {
            const { [sessionId]: removed, ...rest } = state.sessions;
            return {
              sessions: rest,
              currentSessionId:
                state.currentSessionId === sessionId ? null : state.currentSessionId,
              recentSessionIds: state.recentSessionIds.filter((id) => id !== sessionId),
            };
          }),

        setCurrentSession: (sessionId) => {
          set({ currentSessionId: sessionId });
          if (sessionId) {
            get().addToRecentSessions(sessionId);
          }
        },

        setLoadingSessions: (isLoading) => set({ isLoadingSessions: isLoading }),

        setSessionsError: (error) => set({ sessionsError: error }),

        // Orchestration actions
        setOrchestrationProgress: (sessionId, progress) =>
          set((state) => ({
            orchestrationProgress: {
              ...state.orchestrationProgress,
              [sessionId]: progress,
            },
          })),

        updateOrchestrationProgress: (sessionId, updates) =>
          set((state) => {
            const existing = state.orchestrationProgress[sessionId];
            if (!existing) return state;
            return {
              orchestrationProgress: {
                ...state.orchestrationProgress,
                [sessionId]: { ...existing, ...updates },
              },
            };
          }),

        startOrchestration: (sessionId) =>
          set((state) => ({
            isOrchestrating: true,
            orchestrationProgress: {
              ...state.orchestrationProgress,
              [sessionId]: {
                sessionId,
                status: 'in_progress',
                currentAgent: 'analysis',
                completedSteps: [],
                totalSteps: 4,
                artifacts: [],
              },
            },
          })),

        completeOrchestration: (sessionId) =>
          set((state) => ({
            isOrchestrating: false,
            orchestrationProgress: {
              ...state.orchestrationProgress,
              [sessionId]: {
                ...state.orchestrationProgress[sessionId],
                status: 'completed',
                currentAgent: null,
              },
            },
          })),

        failOrchestration: (sessionId, error) =>
          set((state) => ({
            isOrchestrating: false,
            orchestrationProgress: {
              ...state.orchestrationProgress,
              [sessionId]: {
                ...state.orchestrationProgress[sessionId],
                status: 'failed',
                error,
                currentAgent: null,
              },
            },
          })),

        resetOrchestration: (sessionId) =>
          set((state) => {
            const { [sessionId]: removed, ...rest } = state.orchestrationProgress;
            return {
              isOrchestrating: false,
              orchestrationProgress: rest,
            };
          }),

        // Recent sessions actions
        addToRecentSessions: (sessionId) =>
          set((state) => {
            const filtered = state.recentSessionIds.filter((id) => id !== sessionId);
            return {
              recentSessionIds: [sessionId, ...filtered].slice(0, 10),
            };
          }),

        clearRecentSessions: () => set({ recentSessionIds: [] }),
      }),
      {
        name: 'mmcode-session-store',
        partialize: (state) => ({
          recentSessionIds: state.recentSessionIds,
        }),
      }
    ),
    { name: 'SessionStore' }
  )
);

/**
 * Selectors
 */
export const selectCurrentSession = (state: SessionState) =>
  state.currentSessionId ? state.sessions[state.currentSessionId] : null;
export const selectSessions = (state: SessionState) => Object.values(state.sessions);
export const selectIsOrchestrating = (state: SessionState) => state.isOrchestrating;
export const selectOrchestrationProgress = (state: SessionState) => state.orchestrationProgress;
export const selectRecentSessions = (state: SessionState) =>
  state.recentSessionIds
    .map((id) => state.sessions[id])
    .filter(Boolean) as Session[];

export default useSessionStore;
