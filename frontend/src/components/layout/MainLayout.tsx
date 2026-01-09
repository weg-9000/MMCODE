/**
 * MainLayout component
 * Main application layout with header, sidebar, and content area
 */

import { Outlet } from 'react-router-dom';
import { Suspense } from 'react';
import { Header } from './Header';
import { Sidebar } from './Sidebar';
import { useUIStore } from '@/stores';
import { clsx } from 'clsx';
import { LoadingOverlay } from '@/components/shared/LoadingOverlay';
import { NotificationContainer } from '@/components/shared/NotificationContainer';

export function MainLayout() {
  // Use individual selectors to prevent infinite re-renders
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const sidebarWidth = useUIStore((state) => state.sidebarWidth);
  const globalLoading = useUIStore((state) => state.globalLoading);
  const loadingMessage = useUIStore((state) => state.loadingMessage);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <Header />

      {/* Main content area */}
      <div className="flex">
        {/* Sidebar */}
        <Sidebar />

        {/* Content */}
        <main
          className={clsx(
            'flex-1 min-h-[calc(100vh-4rem)] transition-all duration-200',
            sidebarOpen ? 'lg:pl-0' : ''
          )}
          style={{
            marginLeft: sidebarOpen ? `${sidebarWidth}px` : 0,
          }}
        >
          <Suspense fallback={<PageLoadingFallback />}>
            <Outlet />
          </Suspense>
        </main>
      </div>

      {/* Global loading overlay */}
      {globalLoading && <LoadingOverlay message={loadingMessage || undefined} />}

      {/* Notifications */}
      <NotificationContainer />
    </div>
  );
}

/**
 * Page loading fallback
 */
function PageLoadingFallback() {
  return (
    <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        <p className="text-sm text-gray-500">Loading...</p>
      </div>
    </div>
  );
}

export default MainLayout;
