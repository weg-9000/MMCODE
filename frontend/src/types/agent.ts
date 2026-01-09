/**
 * Agent-related type definitions
 * Represents AI agents in the A2A system
 */

export type AgentRole =
  | 'orchestrator'
  | 'architect'
  | 'tech_lead'
  | 'technical_writer'
  | 'stack_recommender'
  | 'security_analyst'
  | 'documenter';

export type AgentStatus = 'active' | 'inactive' | 'maintenance' | 'error';

/**
 * Agent capability definition
 */
export interface AgentCapability {
  name: string;
  description: string;
  inputTypes: string[];
  outputTypes: string[];
}

/**
 * Agent entity
 */
export interface Agent {
  id: string;
  name: string;
  role: AgentRole;
  description?: string;
  endpoint_url?: string;
  capabilities: string[];
  status: AgentStatus;
  version: string;
  created_at: string;
  last_seen?: string;
  metadata?: AgentMetadata;
}

export interface AgentMetadata {
  framework?: string;
  specializations?: string[];
  output_formats?: string[];
  max_concurrent_tasks?: number;
  average_processing_time?: number;
}

/**
 * Agent card for A2A protocol
 */
export interface AgentCard {
  agent_id: string;
  agent_name: string;
  framework: 'langchain' | 'autogen' | 'crewai' | 'custom';
  capabilities: string[];
  endpoint_url: string;
  version: string;
  metadata?: Record<string, unknown>;
}

/**
 * A2A Task definition
 */
export interface A2ATask {
  task_id: string;
  agent_url: string;
  task_type: string;
  status: A2ATaskStatus;
  context: Record<string, unknown>;
  result?: Record<string, unknown>;
  error?: string;
  correlation_id?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export type A2ATaskStatus =
  | 'pending'
  | 'submitted'
  | 'processing'
  | 'completed'
  | 'failed'
  | 'cancelled';

/**
 * A2A Task creation request
 */
export interface A2ATaskRequest {
  agent_url: string;
  task_type: string;
  context: Record<string, unknown>;
  correlation_id?: string;
  priority?: 'high' | 'medium' | 'low';
}

/**
 * A2A Task response
 */
export interface A2ATaskResponse {
  task_id: string;
  status: A2ATaskStatus;
  agent_url: string;
  task_type: string;
  created_at: string;
  result?: Record<string, unknown>;
  error?: string;
}

/**
 * Agent health status
 */
export interface AgentHealth {
  agent_id: string;
  status: 'healthy' | 'unhealthy' | 'degraded';
  response_time_ms?: number;
  last_check: string;
  error?: string;
  details?: Record<string, unknown>;
}

/**
 * Agent system health overview
 */
export interface SystemHealth {
  overall_status: 'healthy' | 'unhealthy' | 'degraded';
  agents: Record<string, AgentHealth>;
  timestamp: string;
}

/**
 * Agent task execution result
 */
export interface TaskExecutionResult {
  task_id: string;
  status: 'success' | 'failure' | 'partial';
  result?: Record<string, unknown>;
  artifacts?: string[];
  processing_time_seconds: number;
  quality_score?: number;
  error?: string;
}

/**
 * Agent workflow step
 */
export interface WorkflowStep {
  step_id: string;
  agent_id: string;
  task_type: string;
  status: A2ATaskStatus;
  order: number;
  dependencies: string[];
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  started_at?: string;
  completed_at?: string;
}

/**
 * Agent workflow definition
 */
export interface AgentWorkflow {
  workflow_id: string;
  name: string;
  description: string;
  steps: WorkflowStep[];
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percentage: number;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}
