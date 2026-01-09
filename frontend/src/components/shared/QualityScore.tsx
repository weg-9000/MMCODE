/**
 * QualityScore component
 * Displays quality score with visual indicator
 */

import { clsx } from 'clsx';
import { CheckCircle, AlertTriangle, XCircle, type LucideIcon } from 'lucide-react';

type QualityLevel = 'excellent' | 'good' | 'warning' | 'poor';

/**
 * Get quality level from score
 */
function getQualityLevel(score: number): QualityLevel {
  if (score >= 0.9) return 'excellent';
  if (score >= 0.7) return 'good';
  if (score >= 0.5) return 'warning';
  return 'poor';
}

/**
 * Quality level configuration
 */
const qualityConfig: Record<
  QualityLevel,
  { color: string; bgColor: string; icon: LucideIcon; label: string }
> = {
  excellent: {
    color: 'text-quality-excellent',
    bgColor: 'bg-green-100',
    icon: CheckCircle,
    label: 'Excellent',
  },
  good: {
    color: 'text-quality-good',
    bgColor: 'bg-blue-100',
    icon: CheckCircle,
    label: 'Good',
  },
  warning: {
    color: 'text-quality-warning',
    bgColor: 'bg-yellow-100',
    icon: AlertTriangle,
    label: 'Needs Improvement',
  },
  poor: {
    color: 'text-quality-poor',
    bgColor: 'bg-red-100',
    icon: XCircle,
    label: 'Poor',
  },
};

export interface QualityScoreProps {
  score: number;
  showLabel?: boolean;
  showPercentage?: boolean;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'default' | 'badge' | 'bar' | 'ring';
  className?: string;
}

export interface QualityBreakdownItem {
  label: string;
  score: number;
}

export function QualityScore({
  score,
  showLabel = false,
  showPercentage = true,
  size = 'md',
  variant = 'default',
  className,
}: QualityScoreProps) {
  const level = getQualityLevel(score);
  const config = qualityConfig[level];
  const percentage = Math.round(score * 100);
  const Icon = config.icon;

  const sizeClasses = {
    sm: 'text-xs',
    md: 'text-sm',
    lg: 'text-base',
  };

  const iconSizes = {
    sm: 12,
    md: 16,
    lg: 20,
  };

  if (variant === 'badge') {
    return (
      <span
        className={clsx(
          'inline-flex items-center gap-1 rounded-full px-2 py-0.5 font-medium',
          config.bgColor,
          config.color,
          sizeClasses[size],
          className
        )}
      >
        <Icon size={iconSizes[size]} />
        {showPercentage && <span>{percentage}%</span>}
        {showLabel && <span>{config.label}</span>}
      </span>
    );
  }

  if (variant === 'bar') {
    return (
      <div className={clsx('w-full', className)}>
        {(showLabel || showPercentage) && (
          <div className={clsx('flex justify-between mb-1', sizeClasses[size])}>
            {showLabel && <span className="text-gray-600">{config.label}</span>}
            {showPercentage && <span className={config.color}>{percentage}%</span>}
          </div>
        )}
        <div className="progress-bar">
          <div
            className={clsx('progress-bar-fill', {
              'bg-quality-excellent': level === 'excellent',
              'bg-quality-good': level === 'good',
              'bg-quality-warning': level === 'warning',
              'bg-quality-poor': level === 'poor',
            })}
            style={{ width: `${percentage}%` }}
          />
        </div>
      </div>
    );
  }

  if (variant === 'ring') {
    const ringSize = size === 'sm' ? 32 : size === 'md' ? 48 : 64;
    const strokeWidth = size === 'sm' ? 3 : size === 'md' ? 4 : 5;
    const radius = (ringSize - strokeWidth) / 2;
    const circumference = 2 * Math.PI * radius;
    const strokeDashoffset = circumference - (score * circumference);

    return (
      <div className={clsx('relative inline-flex items-center justify-center', className)}>
        <svg width={ringSize} height={ringSize} className="-rotate-90">
          {/* Background circle */}
          <circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            className="text-gray-200"
          />
          {/* Progress circle */}
          <circle
            cx={ringSize / 2}
            cy={ringSize / 2}
            r={radius}
            fill="none"
            stroke="currentColor"
            strokeWidth={strokeWidth}
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
            className={config.color}
          />
        </svg>
        {showPercentage && (
          <span
            className={clsx(
              'absolute font-semibold',
              config.color,
              size === 'sm' && 'text-[10px]',
              size === 'md' && 'text-xs',
              size === 'lg' && 'text-sm'
            )}
          >
            {percentage}
          </span>
        )}
      </div>
    );
  }

  // Default variant
  return (
    <span
      className={clsx(
        'quality-indicator inline-flex items-center gap-1',
        config.color,
        sizeClasses[size],
        className
      )}
    >
      <Icon size={iconSizes[size]} />
      {showPercentage && <span className="font-medium">{percentage}%</span>}
      {showLabel && <span>{config.label}</span>}
    </span>
  );
}

/**
 * QualityScoreBreakdown component
 * Shows multiple quality metrics
 */
interface QualityMetric {
  label: string;
  score: number;
}

interface QualityScoreBreakdownProps {
  metrics: QualityMetric[];
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function QualityScoreBreakdown({
  metrics,
  size = 'sm',
  className,
}: QualityScoreBreakdownProps) {
  return (
    <div className={clsx('space-y-2', className)}>
      {metrics.map((metric) => (
        <div key={metric.label}>
          <div className="flex justify-between text-xs text-gray-600 mb-1">
            <span>{metric.label}</span>
            <span>{Math.round(metric.score * 100)}%</span>
          </div>
          <QualityScore score={metric.score} variant="bar" size={size} showLabel={false} showPercentage={false} />
        </div>
      ))}
    </div>
  );
}

export default QualityScore;
