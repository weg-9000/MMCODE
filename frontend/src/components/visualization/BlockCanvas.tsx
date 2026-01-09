/**
 * BlockCanvas component
 * Main visualization canvas using React Flow for block-coding style display
 * Lazy loaded for initial load optimization
 */

import { useCallback, useMemo, useRef, useEffect } from 'react';
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  Panel,
  useNodesState,
  useEdgesState,
  addEdge,
  Connection,
  NodeTypes,
  ReactFlowInstance,
  MarkerType,
  BackgroundVariant,
  Node as ReactFlowNode,
  Edge as ReactFlowEdge,
} from 'reactflow';
import 'reactflow/dist/style.css';
import { clsx } from 'clsx';
import { ZoomIn, ZoomOut, Maximize2, Grid3X3, GitBranch } from 'lucide-react';
import { useVisualizationStore } from '@/stores';
import type { BlockNode, BlockType } from '@/types';

// Lazy loaded node components will be imported dynamically
import { AnalysisBlockNode } from '../blocks/AnalysisBlockNode';
import { ArchitectureBlockNode } from '../blocks/ArchitectureBlockNode';
import { StackBlockNode } from '../blocks/StackBlockNode';
import { DocumentBlockNode } from '../blocks/DocumentBlockNode';
import { SessionBlockNode } from '../blocks/SessionBlockNode';

/**
 * Custom node types mapping
 */
const nodeTypes: NodeTypes = {
  analysis: AnalysisBlockNode,
  architecture: ArchitectureBlockNode,
  stack: StackBlockNode,
  document: DocumentBlockNode,
  session: SessionBlockNode,
};

/**
 * Node colors by type for minimap
 */
const nodeColors: Record<BlockType, string> = {
  analysis: '#a855f7',      // purple-500
  architecture: '#06b6d4',  // cyan-500
  stack: '#10b981',         // emerald-500
  document: '#f59e0b',      // amber-500
  session: '#6366f1',       // indigo-500
};

/**
 * Props for BlockCanvas
 */
interface BlockCanvasProps {
  className?: string;
  onNodeClick?: (node: BlockNode) => void;
  onNodeDoubleClick?: (node: BlockNode) => void;
  readOnly?: boolean;
}

/**
 * BlockCanvas component - React Flow based visualization
 */
