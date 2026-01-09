/**
 * Session-related type definitions
 * Mirrors backend schemas for type safety
 */

export type SessionStatus = 'active' | 'completed' | 'archived';
export type TaskStatus = 'pending' | 'processing' | 'completed' | 'failed';
export type Priority = 'high' | 'medium' | 'low';

/**
 * Session entity representing a requirement analysis workflow
 */
export interface Session {
  id: string;
  title: string;
  description?: string;
  requirements_text?: string;
  status: SessionStatus;
  created_at: string;
  updated_at: string;
  tasks?: TaskSummary[];
  artifacts?: ArtifactSummary[];
}

/**
 * Create session request payload
 */
export interface SessionCreate {
  title: string;
  description?: string;
  requirements_text?: string;
}

/**
 * Update session request payload
 */
export interface SessionUpdate {
  title?: string;
  description?: string;
  requirements_text?: string;
  status?: SessionStatus;
}

/**
 * Task summary for session responses
 */
export interface TaskSummary {
  id: string;
  task_type: string;
  agent_id: string;
  status: TaskStatus;
  priority: Priority;
  created_at: string;
  quality_score?: number;
}

/**
 * Full task response
 */
export interface Task extends TaskSummary {
  session_id: string;
  input_data?: Record<string, unknown>;
  output_data?: Record<string, unknown>;
  error_message?: string;
  started_at?: string;
  completed_at?: string;
  processing_time?: number;
  confidence_score?: number;
}

/**
 * Artifact summary for session responses
 */
export interface ArtifactSummary {
  id: string;
  artifact_type: string;
  title: string;
  quality_score?: number;
  created_at: string;
  is_final: boolean;
}

/**
 * Requirement analysis request
 */
export interface RequirementAnalysisRequest {
  requirements: string;
  preferences?: Record<string, unknown>;
}

/**
 * Analysis response
 */
export interface AnalysisResponse {
  session_id: string;
  task_id: string;
  status: string;
  message?: string;
  analysis_result?: Record<string, unknown>;
  error?: string;
  processing_time?: number;
  quality_score?: number;
}

/**
 * Orchestration request for full agent workflow
 */
export interface OrchestrationRequest {
  requirements: string;
  session_title?: string;
  description?: string;
  preferences?: Record<string, unknown>;
}

/**
 * Orchestration response
 */
export interface OrchestrationResponse {
  session_id: string;
  status: string;
  message?: string;
  progress_percentage?: number;
  estimated_completion_minutes?: number;
  tasks: TaskSummary[];
  artifacts: ArtifactSummary[];
  total_processing_time?: number;
  overall_quality_score?: number;
}

/**
 * Workflow status types
 */
export type WorkflowStatus = 'started' | 'in_progress' | 'completed' | 'failed' | 'cancelled';
