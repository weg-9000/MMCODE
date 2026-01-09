/**
 * MindMapView component
 * Hierarchical mind-map style visualization of blocks
 */

import { useCallback, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronRight,
  ChevronDown,
  FileSearch,
  Layers,
  Package,
  FileText,
  FolderKanban,
  Circle,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useVisualizationStore } from '@/stores';
import { TechStackBadge } from '../shared/TechStackBadge';
import type { MindMapNode, BlockType, BlockStatus } from '@/types';

/**
 * Extended node type for mind map nodes
 */
type ExtendedNodeType = BlockType | 'entity' | 'use-case' | 'pattern' | 'component' | 'technology' | 'document';

/**
 * Block type icons
 */
const typeIcons: Record<ExtendedNodeType, React.ComponentType<{ className?: string }>> = {
  analysis: FileSearch,
  architecture: Layers,
  stack: Package,
  document: FileText,
  session: FolderKanban,
  entity: Circle,
  'use-case': Circle,
  pattern: Layers,
  component: Package,
  technology: Package,
};

/**
 * Block type colors
 */
const typeColors: Record<ExtendedNodeType, string> = {
  analysis: 'text-purple-500 bg-purple-50 border-purple-200',
  architecture: 'text-cyan-500 bg-cyan-50 border-cyan-200',
  stack: 'text-emerald-500 bg-emerald-50 border-emerald-200',
  document: 'text-amber-500 bg-amber-50 border-amber-200',
  session: 'text-indigo-500 bg-indigo-50 border-indigo-200',
  entity: 'text-gray-500 bg-gray-50 border-gray-200',
  'use-case': 'text-blue-500 bg-blue-50 border-blue-200',
  pattern: 'text-violet-500 bg-violet-50 border-violet-200',
  component: 'text-teal-500 bg-teal-50 border-teal-200',
  technology: 'text-orange-500 bg-orange-50 border-orange-200',
};

/**
 * Status colors
 */
const statusColors: Record<BlockStatus, string> = {
  pending: 'bg-gray-400',
  processing: 'bg-blue-500 animate-pulse',
  completed: 'bg-green-500',
  failed: 'bg-red-500',
};

/**
 * Props for MindMapNodeItem
 */
interface MindMapNodeItemProps {
  node: MindMapNode;
  level: number;
  onSelect: (nodeId: string) => void;
  selectedId: string | null;
  searchQuery: string;
}

/**
 * MindMapNodeItem - Single node in the mind map
 */
