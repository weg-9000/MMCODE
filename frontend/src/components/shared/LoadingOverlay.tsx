/**
 * LoadingOverlay component
 * Full-screen loading overlay with spinner
 */

import { clsx } from 'clsx';
import { Loader2 } from 'lucide-react';

interface LoadingOverlayProps {
  message?: string;
  className?: string;
  transparent?: boolean;
}

export function LoadingOverlay({
  message = 'Loading...',
  className,
  transparent = false,
}: LoadingOverlayProps) {
  return (
    <div
      className={clsx(
        'fixed inset-0 z-50 flex items-center justify-center',
        transparent ? 'bg-black/20' : 'bg-white/80',
        'backdrop-blur-sm',
        className
      )}
    >
      <div className="flex flex-col items-center gap-4 rounded-xl bg-white p-8 shadow-lg">
        <Loader2 className="h-8 w-8 animate-spin text-primary-600" />
        <p className="text-sm font-medium text-gray-600">{message}</p>
      </div>
    </div>
  );
}

/**
 * Loading spinner component
 */
interface LoadingSpinnerProps {
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function LoadingSpinner({ size = 'md', className }: LoadingSpinnerProps) {
  const sizeClasses = {
    sm: 'h-4 w-4',
    md: 'h-6 w-6',
    lg: 'h-8 w-8',
  };

  return (
    <Loader2
      className={clsx('animate-spin text-primary-600', sizeClasses[size], className)}
    />
  );
}

/**
 * Skeleton loader component
 */
interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export function Skeleton({
  className,
  variant = 'text',
  width,
  height,
}: SkeletonProps) {
  return (
    <div
      className={clsx(
        'skeleton',
        variant === 'circular' && 'rounded-full',
        variant === 'rectangular' && 'rounded-lg',
        variant === 'text' && 'rounded h-4',
        className
      )}
      style={{
        width: width,
        height: height,
      }}
    />
  );
}

/**
 * Block skeleton loader
 */
export function BlockSkeleton() {
  return (
    <div className="block-node p-4 w-[280px]">
      <div className="flex items-center gap-3 mb-3">
        <Skeleton variant="rectangular" width={32} height={32} />
        <div className="flex-1">
          <Skeleton width="70%" height={16} className="mb-1" />
          <Skeleton width="40%" height={12} />
        </div>
      </div>
      <div className="flex gap-1 mb-3">
        <Skeleton variant="rectangular" width={60} height={20} className="rounded-full" />
        <Skeleton variant="rectangular" width={60} height={20} className="rounded-full" />
        <Skeleton variant="rectangular" width={60} height={20} className="rounded-full" />
      </div>
      <div className="space-y-2">
        <Skeleton width="100%" height={12} />
        <Skeleton width="80%" height={12} />
        <Skeleton width="60%" height={12} />
      </div>
    </div>
  );
}

/**
 * Page loading state
 */
interface PageLoadingProps {
  message?: string;
}

export function PageLoading({ message = 'Loading...' }: PageLoadingProps) {
  return (
    <div className="flex h-[calc(100vh-4rem)] items-center justify-center">
      <div className="flex flex-col items-center gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary-200 border-t-primary-600" />
        <p className="text-sm text-gray-500">{message}</p>
      </div>
    </div>
  );
}

export default LoadingOverlay;
