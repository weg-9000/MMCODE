/**
 * Lazy loaded MindMapView wrapper
 * Enables code splitting for mind map visualization
 */

import { lazy, Suspense } from 'react';
import { LoadingOverlay } from '../shared/LoadingOverlay';

// Lazy load the MindMapView component
const MindMapView = lazy(() => import('./MindMapView'));

/**
 * Props passed through to MindMapView
 */
interface MindMapViewLazyProps {
  className?: string;
  nodes?: any[];
}

/**
 * MindMapViewLazy - Lazy loaded wrapper with loading fallback
 */
export function MindMapViewLazy(props: MindMapViewLazyProps) {
  return (
    <Suspense
      fallback={
        <LoadingOverlay
          message="Loading mind map..."
          className="bg-gray-50"
        />
      }
    >
      <MindMapView {...props} />
    </Suspense>
  );
}

export default MindMapViewLazy;