function MindMapNodeItem({
  node,
  level,
  onSelect,
  selectedId,
  searchQuery,
}: MindMapNodeItemProps) {
  const [isExpanded, setIsExpanded] = useState(level < 2);
  const hasChildren = node.children && node.children.length > 0;

  const IconComponent = typeIcons[node.type] || Circle;
  const colorClasses = typeColors[node.type] || 'text-gray-500 bg-gray-50 border-gray-200';

  // Highlight search matches
  const highlightText = useCallback(
    (text: string) => {
      if (!searchQuery) return text;
      const regex = new RegExp(`(${searchQuery})`, 'gi');
      const parts = text.split(regex);
      return parts.map((part, i) =>
        regex.test(part) ? (
          <mark key={i} className="bg-yellow-200 rounded px-0.5">
            {part}
          </mark>
        ) : (
          part
        )
      );
    },
    [searchQuery]
  );

  // Check if node matches search
  const matchesSearch = useMemo(() => {
    if (!searchQuery) return true;
    const query = searchQuery.toLowerCase();
    return (
      node.label.toLowerCase().includes(query) ||
      node.description?.toLowerCase().includes(query) ||
      node.techStack?.some((t) => t.toLowerCase().includes(query)) ||
      node.features?.some((f) => f.toLowerCase().includes(query))
    );
  }, [node, searchQuery]);

  // Auto-expand if children match search
  const hasMatchingChildren = useMemo(() => {
    if (!searchQuery || !hasChildren) return false;

    const checkChildren = (children: MindMapNode[]): boolean => {
      return children.some((child) => {
        const query = searchQuery.toLowerCase();
        const matches =
          child.label.toLowerCase().includes(query) ||
          child.description?.toLowerCase().includes(query);
        if (matches) return true;
        if (child.children) return checkChildren(child.children);
        return false;
      });
    };

    return checkChildren(node.children || []);
  }, [node.children, searchQuery, hasChildren]);

  // Auto-expand for search results
  const shouldExpand = isExpanded || hasMatchingChildren;

  if (!matchesSearch && !hasMatchingChildren) return null;

  return (
    <div className="select-none">
      {/* Node header */}
      <div
        onClick={() => onSelect(node.id)}
        className={clsx(
          'flex items-start gap-2 p-2 rounded-lg cursor-pointer transition-all',
          'hover:bg-gray-50',
          selectedId === node.id && 'bg-primary-50 ring-1 ring-primary-200'
        )}
        style={{ marginLeft: `${level * 24}px` }}
      >
        {/* Expand/collapse button */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            setIsExpanded(!isExpanded);
          }}
          className={clsx(
            'p-0.5 rounded hover:bg-gray-200 transition-colors',
            !hasChildren && 'invisible'
          )}
        >
          {shouldExpand ? (
            <ChevronDown className="h-4 w-4 text-gray-400" />
          ) : (
            <ChevronRight className="h-4 w-4 text-gray-400" />
          )}
        </button>

        {/* Type icon */}
        <div
          className={clsx(
            'p-1.5 rounded-lg border',
            colorClasses
          )}
        >
          <IconComponent className="h-4 w-4" />
        </div>

        {/* Content */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <h4 className="text-sm font-medium text-gray-900 truncate">
              {highlightText(node.label)}
            </h4>
            {/* Status indicator */}
            <span
              className={clsx(
                'w-2 h-2 rounded-full flex-shrink-0',
                statusColors[node.status]
              )}
              title={node.status}
            />
            {/* Quality score */}
            {node.qualityScore !== undefined && (
              <span
                className={clsx(
                  'text-xs font-medium px-1.5 py-0.5 rounded',
                  node.qualityScore >= 0.8
                    ? 'bg-green-100 text-green-700'
                    : node.qualityScore >= 0.6
                    ? 'bg-yellow-100 text-yellow-700'
                    : 'bg-red-100 text-red-700'
                )}
              >
                {Math.round(node.qualityScore * 100)}%
              </span>
            )}
          </div>

          {/* Description */}
          {node.description && (
            <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
              {highlightText(node.description)}
            </p>
          )}

          {/* Tech stack badges */}
          {node.techStack && node.techStack.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {node.techStack.slice(0, 4).map((tech, idx) => (
                <TechStackBadge key={idx} name={tech} size="sm" />
              ))}
              {node.techStack.length > 4 && (
                <span className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-500 rounded">
                  +{node.techStack.length - 4}
                </span>
              )}
            </div>
          )}

          {/* Features */}
          {node.features && node.features.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1">
              {node.features.slice(0, 3).map((feature, idx) => (
                <span
                  key={idx}
                  className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                >
                  {feature}
                </span>
              ))}
              {node.features.length > 3 && (
                <span className="text-xs text-gray-400">
                  +{node.features.length - 3}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Children */}
      <AnimatePresence>
        {shouldExpand && hasChildren && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            {/* Connection line */}
            <div
              className="border-l-2 border-gray-200 ml-4"
              style={{ marginLeft: `${level * 24 + 20}px` }}
            >
              {node.children!.map((child) => (
                <MindMapNodeItem
                  key={child.id}
                  node={child}
                  level={level + 1}
                  onSelect={onSelect}
                  selectedId={selectedId}
                  searchQuery={searchQuery}
                />
              ))}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * Props for MindMapView
 */
interface MindMapViewProps {
  className?: string;
  nodes?: MindMapNode[];
}

/**
 * MindMapView component
 */
export function MindMapView({ className, nodes: propNodes }: MindMapViewProps) {
  // Use individual selectors to prevent infinite re-renders
  const mindMapNodes = useVisualizationStore((state) => state.mindMapNodes);
  const selectedNodeId = useVisualizationStore((state) => state.selectedNodeId);
  const selectNode = useVisualizationStore((state) => state.selectNode);
  const searchQuery = useVisualizationStore((state) => state.searchQuery);
  const filterOptions = useVisualizationStore((state) => state.filterOptions);

  // Use prop nodes or store nodes
  const nodes = propNodes || mindMapNodes;

  // Filter nodes based on filter options
  const filteredNodes = useMemo(() => {
    if (filterOptions.types.length === 0 && filterOptions.statuses.length === 0) {
      return nodes;
    }

    const filterNode = (node: MindMapNode): MindMapNode | null => {
      // Only match types that are part of BlockType
      const isBlockType = ['analysis', 'architecture', 'stack', 'document', 'session'].includes(node.type);
      const typeMatch =
        filterOptions.types.length === 0 ||
        (isBlockType && filterOptions.types.includes(node.type as BlockType));
      const statusMatch =
        filterOptions.statuses.length === 0 ||
        filterOptions.statuses.includes(node.status);

      // Filter children recursively
      const filteredChildren = node.children
        ?.map(filterNode)
        .filter((n): n is MindMapNode => n !== null);

      // Include node if it matches or has matching children
      if ((typeMatch && statusMatch) || (filteredChildren && filteredChildren.length > 0)) {
        return {
          ...node,
          children: filteredChildren,
        };
      }

      return null;
    };

    return nodes
      .map(filterNode)
      .filter((n): n is MindMapNode => n !== null);
  }, [nodes, filterOptions]);

  // Handle node selection
  const handleSelect = useCallback(
    (nodeId: string) => {
      selectNode(nodeId);
    },
    [selectNode]
  );

  if (filteredNodes.length === 0) {
    return (
      <div className={clsx('flex items-center justify-center h-full', className)}>
        <div className="text-center text-gray-500">
          <FolderKanban className="h-12 w-12 mx-auto mb-2 text-gray-300" />
          <p className="text-sm">No blocks to display</p>
          {searchQuery && (
            <p className="text-xs mt-1">
              No results for "{searchQuery}"
            </p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className={clsx('p-4 overflow-auto', className)}>
      <div className="space-y-1">
        {filteredNodes.map((node) => (
          <MindMapNodeItem
            key={node.id}
            node={node}
            level={0}
            onSelect={handleSelect}
            selectedId={selectedNodeId}
            searchQuery={searchQuery}
          />
        ))}
      </div>
    </div>
  );
}

export default MindMapView;
