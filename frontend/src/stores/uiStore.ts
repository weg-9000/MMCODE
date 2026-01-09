/**
 * UI store
 * Global state for UI elements like sidebar, modals, notifications
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

/**
 * Notification type
 */
export interface Notification {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  title: string;
  message?: string;
  duration?: number;
  dismissible?: boolean;
}

/**
 * Modal configuration
 */
export interface ModalConfig {
  id: string;
  title: string;
  content?: React.ReactNode;
  size?: 'sm' | 'md' | 'lg' | 'xl';
  closable?: boolean;
  onClose?: () => void;
}

/**
 * Theme type
 */
export type Theme = 'light' | 'dark' | 'system';

/**
 * UI store state
 */
interface UIState {
  // Sidebar
  sidebarOpen: boolean;
  sidebarWidth: number;

  // Theme
  theme: Theme;

  // Notifications
  notifications: Notification[];

  // Modals
  activeModal: ModalConfig | null;

  // Loading states
  globalLoading: boolean;
  loadingMessage: string | null;

  // Preferences
  compactMode: boolean;
  showQualityScores: boolean;
  showTechBadges: boolean;

  // Actions - Sidebar
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setSidebarWidth: (width: number) => void;

  // Actions - Theme
  setTheme: (theme: Theme) => void;

  // Actions - Notifications
  addNotification: (notification: Omit<Notification, 'id'>) => void;
  removeNotification: (id: string) => void;
  clearNotifications: () => void;

  // Actions - Modals
  openModal: (config: Omit<ModalConfig, 'id'>) => void;
  closeModal: () => void;

  // Actions - Loading
  setGlobalLoading: (loading: boolean, message?: string) => void;

  // Actions - Preferences
  toggleCompactMode: () => void;
  toggleQualityScores: () => void;
  toggleTechBadges: () => void;
  setPreference: <K extends keyof UIPreferences>(key: K, value: UIPreferences[K]) => void;
}

/**
 * UI preferences subset for persistence
 */
interface UIPreferences {
  compactMode: boolean;
  showQualityScores: boolean;
  showTechBadges: boolean;
  theme: Theme;
  sidebarWidth: number;
}

/**
 * Generate unique ID
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * UI store
 */
export const useUIStore = create<UIState>()(
  devtools(
    persist(
      (set, get) => ({
        // Initial state
        sidebarOpen: true,
        sidebarWidth: 280,
        theme: 'system',
        notifications: [],
        activeModal: null,
        globalLoading: false,
        loadingMessage: null,
        compactMode: false,
        showQualityScores: true,
        showTechBadges: true,

        // Sidebar actions
        toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
        setSidebarOpen: (open) => set({ sidebarOpen: open }),
        setSidebarWidth: (width) => set({ sidebarWidth: Math.max(200, Math.min(400, width)) }),

        // Theme actions
        setTheme: (theme) => {
          set({ theme });
          // Apply theme to document
          if (theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
            document.documentElement.classList.add('dark');
          } else {
            document.documentElement.classList.remove('dark');
          }
        },

        // Notification actions
        addNotification: (notification) => {
          const id = generateId();
          const newNotification: Notification = {
            id,
            duration: 5000,
            dismissible: true,
            ...notification,
          };

          set((state) => ({
            notifications: [...state.notifications, newNotification],
          }));

          // Auto-remove after duration
          if (newNotification.duration && newNotification.duration > 0) {
            setTimeout(() => {
              get().removeNotification(id);
            }, newNotification.duration);
          }
        },

        removeNotification: (id) =>
          set((state) => ({
            notifications: state.notifications.filter((n) => n.id !== id),
          })),

        clearNotifications: () => set({ notifications: [] }),

        // Modal actions
        openModal: (config) =>
          set({
            activeModal: {
              id: generateId(),
              size: 'md',
              closable: true,
              ...config,
            },
          }),

        closeModal: () => {
          const modal = get().activeModal;
          if (modal?.onClose) {
            modal.onClose();
          }
          set({ activeModal: null });
        },

        // Loading actions
        setGlobalLoading: (loading, message) =>
          set({
            globalLoading: loading,
            loadingMessage: loading ? message || null : null,
          }),

        // Preference actions
        toggleCompactMode: () => set((state) => ({ compactMode: !state.compactMode })),
        toggleQualityScores: () =>
          set((state) => ({ showQualityScores: !state.showQualityScores })),
        toggleTechBadges: () => set((state) => ({ showTechBadges: !state.showTechBadges })),

        setPreference: (key, value) => set({ [key]: value }),
      }),
      {
        name: 'mmcode-ui-store',
        partialize: (state) => ({
          theme: state.theme,
          sidebarWidth: state.sidebarWidth,
          compactMode: state.compactMode,
          showQualityScores: state.showQualityScores,
          showTechBadges: state.showTechBadges,
        }),
      }
    ),
    { name: 'UIStore' }
  )
);

/**
 * Convenience hooks for notifications
 * Uses individual selectors to prevent infinite re-renders
 */
export const useNotifications = () => {
  const notifications = useUIStore((state) => state.notifications);
  const addNotification = useUIStore((state) => state.addNotification);
  const removeNotification = useUIStore((state) => state.removeNotification);
  const clearNotifications = useUIStore((state) => state.clearNotifications);

  return {
    notifications,
    notify: addNotification,
    remove: removeNotification,
    clear: clearNotifications,
    success: (title: string, message?: string) =>
      addNotification({ type: 'success', title, message }),
    error: (title: string, message?: string) =>
      addNotification({ type: 'error', title, message }),
    warning: (title: string, message?: string) =>
      addNotification({ type: 'warning', title, message }),
    info: (title: string, message?: string) =>
      addNotification({ type: 'info', title, message }),
  };
};

export default useUIStore;
