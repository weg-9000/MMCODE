/**
 * SessionBlockNode component
 * Displays session/project overview as the root block
 */

import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { FolderKanban, Clock, CheckCircle2, XCircle, Loader2 } from 'lucide-react';
import { clsx } from 'clsx';
import { BaseBlockNode } from './BaseBlockNode';
import type { SessionBlockSummary } from '@/types';

/**
 * Props extending BlockNodeData with session-specific data
 */
interface SessionNodeData extends SessionBlockSummary {
  title: string;
  type: 'session';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  qualityScore?: number;
}

/**
 * Status icons
 */
const statusIcons = {
  pending: Clock,
  processing: Loader2,
  completed: CheckCircle2,
  failed: XCircle,
};

/**
 * Status colors
 */
const statusColors = {
  pending: 'text-gray-500',
  processing: 'text-blue-500',
  completed: 'text-green-500',
  failed: 'text-red-500',
};

/**
 * SessionBlockNode - Displays session overview
 */
export const SessionBlockNode = memo(function SessionBlockNode(
  props: NodeProps<SessionNodeData>
) {
  const { data } = props;
  const {
    taskCount = 0,
    completedTasks = 0,
    artifactCount = 0,
    createdAt,
    updatedAt,
  } = data;

  const progress = taskCount > 0 ? (completedTasks / taskCount) * 100 : 0;
  const StatusIcon = statusIcons[data.status];

  return (
    <BaseBlockNode
      {...props}
      icon={<FolderKanban className="h-4 w-4 text-indigo-600" />}
      headerColor="bg-indigo-50"
    >
      <div className="space-y-3">
        {/* Status */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <StatusIcon
              className={clsx(
                'h-4 w-4',
                statusColors[data.status],
                data.status === 'processing' && 'animate-spin'
              )}
            />
            <span className="text-sm font-medium text-gray-700 capitalize">
              {data.status}
            </span>
          </div>
          {data.qualityScore !== undefined && (
            <span
              className={clsx(
                'text-xs font-semibold px-2 py-0.5 rounded',
                data.qualityScore >= 0.8
                  ? 'bg-green-100 text-green-700'
                  : data.qualityScore >= 0.6
                  ? 'bg-yellow-100 text-yellow-700'
                  : 'bg-red-100 text-red-700'
              )}
            >
              {Math.round(data.qualityScore * 100)}%
            </span>
          )}
        </div>

        {/* Progress Bar */}
        {taskCount > 0 && (
          <div>
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Progress</span>
              <span>
                {completedTasks}/{taskCount} tasks
              </span>
            </div>
            <div className="progress-bar">
              <div
                className="progress-bar-fill"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Stats Grid */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-gray-50 rounded p-2">
            <div className="text-lg font-semibold text-gray-900">
              {taskCount}
            </div>
            <div className="text-xs text-gray-500">Tasks</div>
          </div>
          <div className="bg-gray-50 rounded p-2">
            <div className="text-lg font-semibold text-gray-900">
              {artifactCount}
            </div>
            <div className="text-xs text-gray-500">Artifacts</div>
          </div>
        </div>

        {/* Timestamps */}
        <div className="pt-2 border-t border-gray-100 space-y-1">
          {createdAt && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Created</span>
              <span className="text-gray-700">
                {new Date(createdAt).toLocaleDateString()}
              </span>
            </div>
          )}
          {updatedAt && (
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Updated</span>
              <span className="text-gray-700">
                {new Date(updatedAt).toLocaleDateString()}
              </span>
            </div>
          )}
        </div>
      </div>
    </BaseBlockNode>
  );
});

export default SessionBlockNode;
