/**
 * Lazy loaded BlockCanvas wrapper
 * Enables code splitting for React Flow visualization
 */

import { lazy, Suspense } from 'react';
import { LoadingOverlay } from '../shared/LoadingOverlay';

// Lazy load the BlockCanvas component
const BlockCanvas = lazy(() => import('./BlockCanvas'));

/**
 * Props passed through to BlockCanvas
 */
interface BlockCanvasLazyProps {
  className?: string;
  onNodeClick?: (node: any) => void;
  onNodeDoubleClick?: (node: any) => void;
  readOnly?: boolean;
}

/**
 * BlockCanvasLazy - Lazy loaded wrapper with loading fallback
 */
export function BlockCanvasLazy(props: BlockCanvasLazyProps) {
  return (
    <Suspense
      fallback={
        <LoadingOverlay
          message="Loading visualization..."
          className="bg-gray-50"
        />
      }
    >
      <BlockCanvas {...props} />
    </Suspense>
  );
}

export default BlockCanvasLazy;
