/**
 * DocumentViewer page
 * Displays and allows navigation of generated artifacts
 */

import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  FileText,
  Database,
  Code,
  BookOpen,
  Download,
  Copy,
  Check,
  ChevronLeft,
  ChevronRight,
  AlertCircle,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useUIStore } from '@/stores';
import { ERDViewer, MarkdownViewer } from '@/components/viewers';
import { QualityScore } from '@/components/shared';
import { isMockMode, mockArtifacts } from '@/mocks';
import { orchestrationService } from '@/services/orchestrationService';
import type { Artifact, ArtifactType, DocumentationContent, AnalysisContent, ArchitectureContent, StackContent, TechnologyChoice } from '@/types';

/**
 * Artifact type icons and labels
 */
const artifactTypeConfig: Record<ArtifactType, { icon: React.ElementType; label: string; color: string }> = {
  analysis_result: { icon: FileText, label: 'Analysis Result', color: 'text-purple-500' },
  architecture_design: { icon: Database, label: 'Architecture Design', color: 'text-cyan-500' },
  stack_recommendation: { icon: Code, label: 'Stack Recommendation', color: 'text-emerald-500' },
  documentation_suite: { icon: BookOpen, label: 'Documentation Suite', color: 'text-amber-500' },
  openapi_specification: { icon: Code, label: 'OpenAPI Spec', color: 'text-blue-500' },
  erd: { icon: Database, label: 'ERD', color: 'text-indigo-500' },
  readme: { icon: BookOpen, label: 'README', color: 'text-green-500' },
  deployment_guide: { icon: FileText, label: 'Deployment Guide', color: 'text-orange-500' },
  technical_specification: { icon: FileText, label: 'Technical Spec', color: 'text-gray-500' },
  api_documentation: { icon: Code, label: 'API Docs', color: 'text-pink-500' },
};

/**
 * Artifact card component
 */
function ArtifactCard({
  artifact,
  isSelected,
  onClick,
}: {
  artifact: Artifact;
  isSelected: boolean;
  onClick: () => void;
}) {
  const config = artifactTypeConfig[artifact.artifact_type] || artifactTypeConfig.analysis_result;
  const Icon = config.icon;

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left p-3 rounded-lg border transition-all',
        isSelected
          ? 'border-primary-500 bg-primary-50 shadow-sm'
          : 'border-gray-200 bg-white hover:border-gray-300 hover:shadow-sm'
      )}
    >
      <div className="flex items-start gap-3">
        <div className={clsx('p-2 rounded-lg bg-gray-50', config.color)}>
          <Icon className="h-4 w-4" />
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-gray-900 truncate">{artifact.title}</h4>
          <p className="text-xs text-gray-500 mt-0.5">{config.label}</p>
          {artifact.quality_score && (
            <div className="mt-2">
              <QualityScore score={artifact.quality_score} size="sm" />
            </div>
          )}
        </div>
      </div>
    </button>
  );
}

/**
 * Content renderer based on artifact type
 */
