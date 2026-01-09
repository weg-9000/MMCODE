/**
 * ArchitectureBlockNode component
 * Displays architecture design results in block format
 */

import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { Layers, Box, GitBranch, FileCode } from 'lucide-react';
import { clsx } from 'clsx';
import { BaseBlockNode } from './BaseBlockNode';
import type { ArchitectureBlockSummary } from '@/types';

/**
 * Props extending BlockNodeData with architecture-specific data
 */
interface ArchitectureNodeData extends ArchitectureBlockSummary {
  title: string;
  type: 'architecture';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  qualityScore?: number;
}

/**
 * Pattern color mapping
 */
const patternColors: Record<string, string> = {
  microservices: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  monolithic: 'bg-slate-100 text-slate-700 border-slate-200',
  serverless: 'bg-violet-100 text-violet-700 border-violet-200',
  'event-driven': 'bg-amber-100 text-amber-700 border-amber-200',
  layered: 'bg-blue-100 text-blue-700 border-blue-200',
  hexagonal: 'bg-emerald-100 text-emerald-700 border-emerald-200',
  cqrs: 'bg-rose-100 text-rose-700 border-rose-200',
  ddd: 'bg-indigo-100 text-indigo-700 border-indigo-200',
};

/**
 * Get pattern color class
 */
function getPatternColor(pattern: string): string {
  const key = pattern.toLowerCase().replace(/[\s-_]/g, '-');
  return patternColors[key] || 'bg-gray-100 text-gray-700 border-gray-200';
}

/**
 * ArchitectureBlockNode - Displays architecture design
 */
export const ArchitectureBlockNode = memo(function ArchitectureBlockNode(
  props: NodeProps<ArchitectureNodeData>
) {
  const { data } = props;
  const {
    patterns = [],
    layers = [],
    components = [],
    decisions = [],
  } = data;

  return (
    <BaseBlockNode
      {...props}
      icon={<Layers className="h-4 w-4 text-cyan-600" />}
      headerColor="bg-cyan-50"
    >
      <div className="space-y-3">
        {/* Architecture Patterns */}
        {patterns.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <GitBranch className="h-3.5 w-3.5 text-cyan-500" />
              <span className="text-xs font-medium text-gray-700">
                Patterns ({patterns.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {patterns.slice(0, 3).map((pattern, idx) => {
                const name = typeof pattern === 'string' ? pattern : pattern.name;
                return (
                  <span
                    key={idx}
                    className={clsx(
                      'px-2 py-0.5 text-xs rounded-full border font-medium',
                      getPatternColor(name)
                    )}
                  >
                    {name}
                  </span>
                );
              })}
              {patterns.length > 3 && (
                <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">
                  +{patterns.length - 3}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Layers */}
        {layers.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Layers className="h-3.5 w-3.5 text-blue-500" />
              <span className="text-xs font-medium text-gray-700">
                Layers ({layers.length})
              </span>
            </div>
            <div className="space-y-1">
              {layers.slice(0, 4).map((layer, idx) => {
                const name = typeof layer === 'string' ? layer : layer.name;
                return (
                  <div
                    key={idx}
                    className="flex items-center gap-2 px-2 py-1 bg-gray-50 rounded text-xs"
                  >
                    <div
                      className="w-2 h-2 rounded-sm"
                      style={{
                        backgroundColor: `hsl(${(idx * 60 + 180) % 360}, 60%, 60%)`,
                      }}
                    />
                    <span className="text-gray-700">{name}</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* Components */}
        {components.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 mb-1.5">
              <Box className="h-3.5 w-3.5 text-emerald-500" />
              <span className="text-xs font-medium text-gray-700">
                Components ({components.length})
              </span>
            </div>
            <div className="flex flex-wrap gap-1">
              {components.slice(0, 4).map((component, idx) => {
                const name = typeof component === 'string' ? component : component.name;
                return (
                  <span
                    key={idx}
                    className="px-2 py-0.5 text-xs bg-emerald-50 text-emerald-700 rounded border border-emerald-200"
                  >
                    {name}
                  </span>
                );
              })}
              {components.length > 4 && (
                <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">
                  +{components.length - 4}
                </span>
              )}
            </div>
          </div>
        )}

        {/* ADR Count */}
        {decisions.length > 0 && (
          <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
            <FileCode className="h-3.5 w-3.5 text-gray-400" />
            <span className="text-xs text-gray-500">
              {decisions.length} architecture decision{decisions.length !== 1 ? 's' : ''}
            </span>
          </div>
        )}
      </div>
    </BaseBlockNode>
  );
});

export default ArchitectureBlockNode;
