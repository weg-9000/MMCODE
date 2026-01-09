/**
 * Block visualization type definitions
 * Used for ERD-like and mind-map style visualizations
 */

import type { Node, Edge } from 'reactflow';

export type BlockType = 'analysis' | 'architecture' | 'stack' | 'document' | 'session';
export type BlockStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * Base block node data interface
 */
export interface BaseBlockData {
  id: string;
  type: BlockType;
  title: string;
  status: BlockStatus;
  qualityScore?: number;
  description?: string;
  techStack?: string[];
  features?: string[];
}

/**
 * Analysis block specific data
 */
export interface AnalysisBlockData extends BaseBlockData {
  type: 'analysis';
  functionalRequirements?: Array<string | { id?: string; name: string; description?: string }>;
  nonFunctionalRequirements?: Array<string | { category: string; description?: string }>;
  domainConcepts?: Array<string | { name: string; description?: string }>;
  stakeholders?: string[];
  useCases?: string[];
  constraints?: string[];
}

/**
 * Architecture block specific data
 */
export interface ArchitectureBlockData extends BaseBlockData {
  type: 'architecture';
  patterns?: Array<string | { name: string; description?: string; benefits?: string; trade_offs?: string }>;
  layers?: Array<string | { name: string; responsibilities?: string[] }>;
  components?: Array<string | { name: string; description?: string; dependencies?: string[] }>;
  decisions?: Array<string | { id: string; title: string; status?: string }>;
  architectureStyle?: string;
  scalability?: string;
}

/**
 * Stack block specific data
 */
export interface StackBlockData extends BaseBlockData {
  type: 'stack';
  frontend?: Array<string | { name: string; category?: string; reason?: string }>;
  backend?: Array<string | { name: string; category?: string; reason?: string }>;
  database?: Array<string | { name: string; category?: string; reason?: string }>;
  infrastructure?: Array<string | { name: string; category?: string; reason?: string }>;
  reasoning?: Array<string | { category: string; reason: string }>;
  suitabilityScore?: number;
  feasibilityScore?: number;
}

/**
 * Document block specific data
 */
export interface DocumentBlockData extends BaseBlockData {
  type: 'document';
  documentTypes?: Array<string | { name: string; format?: string }>;
  sections?: Array<string | { title: string; content?: string }>;
  formats?: string[];
  totalPages?: number;
  coveragePercentage?: number;
}

/**
 * Session block specific data
 */
export interface SessionBlockData extends BaseBlockData {
  type: 'session';
  taskCount?: number;
  completedTasks?: number;
  artifactCount?: number;
  createdAt?: string;
  updatedAt?: string;
  overallProgress?: number;
}

/**
 * Union type for all block data
 */
export type BlockNodeData =
  | AnalysisBlockData
  | ArchitectureBlockData
  | StackBlockData
  | DocumentBlockData
  | SessionBlockData;

/**
 * Summary types for backwards compatibility
 */
export type AnalysisBlockSummary = Omit<AnalysisBlockData, 'type'>;
export type ArchitectureBlockSummary = Omit<ArchitectureBlockData, 'type'>;
export type StackBlockSummary = Omit<StackBlockData, 'type'>;
export type DocumentBlockSummary = Omit<DocumentBlockData, 'type'>;
export type SessionBlockSummary = Omit<SessionBlockData, 'type'>;

export type BlockSummary =
  | AnalysisBlockSummary
  | ArchitectureBlockSummary
  | StackBlockSummary
  | DocumentBlockSummary
  | SessionBlockSummary;

export interface BlockMetadata {
  processingTime?: number;
  createdAt: string;
  updatedAt?: string;
  agentId?: string;
}

/**
 * React Flow node type for blocks
 */
export type BlockNode = Node<BlockNodeData>;

/**
 * React Flow edge type for blocks
 */
export type BlockEdge = Edge<{
  label?: string;
  animated?: boolean;
  type?: 'default' | 'data-flow' | 'dependency';
}>;

/**
 * Block connection definition
 */
export interface BlockConnection {
  sourceId: string;
  targetId: string;
  type: 'flow' | 'dependency' | 'reference';
  label?: string;
}

/**
 * Mind map node for hierarchical visualization
 */
export interface MindMapNode {
  id: string;
  parentId?: string;
  type: BlockType | 'entity' | 'use-case' | 'pattern' | 'component' | 'technology' | 'document';
  label: string;
  description?: string;
  techStack?: string[];
  features?: string[];
  status: BlockStatus;
  qualityScore?: number;
  expanded?: boolean;
  children?: MindMapNode[];
  metadata?: Record<string, unknown>;
}

/**
 * Filter options for block visualization
 */
export interface BlockFilterOptions {
  types: BlockType[];
  statuses: BlockStatus[];
  searchQuery?: string;
  showCompleted?: boolean;
  showPending?: boolean;
  showFailed?: boolean;
  minQualityScore?: number;
}

/**
 * Default filter options
 */
export const DEFAULT_FILTER_OPTIONS: BlockFilterOptions = {
  types: [],
  statuses: [],
  searchQuery: '',
  showCompleted: true,
  showPending: true,
  showFailed: true,
};

/**
 * Layout configuration for block canvas
 */
export interface LayoutConfig {
  direction: 'horizontal' | 'vertical';
  spacing: {
    horizontal: number;
    vertical: number;
  };
  nodeWidth: number;
  nodeHeight: number;
  autoLayout: boolean;
}

/**
 * Default layout configuration
 */
export const DEFAULT_LAYOUT_CONFIG: LayoutConfig = {
  direction: 'horizontal',
  spacing: {
    horizontal: 200,
    vertical: 100,
  },
  nodeWidth: 280,
  nodeHeight: 160,
  autoLayout: true,
};

/**
 * Block interaction actions
 */
export interface BlockActions {
  onExpand: (nodeId: string) => void;
  onCollapse: (nodeId: string) => void;
  onSelect: (nodeId: string) => void;
  onViewDetails: (nodeId: string) => void;
  onExport: (nodeId: string, format: 'json' | 'md' | 'yaml') => void;
}

/**
 * Canvas viewport state
 */
export interface CanvasViewport {
  x: number;
  y: number;
  zoom: number;
}

/**
 * Block canvas state
 */
export interface BlockCanvasState {
  nodes: BlockNode[];
  edges: BlockEdge[];
  selectedNodeId?: string;
  viewport: CanvasViewport;
  filterOptions: BlockFilterOptions;
  layoutConfig: LayoutConfig;
}
