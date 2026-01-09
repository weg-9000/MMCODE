/**
 * Document viewers index
 * All viewers support lazy loading for code splitting
 */

import { lazy, Suspense, ComponentType } from 'react';
import { LoadingOverlay } from '../shared/LoadingOverlay';

// Lazy load viewers
const MarkdownViewer = lazy(() => import('./MarkdownViewer'));
const ERDViewer = lazy(() => import('./ERDViewer'));
const OpenAPIViewer = lazy(() => import('./OpenAPIViewer'));

/**
 * Create lazy wrapper HOC
 */
function withLazyLoading<P extends object>(
  LazyComponent: ComponentType<P>,
  loadingMessage: string
) {
  return function LazyWrapper(props: P) {
    return (
      <Suspense fallback={<LoadingOverlay message={loadingMessage} />}>
        <LazyComponent {...props} />
      </Suspense>
    );
  };
}

// Export lazy-loaded versions
export const MarkdownViewerLazy = withLazyLoading(
  MarkdownViewer,
  'Loading Markdown viewer...'
);

export const ERDViewerLazy = withLazyLoading(
  ERDViewer,
  'Loading ERD viewer...'
);

export const OpenAPIViewerLazy = withLazyLoading(
  OpenAPIViewer,
  'Loading API documentation...'
);

// Re-export original components for direct imports
export { MarkdownViewer } from './MarkdownViewer';
export { ERDViewer } from './ERDViewer';
export { OpenAPIViewer } from './OpenAPIViewer';
