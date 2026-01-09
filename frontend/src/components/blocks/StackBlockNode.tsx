/**
 * StackBlockNode component
 * Displays technology stack recommendations in block format
 */

import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { Package, Server, Database, Cloud, Cpu, Wrench } from 'lucide-react';
import { BaseBlockNode } from './BaseBlockNode';
import { TechStackBadge, type TechCategory } from '../shared/TechStackBadge';
import type { StackBlockSummary } from '@/types';

/**
 * Props extending BlockNodeData with stack-specific data
 */
interface StackNodeData extends StackBlockSummary {
  title: string;
  type: 'stack';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  qualityScore?: number;
}

/**
 * Category icons
 */
const categoryIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  frontend: Package,
  backend: Server,
  database: Database,
  infrastructure: Cloud,
  ai: Cpu,
  devops: Wrench,
};

/**
 * StackBlockNode - Displays technology stack recommendations
 */
export const StackBlockNode = memo(function StackBlockNode(
  props: NodeProps<StackNodeData>
) {
  const { data } = props;
  const {
    frontend = [],
    backend = [],
    database = [],
    infrastructure = [],
    reasoning = [],
  } = data;

  // Group all technologies by category
  const categories = [
    { name: 'Frontend', items: frontend, category: 'framework' as TechCategory },
    { name: 'Backend', items: backend, category: 'language' as TechCategory },
    { name: 'Database', items: database, category: 'database' as TechCategory },
    { name: 'Infrastructure', items: infrastructure, category: 'infrastructure' as TechCategory },
  ].filter((cat) => cat.items.length > 0);

  return (
    <BaseBlockNode
      {...props}
      icon={<Package className="h-4 w-4 text-emerald-600" />}
      headerColor="bg-emerald-50"
    >
      <div className="space-y-3">
        {/* Technology Categories */}
        {categories.map(({ name, items, category }) => {
          const IconComponent = categoryIcons[name.toLowerCase()] || Package;
          return (
            <div key={name}>
              <div className="flex items-center gap-1.5 mb-1.5">
                <IconComponent className="h-3.5 w-3.5 text-emerald-500" />
                <span className="text-xs font-medium text-gray-700">
                  {name} ({items.length})
                </span>
              </div>
              <div className="flex flex-wrap gap-1">
                {items.slice(0, 4).map((tech, idx) => {
                  const techName = typeof tech === 'string' ? tech : tech.name;
                  const techCategory = typeof tech === 'object' && tech.category
                    ? tech.category as TechCategory
                    : category;
                  return (
                    <TechStackBadge
                      key={idx}
                      name={techName}
                      category={techCategory}
                      size="sm"
                    />
                  );
                })}
                {items.length > 4 && (
                  <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">
                    +{items.length - 4}
                  </span>
                )}
              </div>
            </div>
          );
        })}

        {/* Stack Summary */}
        {categories.length > 0 && (
          <div className="pt-2 border-t border-gray-100">
            <div className="flex items-center justify-between text-xs">
              <span className="text-gray-500">
                {categories.reduce((acc, cat) => acc + cat.items.length, 0)} technologies
              </span>
              {reasoning.length > 0 && (
                <span className="text-emerald-600 font-medium">
                  {reasoning.length} recommendation{reasoning.length !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Reasoning preview */}
        {reasoning.length > 0 && (
          <div className="text-xs text-gray-500 bg-gray-50 rounded p-2">
            <p className="line-clamp-2">
              {typeof reasoning[0] === 'string' ? reasoning[0] : reasoning[0].reason}
            </p>
          </div>
        )}
      </div>
    </BaseBlockNode>
  );
});

export default StackBlockNode;
