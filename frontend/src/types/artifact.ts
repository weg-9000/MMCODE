/**
 * Artifact-related type definitions
 * Represents generated outputs from agent workflows
 */

export type ArtifactType =
  | 'analysis_result'
  | 'architecture_design'
  | 'stack_recommendation'
  | 'documentation_suite'
  | 'openapi_specification'
  | 'erd'
  | 'readme'
  | 'deployment_guide'
  | 'technical_specification'
  | 'api_documentation';

export type ContentFormat = 'json' | 'markdown' | 'yaml' | 'mermaid' | 'plantuml' | 'html';

/**
 * Full artifact entity
 */
export interface Artifact {
  id: string;
  session_id: string;
  task_id?: string;
  artifact_type: ArtifactType;
  title: string;
  description?: string;
  content: ArtifactContent;
  content_format: ContentFormat;
  file_path?: string;
  quality_score?: number;
  confidence_score?: number;
  version: string;
  created_by?: string;
  created_at: string;
  updated_at: string;
  is_final: boolean;
  is_public: boolean;
}

/**
 * Artifact content union type
 */
export type ArtifactContent =
  | AnalysisContent
  | ArchitectureContent
  | StackContent
  | DocumentationContent
  | Record<string, unknown>;

/**
 * Analysis result content structure
 */
export interface AnalysisContent {
  entities: string[];
  use_cases: string[];
  constraints: string[];
  functional_requirements?: FunctionalRequirement[];
  non_functional_requirements?: NonFunctionalRequirement[];
  domain_concepts?: DomainConcept[];
  quality_score: number;
  confidence: number;
  metadata?: Record<string, unknown>;
}

export interface FunctionalRequirement {
  id: string;
  title: string;
  description: string;
  priority: 'high' | 'medium' | 'low';
  category?: string;
}

export interface NonFunctionalRequirement {
  id: string;
  title: string;
  description: string;
  category: 'performance' | 'security' | 'scalability' | 'reliability' | 'usability';
  metric?: string;
  target?: string;
}

export interface DomainConcept {
  name: string;
  description: string;
  attributes?: string[];
  relationships?: string[];
}

/**
 * Architecture design content structure
 */
export interface ArchitectureContent {
  architecture: ArchitectureDesign;
  patterns: ArchitecturePattern[];
  components: ComponentModel[];
  diagrams: Record<string, string>;
  decisions: ArchitectureDecisionRecord[];
  metadata?: ArchitectureMetadata;
}

export interface ArchitectureDesign {
  name: string;
  description: string;
  architecture_style: string;
  layers: ArchitectureLayer[];
  complexity_level: 'low' | 'medium' | 'high';
  scalability_tier: 'single' | 'multi' | 'distributed';
  data_tier?: string;
}

export interface ArchitectureLayer {
  name: string;
  description: string;
  components: string[];
  technologies?: string[];
}

export interface ArchitecturePattern {
  name: string;
  category: string;
  description: string;
  context: string;
  benefits: string[];
  trade_offs: string[];
  implementation_notes?: string;
}

export interface ComponentModel {
  name: string;
  type: 'service' | 'module' | 'library' | 'external';
  description: string;
  responsibilities: string[];
  interfaces: string[];
  dependencies: string[];
  technologies?: string[];
}

export interface ArchitectureDecisionRecord {
  id: string;
  title: string;
  status: 'proposed' | 'accepted' | 'deprecated' | 'superseded';
  context: string;
  decision: string;
  rationale: string;
  consequences: string;
}

export interface ArchitectureMetadata {
  design_timestamp: string;
  complexity_level: string;
  scalability_tier: string;
  pattern_count: number;
  component_count: number;
}

/**
 * Stack recommendation content structure
 */
export interface StackContent {
  recommendation: StackRecommendation;
  quality_assessment: QualityAssessment;
  architecture_context: Record<string, unknown>;
  implementation_guidance: ImplementationGuidance;
  metadata?: StackMetadata;
}

export interface StackRecommendation {
  backend: TechnologyChoice[];
  frontend?: TechnologyChoice[];
  database: TechnologyChoice[];
  infrastructure?: TechnologyChoice[];
  ai_ml?: TechnologyChoice[];
  devops?: TechnologyChoice[];
  monitoring?: TechnologyChoice[];
}

export interface TechnologyChoice {
  name: string;
  version?: string;
  category: string;
  description: string;
  rationale: string;
  alternatives?: string[];
  compatibility_score?: number;
}

export interface QualityAssessment {
  overall_score: number;
  suitability: number;
  completeness: number;
  feasibility: number;
  maintainability?: number;
  security?: number;
}

export interface ImplementationGuidance {
  rationale: string;
  implementation_notes: string[];
  next_steps: string[];
  risks?: string[];
  prerequisites?: string[];
}

export interface StackMetadata {
  analysis_timestamp: string;
  agent_version: string;
  complexity_assessment: string;
  confidence_level: number;
}

/**
 * Documentation content structure
 */
export interface DocumentationContent {
  documentation_suite: DocumentationSuite;
  quality_assessment: Record<string, number>;
  generation_summary: GenerationSummary;
}

export interface DocumentationSuite {
  suite_id: string;
  name: string;
  description: string;
  documents: GeneratedDocument[];
  suite_quality_score: number;
  coverage_matrix: Record<string, boolean>;
}

export interface GeneratedDocument {
  id: string;
  document_type: string;
  title: string;
  format: ContentFormat;
  content: string | Record<string, unknown>;
  quality_score: number;
  sections?: DocumentSection[];
}

export interface DocumentSection {
  id: string;
  title: string;
  content: string;
  order: number;
}

export interface GenerationSummary {
  total_documents: number;
  document_types: string[];
  overall_quality: number;
  coverage_matrix: Record<string, boolean>;
  generation_time: string;
}