export function BlockCanvas({
  className,
  onNodeClick,
  onNodeDoubleClick,
  readOnly = false,
}: BlockCanvasProps) {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const reactFlowInstance = useRef<ReactFlowInstance | null>(null);

  // Get state from visualization store - use individual selectors to prevent infinite re-renders
  const storeNodes = useVisualizationStore((state) => state.nodes);
  const storeEdges = useVisualizationStore((state) => state.edges);
  const viewport = useVisualizationStore((state) => state.viewport);
  const setViewport = useVisualizationStore((state) => state.setViewport);
  const selectNode = useVisualizationStore((state) => state.selectNode);
  const filterOptions = useVisualizationStore((state) => state.filterOptions);
  const searchQuery = useVisualizationStore((state) => state.searchQuery);

  // Local React Flow state
  const [nodes, setNodes, onNodesChange] = useNodesState(storeNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(storeEdges);

  // Sync store nodes to local state
  useEffect(() => {
    setNodes(storeNodes);
  }, [storeNodes, setNodes]);

  useEffect(() => {
    setEdges(storeEdges);
  }, [storeEdges, setEdges]);

  // Filter and search nodes
  const filteredNodes = useMemo(() => {
    let result = nodes;

    // Apply type filter
    if (filterOptions.types.length > 0) {
      result = result.filter((node) =>
        filterOptions.types.includes(node.data?.type)
      );
    }

    // Apply status filter
    if (filterOptions.statuses.length > 0) {
      result = result.filter((node) =>
        filterOptions.statuses.includes(node.data?.status)
      );
    }

    // Apply search query
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      result = result.filter((node) => {
        const data = node.data;
        if (!data) return false;

        // Search in title and description
        const titleMatch = data.title?.toLowerCase().includes(query);
        const descMatch = data.description?.toLowerCase().includes(query);

        // Search in tech stack
        const techMatch = data.techStack?.some((tech: string) =>
          tech.toLowerCase().includes(query)
        );

        // Search in features
        const featureMatch = data.features?.some((feature: string) =>
          feature.toLowerCase().includes(query)
        );

        return titleMatch || descMatch || techMatch || featureMatch;
      });
    }

    return result;
  }, [nodes, filterOptions, searchQuery]);

  // Filter edges based on visible nodes
  const filteredEdges = useMemo(() => {
    const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));
    return edges.filter(
      (edge) =>
        visibleNodeIds.has(edge.source) && visibleNodeIds.has(edge.target)
    );
  }, [edges, filteredNodes]);

  // Handle connection
  const onConnect = useCallback(
    (params: Connection) => {
      if (readOnly) return;

      const newEdge: ReactFlowEdge = {
        ...params,
        id: `edge-${params.source}-${params.target}`,
        type: 'smoothstep',
        animated: true,
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#94a3b8',
        },
        style: { stroke: '#94a3b8', strokeWidth: 2 },
      } as ReactFlowEdge;

      setEdges((eds) => addEdge(newEdge, eds));
    },
    [readOnly, setEdges]
  );

  // Handle node click
  const handleNodeClick = useCallback(
    (_event: React.MouseEvent, node: ReactFlowNode) => {
      selectNode(node.id);
      onNodeClick?.(node as BlockNode);
    },
    [selectNode, onNodeClick]
  );

  // Handle node double click
  const handleNodeDoubleClick = useCallback(
    (_event: React.MouseEvent, node: ReactFlowNode) => {
      onNodeDoubleClick?.(node as BlockNode);
    },
    [onNodeDoubleClick]
  );

  // Handle viewport change
  const onMoveEnd = useCallback(
    (_event: any, viewport: { x: number; y: number; zoom: number }) => {
      setViewport(viewport);
    },
    [setViewport]
  );

  // Handle React Flow init
  const onInit = useCallback((instance: ReactFlowInstance) => {
    reactFlowInstance.current = instance;

    // Apply saved viewport if exists
    if (viewport.zoom !== 1 || viewport.x !== 0 || viewport.y !== 0) {
      instance.setViewport(viewport);
    }
  }, [viewport]);

  // Fit view to content
  const handleFitView = useCallback(() => {
    reactFlowInstance.current?.fitView({ padding: 0.2 });
  }, []);

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    reactFlowInstance.current?.zoomIn();
  }, []);

  const handleZoomOut = useCallback(() => {
    reactFlowInstance.current?.zoomOut();
  }, []);

  // Minimap node color function
  const getMinimapNodeColor = useCallback((node: ReactFlowNode) => {
    const type = node.data?.type as BlockType;
    return nodeColors[type] || '#6b7280';
  }, []);

  return (
    <div
      ref={reactFlowWrapper}
      className={clsx('w-full h-full canvas-container', className)}
    >
      <ReactFlow
        nodes={filteredNodes}
        edges={filteredEdges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={handleNodeClick}
        onNodeDoubleClick={handleNodeDoubleClick}
        onMoveEnd={onMoveEnd}
        onInit={onInit}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.1}
        maxZoom={2}
        defaultViewport={viewport}
        nodesDraggable={!readOnly}
        nodesConnectable={!readOnly}
        elementsSelectable={true}
        snapToGrid={true}
        snapGrid={[20, 20]}
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={20}
          size={1}
          color="#d1d5db"
        />

        <Controls
          showZoom={false}
          showFitView={false}
          showInteractive={false}
          className="!shadow-lg !border !border-gray-200 !rounded-lg"
        />

        <MiniMap
          nodeColor={getMinimapNodeColor}
          nodeStrokeWidth={3}
          zoomable
          pannable
          className="!shadow-lg !border !border-gray-200 !rounded-lg"
        />

        {/* Custom control panel */}
        <Panel position="top-right" className="flex gap-2">
          <button
            onClick={handleZoomIn}
            className="p-2 bg-white rounded-lg shadow-md border border-gray-200 hover:bg-gray-50 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4 text-gray-600" />
          </button>
          <button
            onClick={handleZoomOut}
            className="p-2 bg-white rounded-lg shadow-md border border-gray-200 hover:bg-gray-50 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4 text-gray-600" />
          </button>
          <button
            onClick={handleFitView}
            className="p-2 bg-white rounded-lg shadow-md border border-gray-200 hover:bg-gray-50 transition-colors"
            title="Fit View"
          >
            <Maximize2 className="h-4 w-4 text-gray-600" />
          </button>
        </Panel>

        {/* Stats panel */}
        <Panel position="bottom-left" className="bg-white/90 backdrop-blur-sm rounded-lg shadow-md border border-gray-200 px-3 py-2">
          <div className="flex items-center gap-4 text-xs text-gray-500">
            <span className="flex items-center gap-1">
              <Grid3X3 className="h-3 w-3" />
              {filteredNodes.length} blocks
            </span>
            <span className="flex items-center gap-1">
              <GitBranch className="h-3 w-3" />
              {filteredEdges.length} connections
            </span>
          </div>
        </Panel>
      </ReactFlow>
    </div>
  );
}

export default BlockCanvas;
