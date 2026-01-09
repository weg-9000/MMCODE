/**
 * Type definitions index
 * Re-exports all types for convenient importing
 */

// Session types
export type {
  SessionStatus,
  TaskStatus,
  Priority,
  Session,
  SessionCreate,
  SessionUpdate,
  TaskSummary,
  Task,
  ArtifactSummary,
  RequirementAnalysisRequest,
  AnalysisResponse,
  OrchestrationRequest,
  OrchestrationResponse,
  WorkflowStatus,
} from './session';

// Artifact types
export type {
  ArtifactType,
  ContentFormat,
  Artifact,
  ArtifactContent,
  AnalysisContent,
  FunctionalRequirement,
  NonFunctionalRequirement,
  DomainConcept,
  ArchitectureContent,
  ArchitectureDesign,
  ArchitectureLayer,
  ArchitecturePattern,
  ComponentModel,
  ArchitectureDecisionRecord,
  ArchitectureMetadata,
  StackContent,
  StackRecommendation,
  TechnologyChoice,
  QualityAssessment,
  ImplementationGuidance,
  StackMetadata,
  DocumentationContent,
  DocumentationSuite,
  GeneratedDocument,
  DocumentSection,
  GenerationSummary,
} from './artifact';

// Block types
export type {
  BlockType,
  BlockStatus,
  BlockNodeData,
  BlockSummary,
  AnalysisBlockSummary,
  ArchitectureBlockSummary,
  StackBlockSummary,
  DocumentBlockSummary,
  SessionBlockSummary,
  BlockMetadata,
  BlockNode,
  BlockEdge,
  BlockConnection,
  MindMapNode,
  BlockFilterOptions,
  LayoutConfig,
  BlockActions,
  CanvasViewport,
  BlockCanvasState,
} from './block';

export { DEFAULT_FILTER_OPTIONS, DEFAULT_LAYOUT_CONFIG } from './block';

// Agent types
export type {
  AgentRole,
  AgentStatus,
  AgentCapability,
  Agent,
  AgentMetadata,
  AgentCard,
  A2ATask,
  A2ATaskStatus,
  A2ATaskRequest,
  A2ATaskResponse,
  AgentHealth,
  SystemHealth,
  TaskExecutionResult,
  WorkflowStep,
  AgentWorkflow,
} from './agent';

/**
 * Common utility types
 */
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P];
};

export type Nullable<T> = T | null;

export type AsyncState<T> = {
  data: T | null;
  isLoading: boolean;
  error: Error | null;
};

/**
 * API Response wrapper type
 */
export interface ApiResponse<T> {
  data: T;
  message?: string;
  status: 'success' | 'error';
  timestamp: string;
}

/**
 * Pagination parameters
 */
export interface PaginationParams {
  page: number;
  limit: number;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

/**
 * Paginated response
 */
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}