function ArtifactContent({ artifact }: { artifact: Artifact }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    const content = typeof artifact.content === 'string'
      ? artifact.content
      : JSON.stringify(artifact.content, null, 2);
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const content = typeof artifact.content === 'string'
      ? artifact.content
      : JSON.stringify(artifact.content, null, 2);
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${artifact.title.toLowerCase().replace(/\s+/g, '-')}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  // Render based on artifact type
  const renderContent = () => {
    switch (artifact.artifact_type) {
      case 'documentation_suite': {
        const docContent = artifact.content as DocumentationContent;
        return (
          <div className="space-y-6">
            {docContent.documentation_suite.documents.map((doc) => (
              <div key={doc.id} className="border border-gray-200 rounded-lg overflow-hidden">
                <div className="px-4 py-3 bg-gray-50 border-b border-gray-200">
                  <h4 className="font-medium text-gray-900">{doc.title}</h4>
                  <p className="text-xs text-gray-500 mt-0.5">{doc.document_type} • {doc.format}</p>
                </div>
                <div className="p-4">
                  {doc.format === 'markdown' && typeof doc.content === 'string' && (
                    <MarkdownViewer content={doc.content} />
                  )}
                  {doc.format === 'mermaid' && typeof doc.content === 'string' && (
                    <ERDViewer
                      data={{ entities: [], relationships: [] }}
                      mermaidCode={doc.content}
                    />
                  )}
                  {doc.format === 'json' && (
                    <pre className="p-4 bg-gray-900 text-gray-100 text-xs rounded overflow-auto max-h-96">
                      {JSON.stringify(doc.content, null, 2)}
                    </pre>
                  )}
                </div>
              </div>
            ))}
          </div>
        );
      }

      case 'analysis_result': {
        const analysisContent = artifact.content as AnalysisContent;
        return (
          <div className="space-y-6">
            {/* Entities */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Entities ({analysisContent.entities.length})</h3>
              <div className="flex flex-wrap gap-2">
                {analysisContent.entities.map((entity) => (
                  <span key={entity} className="px-3 py-1 bg-purple-100 text-purple-700 rounded-full text-sm">
                    {entity}
                  </span>
                ))}
              </div>
            </section>

            {/* Use Cases */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Use Cases ({analysisContent.use_cases.length})</h3>
              <ul className="space-y-2">
                {analysisContent.use_cases.map((useCase, idx) => (
                  <li key={idx} className="flex items-center gap-2 text-sm text-gray-700">
                    <span className="w-6 h-6 flex items-center justify-center bg-blue-100 text-blue-700 rounded-full text-xs font-medium">
                      {idx + 1}
                    </span>
                    {useCase}
                  </li>
                ))}
              </ul>
            </section>

            {/* Constraints */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Constraints ({analysisContent.constraints.length})</h3>
              <ul className="space-y-2">
                {analysisContent.constraints.map((constraint, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                    <AlertCircle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
                    {constraint}
                  </li>
                ))}
              </ul>
            </section>

            {/* Functional Requirements */}
            {analysisContent.functional_requirements && (
              <section>
                <h3 className="text-sm font-semibold text-gray-900 mb-3">Functional Requirements</h3>
                <div className="space-y-3">
                  {analysisContent.functional_requirements.map((req) => (
                    <div key={req.id} className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-mono text-gray-500">{req.id}</span>
                        <span className={clsx(
                          'px-2 py-0.5 text-xs rounded',
                          req.priority === 'high' ? 'bg-red-100 text-red-700' :
                          req.priority === 'medium' ? 'bg-amber-100 text-amber-700' :
                          'bg-gray-100 text-gray-700'
                        )}>
                          {req.priority}
                        </span>
                      </div>
                      <h4 className="font-medium text-gray-900">{req.title}</h4>
                      <p className="text-sm text-gray-600 mt-1">{req.description}</p>
                    </div>
                  ))}
                </div>
              </section>
            )}
          </div>
        );
      }

      case 'architecture_design': {
        const archContent = artifact.content as ArchitectureContent;
        return (
          <div className="space-y-6">
            {/* Architecture Overview */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Architecture Overview</h3>
              <div className="p-4 bg-gray-50 rounded-lg">
                <h4 className="font-medium text-gray-900">{archContent.architecture.name}</h4>
                <p className="text-sm text-gray-600 mt-1">{archContent.architecture.description}</p>
                <div className="flex gap-4 mt-3">
                  <span className="text-xs px-2 py-1 bg-cyan-100 text-cyan-700 rounded">
                    {archContent.architecture.architecture_style}
                  </span>
                  <span className="text-xs px-2 py-1 bg-blue-100 text-blue-700 rounded">
                    {archContent.architecture.complexity_level} complexity
                  </span>
                  <span className="text-xs px-2 py-1 bg-purple-100 text-purple-700 rounded">
                    {archContent.architecture.scalability_tier} tier
                  </span>
                </div>
              </div>
            </section>

            {/* Patterns */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Patterns ({archContent.patterns.length})</h3>
              <div className="grid gap-3">
                {archContent.patterns.map((pattern) => (
                  <div key={pattern.name} className="p-3 border border-gray-200 rounded-lg">
                    <div className="flex items-center gap-2 mb-1">
                      <h4 className="font-medium text-gray-900">{pattern.name}</h4>
                      <span className="text-xs px-2 py-0.5 bg-gray-100 text-gray-600 rounded">
                        {pattern.category}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600">{pattern.description}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Components */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Components ({archContent.components.length})</h3>
              <div className="grid gap-3">
                {archContent.components.map((comp) => (
                  <div key={comp.name} className="p-3 border border-gray-200 rounded-lg">
                    <h4 className="font-medium text-gray-900">{comp.name}</h4>
                    <p className="text-sm text-gray-600 mt-1">{comp.description}</p>
                    {comp.technologies && (
                      <div className="flex gap-1 mt-2">
                        {comp.technologies.map((tech) => (
                          <span key={tech} className="text-xs px-2 py-0.5 bg-emerald-100 text-emerald-700 rounded">
                            {tech}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </section>

            {/* ADRs */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Architecture Decision Records ({archContent.decisions.length})</h3>
              <div className="space-y-3">
                {archContent.decisions.map((adr) => (
                  <details key={adr.id} className="border border-gray-200 rounded-lg">
                    <summary className="p-3 cursor-pointer hover:bg-gray-50">
                      <div className="inline-flex items-center gap-2">
                        <span className="text-xs font-mono text-gray-500">{adr.id}</span>
                        <span className="font-medium text-gray-900">{adr.title}</span>
                        <span className={clsx(
                          'text-xs px-2 py-0.5 rounded',
                          adr.status === 'accepted' ? 'bg-green-100 text-green-700' :
                          adr.status === 'proposed' ? 'bg-blue-100 text-blue-700' :
                          'bg-gray-100 text-gray-700'
                        )}>
                          {adr.status}
                        </span>
                      </div>
                    </summary>
                    <div className="p-3 border-t border-gray-200 bg-gray-50 text-sm space-y-2">
                      <div><strong>Context:</strong> {adr.context}</div>
                      <div><strong>Decision:</strong> {adr.decision}</div>
                      <div><strong>Rationale:</strong> {adr.rationale}</div>
                      <div><strong>Consequences:</strong> {adr.consequences}</div>
                    </div>
                  </details>
                ))}
              </div>
            </section>
          </div>
        );
      }

      case 'stack_recommendation': {
        const stackContent = artifact.content as StackContent;
        const categories = Object.entries(stackContent.recommendation)
          .filter((entry): entry is [string, TechnologyChoice[]] => entry[1] !== undefined && entry[1].length > 0);

        return (
          <div className="space-y-6">
            {/* Quality Assessment */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Quality Assessment</h3>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                {Object.entries(stackContent.quality_assessment).map(([key, value]) => (
                  <div key={key} className="p-3 bg-gray-50 rounded-lg">
                    <div className="text-xs text-gray-500 capitalize">{key.replace(/_/g, ' ')}</div>
                    <div className="text-lg font-semibold text-gray-900 mt-1">
                      {Math.round((value as number) * 100)}%
                    </div>
                  </div>
                ))}
              </div>
            </section>

            {/* Technologies by Category */}
            {categories.map(([category, technologies]) => (
              <section key={category}>
                <h3 className="text-sm font-semibold text-gray-900 mb-3 capitalize">
                  {category.replace(/_/g, ' ')} ({technologies.length})
                </h3>
                <div className="grid gap-3">
                  {technologies.map((tech: TechnologyChoice) => (
                    <div key={tech.name} className="p-3 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2">
                          <h4 className="font-medium text-gray-900">{tech.name}</h4>
                          {tech.version && (
                            <span className="text-xs text-gray-500">v{tech.version}</span>
                          )}
                        </div>
                        {tech.compatibility_score && (
                          <QualityScore score={tech.compatibility_score} size="sm" />
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">{tech.description}</p>
                      <p className="text-xs text-gray-500 mt-2 italic">{tech.rationale}</p>
                    </div>
                  ))}
                </div>
              </section>
            ))}

            {/* Implementation Guidance */}
            <section>
              <h3 className="text-sm font-semibold text-gray-900 mb-3">Implementation Guidance</h3>
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-900">{stackContent.implementation_guidance.rationale}</p>
                {stackContent.implementation_guidance.next_steps && (
                  <div className="mt-4">
                    <h4 className="text-sm font-medium text-blue-900 mb-2">Next Steps:</h4>
                    <ul className="space-y-1">
                      {stackContent.implementation_guidance.next_steps.map((step, idx) => (
                        <li key={idx} className="text-sm text-blue-800 flex items-start gap-2">
                          <span className="font-medium">{idx + 1}.</span>
                          {step}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </section>
          </div>
        );
      }

      default:
        // Fallback to JSON view
        return (
          <pre className="p-4 bg-gray-900 text-gray-100 text-xs rounded overflow-auto">
            {JSON.stringify(artifact.content, null, 2)}
          </pre>
        );
    }
  };

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-white">
        <div>
          <h2 className="font-semibold text-gray-900">{artifact.title}</h2>
          <p className="text-xs text-gray-500">
            {artifactTypeConfig[artifact.artifact_type]?.label || artifact.artifact_type}
            {artifact.version && ` • v${artifact.version}`}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleCopy}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <Download className="h-4 w-4" />
            Download
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-auto p-4">
        {renderContent()}
      </div>
    </div>
  );
}

/**
 * DocumentViewer page component
 */
export function DocumentViewer() {
  const { sessionId, artifactId } = useParams<{ sessionId: string; artifactId?: string }>();
  const addNotification = useUIStore((state) => state.addNotification);

  const [artifacts, setArtifacts] = useState<Artifact[]>([]);
  const [selectedArtifact, setSelectedArtifact] = useState<Artifact | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch artifacts
  useEffect(() => {
    async function fetchArtifacts() {
      if (!sessionId) return;

      setIsLoading(true);
      setError(null);

      try {
        let artifactList: Artifact[];

        if (isMockMode()) {
          artifactList = mockArtifacts.filter((a) => a.session_id === sessionId);
          if (artifactList.length === 0) {
            artifactList = mockArtifacts;
          }
        } else {
          artifactList = await orchestrationService.getArtifacts(sessionId);
        }

        setArtifacts(artifactList);

        // Select artifact by ID or first one
        if (artifactId) {
          const artifact = artifactList.find((a) => a.id === artifactId);
          setSelectedArtifact(artifact || artifactList[0] || null);
        } else if (artifactList.length > 0) {
          setSelectedArtifact(artifactList[0]);
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to load artifacts';
        setError(errorMessage);
        addNotification({ type: 'error', title: 'Error', message: errorMessage });
      } finally {
        setIsLoading(false);
      }
    }

    fetchArtifacts();
  }, [sessionId, artifactId, addNotification]);

  // Navigation between artifacts
  const currentIndex = selectedArtifact ? artifacts.findIndex((a) => a.id === selectedArtifact.id) : -1;
  const hasPrev = currentIndex > 0;
  const hasNext = currentIndex < artifacts.length - 1;

  const goToPrev = () => {
    if (hasPrev) {
      setSelectedArtifact(artifacts[currentIndex - 1]);
    }
  };

  const goToNext = () => {
    if (hasNext) {
      setSelectedArtifact(artifacts[currentIndex + 1]);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <AlertCircle className="h-12 w-12 text-red-500 mb-4" />
        <h2 className="text-lg font-medium text-gray-900 mb-2">Failed to Load Artifacts</h2>
        <p className="text-gray-500 text-center mb-4">{error}</p>
        <Link
          to={`/sessions/${sessionId}`}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          Back to Session
        </Link>
      </div>
    );
  }

  if (artifacts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full p-8">
        <FileText className="h-12 w-12 text-gray-400 mb-4" />
        <h2 className="text-lg font-medium text-gray-900 mb-2">No Artifacts Found</h2>
        <p className="text-gray-500 text-center mb-4">
          No artifacts have been generated for this session yet.
        </p>
        <Link
          to={`/sessions/${sessionId}`}
          className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
        >
          Back to Session
        </Link>
      </div>
    );
  }

  return (
    <div className="h-full flex">
      {/* Sidebar with artifact list */}
      <div className="w-72 border-r border-gray-200 bg-gray-50 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <Link
            to={`/sessions/${sessionId}`}
            className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 mb-3"
          >
            <ChevronLeft className="h-4 w-4" />
            Back to Session
          </Link>
          <h3 className="font-semibold text-gray-900">Generated Artifacts</h3>
          <p className="text-xs text-gray-500 mt-1">{artifacts.length} artifacts</p>
        </div>

        <div className="flex-1 overflow-auto p-3 space-y-2">
          {artifacts.map((artifact) => (
            <ArtifactCard
              key={artifact.id}
              artifact={artifact}
              isSelected={selectedArtifact?.id === artifact.id}
              onClick={() => setSelectedArtifact(artifact)}
            />
          ))}
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Navigation bar */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-white">
          <button
            onClick={goToPrev}
            disabled={!hasPrev}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <ChevronLeft className="h-4 w-4" />
            Previous
          </button>
          <span className="text-sm text-gray-500">
            {currentIndex + 1} of {artifacts.length}
          </span>
          <button
            onClick={goToNext}
            disabled={!hasNext}
            className="flex items-center gap-1 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Next
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {/* Artifact content */}
        {selectedArtifact && (
          <motion.div
            key={selectedArtifact.id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            className="flex-1 min-h-0"
          >
            <ArtifactContent artifact={selectedArtifact} />
          </motion.div>
        )}
      </div>
    </div>
  );
}

export default DocumentViewer;
