/**
 * BaseBlockNode component
 * Base component for all block node types in the canvas
 */

import { memo, ReactNode } from 'react';
import { Handle, Position, NodeProps } from 'reactflow';
import { clsx } from 'clsx';
import { motion } from 'framer-motion';
import { MoreVertical, Expand, Link2 } from 'lucide-react';
import type { BlockNodeData, BlockStatus } from '@/types';

/**
 * Status indicator colors
 */
const statusColors: Record<BlockStatus, string> = {
  pending: 'bg-gray-400',
  processing: 'bg-blue-500 animate-pulse',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

/**
 * Props for BaseBlockNode
 */
export interface BaseBlockNodeProps extends NodeProps<BlockNodeData> {
  icon: ReactNode;
  headerColor: string;
  children: ReactNode;
  onExpand?: () => void;
  onMenuClick?: () => void;
}

/**
 * BaseBlockNode - Shared structure for all block types
 */
export const BaseBlockNode = memo(function BaseBlockNode({
  data,
  selected,
  icon,
  headerColor,
  children,
  onExpand,
  onMenuClick,
}: BaseBlockNodeProps) {
  const { title, type, status, qualityScore } = data;

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      className={clsx(
        'block-node min-w-[280px] max-w-[320px]',
        `type-${type}`,
        selected && 'selected',
        status === 'processing' && 'processing'
      )}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Top}
        className="!w-3 !h-3 !bg-gray-300 !border-2 !border-white"
      />

      {/* Header */}
      <div
        className={clsx(
          'flex items-center gap-2 px-3 py-2 rounded-t-xl border-b',
          headerColor
        )}
      >
        <div className="flex-shrink-0">{icon}</div>
        <h3 className="flex-1 text-sm font-semibold text-gray-800 truncate">
          {title}
        </h3>
        <div className="flex items-center gap-1">
          {/* Status indicator */}
          <span
            className={clsx(
              'w-2 h-2 rounded-full',
              statusColors[status]
            )}
            title={status}
          />
          {/* Quality score badge */}
          {qualityScore !== undefined && (
            <span
              className={clsx(
                'text-xs font-medium px-1.5 py-0.5 rounded',
                qualityScore >= 0.8
                  ? 'bg-green-100 text-green-700'
                  : qualityScore >= 0.6
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-red-100 text-red-700'
              )}
            >
              {Math.round(qualityScore * 100)}%
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-3">{children}</div>

      {/* Footer with actions */}
      <div className="flex items-center justify-between px-3 py-2 border-t border-gray-100 bg-gray-50/50 rounded-b-xl">
        <div className="flex items-center gap-1">
          <button
            onClick={onExpand}
            className="p-1 rounded hover:bg-gray-200 transition-colors"
            title="Expand details"
          >
            <Expand className="h-3.5 w-3.5 text-gray-500" />
          </button>
          <button
            className="p-1 rounded hover:bg-gray-200 transition-colors"
            title="View connections"
          >
            <Link2 className="h-3.5 w-3.5 text-gray-500" />
          </button>
        </div>
        <button
          onClick={onMenuClick}
          className="p-1 rounded hover:bg-gray-200 transition-colors"
          title="More options"
        >
          <MoreVertical className="h-3.5 w-3.5 text-gray-500" />
        </button>
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Bottom}
        className="!w-3 !h-3 !bg-gray-300 !border-2 !border-white"
      />
    </motion.div>
  );
});

export default BaseBlockNode;
