/**
 * Pages index with lazy loading support
 */

import { lazy, Suspense, ComponentType } from 'react';
import { PageLoading } from '@/components/shared/LoadingOverlay';

// Lazy load pages for code splitting
const Dashboard = lazy(() => import('./Dashboard'));
const RequirementInput = lazy(() => import('./RequirementInput'));
const ProjectVisualization = lazy(() => import('./ProjectVisualization'));
const DocumentViewer = lazy(() => import('./DocumentViewer'));

/**
 * Create lazy wrapper for pages
 */
function withPageLoading<P extends object>(LazyComponent: ComponentType<P>) {
  return function LazyPage(props: P) {
    return (
      <Suspense fallback={<PageLoading />}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}

// Export lazy-loaded pages
export const DashboardPage = withPageLoading(Dashboard);
export const RequirementInputPage = withPageLoading(RequirementInput);
export const ProjectVisualizationPage = withPageLoading(ProjectVisualization);
export const DocumentViewerPage = withPageLoading(DocumentViewer);

// Re-export original components for testing
export { Dashboard, RequirementInput, ProjectVisualization, DocumentViewer };
