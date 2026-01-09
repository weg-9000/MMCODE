/**
 * Visualization store
 * State management for block canvas and mind map visualization
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  BlockNode,
  BlockEdge,
  BlockFilterOptions,
  LayoutConfig,
  CanvasViewport,
  BlockType,
  BlockStatus,
  MindMapNode,
} from '@/types';
import { DEFAULT_FILTER_OPTIONS, DEFAULT_LAYOUT_CONFIG } from '@/types';

/**
 * View mode for visualization
 */
export type ViewMode = 'block' | 'mindmap' | 'list';

/**
 * Visualization store state
 */
export interface VisualizationState {
  // View mode
  viewMode: ViewMode;

  // Block canvas state
  nodes: BlockNode[];
  edges: BlockEdge[];
  selectedNodeId: string | null;
  hoveredNodeId: string | null;

  // Mind map state
  mindMapRoot: MindMapNode | null;
  mindMapNodes: MindMapNode[];
  expandedNodeIds: Set<string>;

  // Viewport
  viewport: CanvasViewport;

  // Filtering and search
  filterOptions: BlockFilterOptions;
  searchQuery: string;
  searchResults: string[]; // Node IDs matching search

  // Layout
  layoutConfig: LayoutConfig;

  // Detail panel
  showDetailPanel: boolean;
  detailPanelNodeId: string | null;

  // Actions - View mode
  setViewMode: (mode: ViewMode) => void;

  // Actions - Nodes and edges
  setNodes: (nodes: BlockNode[]) => void;
  setEdges: (edges: BlockEdge[]) => void;
  addNode: (node: BlockNode) => void;
  updateNode: (nodeId: string, updates: Partial<BlockNode>) => void;
  removeNode: (nodeId: string) => void;

  // Actions - Selection
  selectNode: (nodeId: string | null) => void;
  setHoveredNode: (nodeId: string | null) => void;

  // Actions - Mind map
  setMindMapRoot: (root: MindMapNode | null) => void;
  toggleNodeExpanded: (nodeId: string) => void;
  expandNode: (nodeId: string) => void;
  collapseNode: (nodeId: string) => void;
  expandAll: () => void;
  collapseAll: () => void;

  // Actions - Viewport
  setViewport: (viewport: CanvasViewport) => void;
  resetViewport: () => void;
  zoomIn: () => void;
  zoomOut: () => void;
  fitView: () => void;

  // Actions - Filtering
  setFilterOptions: (options: Partial<BlockFilterOptions>) => void;
  setSearchQuery: (query: string) => void;
  clearFilters: () => void;
  toggleTypeFilter: (type: BlockType) => void;
  toggleStatusFilter: (status: BlockStatus) => void;

  // Actions - Layout
  setLayoutConfig: (config: Partial<LayoutConfig>) => void;
  toggleAutoLayout: () => void;

  // Actions - Detail panel
  setShowDetailPanel: (show: boolean) => void;
  openDetailPanel: (nodeId: string) => void;
  closeDetailPanel: () => void;
  toggleDetailPanel: () => void;

  // Actions - Filters
  resetFilters: () => void;

  // Actions - Reset
  resetVisualization: () => void;
}

/**
 * Default viewport
 */
const DEFAULT_VIEWPORT: CanvasViewport = {
  x: 0,
  y: 0,
  zoom: 1,
};

/**
 * Collect all node IDs from mind map tree
 */
function collectAllNodeIds(node: MindMapNode): string[] {
  const ids = [node.id];
  if (node.children) {
    for (const child of node.children) {
      ids.push(...collectAllNodeIds(child));
    }
  }
  return ids;
}

/**
 * Visualization store
 */
export const useVisualizationStore = create<VisualizationState>()(
  devtools(
    (set, get) => ({
      // Initial state
      viewMode: 'block',
      nodes: [],
      edges: [],
      selectedNodeId: null,
      hoveredNodeId: null,
      mindMapRoot: null,
      mindMapNodes: [],
      expandedNodeIds: new Set(),
      viewport: DEFAULT_VIEWPORT,
      filterOptions: DEFAULT_FILTER_OPTIONS,
      searchQuery: '',
      searchResults: [],
      layoutConfig: DEFAULT_LAYOUT_CONFIG,
      showDetailPanel: false,
      detailPanelNodeId: null,

      // View mode
      setViewMode: (mode) => set({ viewMode: mode }),

      // Nodes and edges
      setNodes: (nodes) => set({ nodes }),
      setEdges: (edges) => set({ edges }),

      addNode: (node) =>
        set((state) => ({
          nodes: [...state.nodes, node],
        })),

      updateNode: (nodeId, updates) =>
        set((state) => ({
          nodes: state.nodes.map((n) =>
            n.id === nodeId ? { ...n, ...updates } : n
          ),
        })),

      removeNode: (nodeId) =>
        set((state) => ({
          nodes: state.nodes.filter((n) => n.id !== nodeId),
          edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
          selectedNodeId: state.selectedNodeId === nodeId ? null : state.selectedNodeId,
        })),

      // Selection
      selectNode: (nodeId) =>
        set({
          selectedNodeId: nodeId,
          showDetailPanel: nodeId !== null,
          detailPanelNodeId: nodeId,
        }),

      setHoveredNode: (nodeId) => set({ hoveredNodeId: nodeId }),

      // Mind map
      setMindMapRoot: (root) => set({ mindMapRoot: root }),

      toggleNodeExpanded: (nodeId) =>
        set((state) => {
          const newExpanded = new Set(state.expandedNodeIds);
          if (newExpanded.has(nodeId)) {
            newExpanded.delete(nodeId);
          } else {
            newExpanded.add(nodeId);
          }
          return { expandedNodeIds: newExpanded };
        }),

      expandNode: (nodeId) =>
        set((state) => ({
          expandedNodeIds: new Set([...state.expandedNodeIds, nodeId]),
        })),

      collapseNode: (nodeId) =>
        set((state) => {
          const newExpanded = new Set(state.expandedNodeIds);
          newExpanded.delete(nodeId);
          return { expandedNodeIds: newExpanded };
        }),

      expandAll: () =>
        set((state) => {
          if (!state.mindMapRoot) return {};
          const allIds = collectAllNodeIds(state.mindMapRoot);
          return { expandedNodeIds: new Set(allIds) };
        }),

      collapseAll: () => set({ expandedNodeIds: new Set() }),

      // Viewport
      setViewport: (viewport) => set({ viewport }),
      resetViewport: () => set({ viewport: DEFAULT_VIEWPORT }),

      zoomIn: () =>
        set((state) => ({
          viewport: { ...state.viewport, zoom: Math.min(state.viewport.zoom * 1.2, 2) },
        })),

      zoomOut: () =>
        set((state) => ({
          viewport: { ...state.viewport, zoom: Math.max(state.viewport.zoom / 1.2, 0.25) },
        })),

      fitView: () => {
        // This will be handled by React Flow's fitView
        set({ viewport: DEFAULT_VIEWPORT });
      },

      // Filtering
      setFilterOptions: (options) =>
        set((state) => ({
          filterOptions: { ...state.filterOptions, ...options },
        })),

      setSearchQuery: (query) => {
        const state = get();
        const lowerQuery = query.toLowerCase();

        // Find matching nodes
        const searchResults = query
          ? state.nodes
              .filter((n) => {
                const data = n.data;
                return (
                  data.title.toLowerCase().includes(lowerQuery) ||
                  (data.techStack?.some((t) => t.toLowerCase().includes(lowerQuery)) ?? false)
                );
              })
              .map((n) => n.id)
          : [];

        set({ searchQuery: query, searchResults });
      },

      clearFilters: () =>
        set({
          filterOptions: DEFAULT_FILTER_OPTIONS,
          searchQuery: '',
          searchResults: [],
        }),

      toggleTypeFilter: (type) =>
        set((state) => {
          const types = state.filterOptions.types.includes(type)
            ? state.filterOptions.types.filter((t) => t !== type)
            : [...state.filterOptions.types, type];
          return {
            filterOptions: { ...state.filterOptions, types },
          };
        }),

      toggleStatusFilter: (status) =>
        set((state) => {
          const statuses = state.filterOptions.statuses.includes(status)
            ? state.filterOptions.statuses.filter((s) => s !== status)
            : [...state.filterOptions.statuses, status];
          return {
            filterOptions: { ...state.filterOptions, statuses },
          };
        }),

      // Layout
      setLayoutConfig: (config) =>
        set((state) => ({
          layoutConfig: { ...state.layoutConfig, ...config },
        })),

      toggleAutoLayout: () =>
        set((state) => ({
          layoutConfig: { ...state.layoutConfig, autoLayout: !state.layoutConfig.autoLayout },
        })),

      // Detail panel
      setShowDetailPanel: (show) => set({ showDetailPanel: show }),

      openDetailPanel: (nodeId) =>
        set({
          showDetailPanel: true,
          detailPanelNodeId: nodeId,
          selectedNodeId: nodeId,
        }),

      closeDetailPanel: () =>
        set({
          showDetailPanel: false,
          detailPanelNodeId: null,
        }),

      toggleDetailPanel: () =>
        set((state) => ({
          showDetailPanel: !state.showDetailPanel,
        })),

      resetFilters: () =>
        set({
          filterOptions: DEFAULT_FILTER_OPTIONS,
          searchQuery: '',
          searchResults: [],
        }),

      // Reset
      resetVisualization: () =>
        set({
          nodes: [],
          edges: [],
          selectedNodeId: null,
          hoveredNodeId: null,
          mindMapRoot: null,
          mindMapNodes: [],
          expandedNodeIds: new Set(),
          viewport: DEFAULT_VIEWPORT,
          filterOptions: DEFAULT_FILTER_OPTIONS,
          searchQuery: '',
          searchResults: [],
          showDetailPanel: false,
          detailPanelNodeId: null,
        }),
    }),
    { name: 'VisualizationStore' }
  )
);

/**
 * Selectors
 */
export const selectFilteredNodes = (state: VisualizationState) => {
  const { nodes, filterOptions, searchResults, searchQuery } = state;

  return nodes.filter((node) => {
    const data = node.data;

    // Type filter
    if (!filterOptions.types.includes(data.type)) {
      return false;
    }

    // Status filter
    if (!filterOptions.statuses.includes(data.status)) {
      return false;
    }

    // Quality score filter
    if (
      filterOptions.minQualityScore !== undefined &&
      data.qualityScore !== undefined &&
      data.qualityScore < filterOptions.minQualityScore
    ) {
      return false;
    }

    // Search filter
    if (searchQuery && searchResults.length > 0) {
      return searchResults.includes(node.id);
    }

    return true;
  });
};

export const selectSelectedNode = (state: VisualizationState) =>
  state.nodes.find((n) => n.id === state.selectedNodeId);

export default useVisualizationStore;
