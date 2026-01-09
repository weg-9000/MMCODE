/**
 * ProjectVisualization page
 * Main visualization page with block canvas and mind map views
 */

import { useEffect, useState, useCallback, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Grid3X3,
  List,
  GitBranch,
  Play,
  Pause,
  RefreshCw,
  Settings,
  Download,
  Share2,
  ChevronRight,
  Loader2,
  AlertCircle,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useSessionStore, useVisualizationStore, useUIStore, type ViewMode } from '@/stores';
import { sessionService } from '@/services/sessionService';
import { orchestrationService } from '@/services/orchestrationService';
import { BlockCanvasLazy } from '@/components/visualization/BlockCanvasLazy';
import { MindMapViewLazy } from '@/components/visualization/MindMapViewLazy';
import { FilterPanel, SearchBar } from '@/components/visualization';
import { LoadingOverlay } from '@/components/shared/LoadingOverlay';
import type { BlockNode, BlockType } from '@/types';

/**
 * View mode toggle button
 */
function ViewModeToggle({
  mode,
  currentMode,
  icon: Icon,
  label,
  onClick,
}: {
  mode: ViewMode;
  currentMode: ViewMode;
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={clsx(
        'flex items-center gap-2 px-3 py-2 rounded-lg transition-colors',
        currentMode === mode
          ? 'bg-primary-100 text-primary-700'
          : 'text-gray-600 hover:bg-gray-100'
      )}
      title={label}
    >
      <Icon className="h-4 w-4" />
      <span className="text-sm font-medium hidden sm:inline">{label}</span>
    </button>
  );
}

/**
 * Orchestration progress panel
 */
function OrchestrationProgressPanel({
  sessionId,
  onStart,
  onCancel,
}: {
  sessionId: string;
  onStart: () => void;
  onCancel: () => void;
}) {
  // Use individual selector to prevent infinite re-renders
  const orchestrationProgress = useSessionStore((state) => state.orchestrationProgress);
  const progress = orchestrationProgress[sessionId];

  if (!progress) return null;

  const steps = [
    { id: 'analysis', label: 'Requirement Analysis', icon: '📋' },
    { id: 'architecture', label: 'Architecture Design', icon: '🏗️' },
    { id: 'stack', label: 'Stack Recommendation', icon: '📦' },
    { id: 'documentation', label: 'Documentation', icon: '📄' },
  ];

  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-gray-700">Orchestration Progress</h3>
        <div className="flex items-center gap-2">
          {progress.status === 'in_progress' || progress.status === 'started' ? (
            <button
              onClick={onCancel}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium text-red-600 bg-red-50 rounded-lg hover:bg-red-100 transition-colors"
            >
              <Pause className="h-3 w-3" />
              Cancel
            </button>
          ) : (
            <button
              onClick={onStart}
              disabled={progress.status === 'completed'}
              className={clsx(
                'flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors',
                progress.status === 'completed'
                  ? 'text-gray-400 bg-gray-100 cursor-not-allowed'
                  : 'text-primary-600 bg-primary-50 hover:bg-primary-100'
              )}
            >
              <Play className="h-3 w-3" />
              {progress.status === 'idle' ? 'Start' : 'Resume'}
            </button>
          )}
        </div>
      </div>

      {/* Steps */}
      <div className="space-y-2">
        {steps.map((step) => {
          const isCompleted = progress.completedSteps.includes(step.id);
          const isCurrent = progress.currentAgent === step.id;

          return (
            <div
              key={step.id}
              className={clsx(
                'flex items-center gap-3 px-3 py-2 rounded-lg',
                isCompleted && 'bg-green-50',
                isCurrent && 'bg-blue-50',
                !isCompleted && !isCurrent && 'bg-gray-50'
              )}
            >
              <span className="text-lg">{step.icon}</span>
              <span
                className={clsx(
                  'text-sm flex-1',
                  isCompleted && 'text-green-700',
                  isCurrent && 'text-blue-700 font-medium',
                  !isCompleted && !isCurrent && 'text-gray-500'
                )}
              >
                {step.label}
              </span>
              {isCompleted && (
                <span className="text-xs text-green-600">✓ Complete</span>
              )}
              {isCurrent && (
                <Loader2 className="h-4 w-4 text-blue-500 animate-spin" />
              )}
            </div>
          );
        })}
      </div>

      {/* Error message */}
      {progress.error && (
        <div className="mt-4 p-3 bg-red-50 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertCircle className="h-4 w-4 text-red-500 mt-0.5" />
            <p className="text-xs text-red-600">{progress.error}</p>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Detail panel for selected block
 */
function DetailPanel({
  node,
  onClose,
}: {
  node: BlockNode | null;
  onClose: () => void;
}) {
  if (!node) return null;

  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      className="w-80 bg-white border-l border-gray-200 h-full overflow-auto"
    >
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        <h3 className="font-medium text-gray-900">{node.data?.title}</h3>
        <button
          onClick={onClose}
          className="p-1 rounded hover:bg-gray-100 transition-colors"
        >
          <ChevronRight className="h-4 w-4 text-gray-400" />
        </button>
      </div>
      <div className="p-4">
        <p className="text-sm text-gray-500">
          Block details will be displayed here.
        </p>
      </div>
    </motion.div>
  );
}

/**
 * ProjectVisualization page component
 */
export function ProjectVisualization() {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();

  // Use individual selectors to prevent infinite re-renders
  const sessions = useSessionStore((state) => state.sessions);
  const setCurrentSession = useSessionStore((state) => state.setCurrentSession);

  const viewMode = useVisualizationStore((state) => state.viewMode);
  const setViewMode = useVisualizationStore((state) => state.setViewMode);
  const selectedNodeId = useVisualizationStore((state) => state.selectedNodeId);
  const selectNode = useVisualizationStore((state) => state.selectNode);
  const nodes = useVisualizationStore((state) => state.nodes);
  const setNodes = useVisualizationStore((state) => state.setNodes);
  const setEdges = useVisualizationStore((state) => state.setEdges);
  const showDetailPanel = useVisualizationStore((state) => state.showDetailPanel);
  const setShowDetailPanel = useVisualizationStore((state) => state.setShowDetailPanel);

  const addNotification = useUIStore((state) => state.addNotification);

  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Get current session
  const session = sessionId ? sessions[sessionId] : null;

  // Load session data
  useEffect(() => {
    if (!sessionId) {
      navigate('/');
      return;
    }

    const loadSession = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Set current session
        setCurrentSession(sessionId);

        // Fetch session details if not in store
        if (!sessions[sessionId]) {
          await sessionService.getSession(sessionId);
          // Session would be added to store via the service
        }

        // TODO: Transform session artifacts to nodes/edges
        // For now, create mock data
        const mockNodes: BlockNode[] = [
          {
            id: 'session-1',
            type: 'session',
            position: { x: 400, y: 50 },
            data: {
              id: 'session-1',
              type: 'session' as BlockType,
              title: session?.title || 'Project',
              status: 'completed',
              taskCount: 4,
              completedTasks: 2,
              artifactCount: 3,
            },
          },
          {
            id: 'analysis-1',
            type: 'analysis',
            position: { x: 100, y: 200 },
            data: {
              id: 'analysis-1',
              type: 'analysis' as BlockType,
              title: 'Requirement Analysis',
              status: 'completed',
              qualityScore: 0.85,
              functionalRequirements: ['User Auth', 'Dashboard', 'Reports'],
              nonFunctionalRequirements: ['Performance', 'Security'],
              domainConcepts: ['User', 'Project', 'Task'],
              stakeholders: ['Admin', 'User'],
            },
          },
          {
            id: 'architecture-1',
            type: 'architecture',
            position: { x: 350, y: 200 },
            data: {
              id: 'architecture-1',
              type: 'architecture' as BlockType,
              title: 'System Architecture',
              status: 'completed',
              qualityScore: 0.9,
              patterns: ['Microservices', 'Event-Driven'],
              layers: ['Presentation', 'Business', 'Data'],
              components: ['API Gateway', 'Auth Service', 'User Service'],
              decisions: ['ADR-001', 'ADR-002'],
            },
          },
          {
            id: 'stack-1',
            type: 'stack',
            position: { x: 600, y: 200 },
            data: {
              id: 'stack-1',
              type: 'stack' as BlockType,
              title: 'Tech Stack',
              status: 'processing',
              frontend: ['React', 'TypeScript', 'Tailwind'],
              backend: ['Python', 'FastAPI'],
              database: ['PostgreSQL', 'Redis'],
              infrastructure: ['Docker', 'Kubernetes'],
              reasoning: ['Scalability', 'Developer Experience'],
            },
          },
        ];

        setNodes(mockNodes);
        setEdges([
          { id: 'e1', source: 'session-1', target: 'analysis-1' },
          { id: 'e2', source: 'session-1', target: 'architecture-1' },
          { id: 'e3', source: 'session-1', target: 'stack-1' },
          { id: 'e4', source: 'analysis-1', target: 'architecture-1' },
        ]);
      } catch (err) {
        console.error('Failed to load session:', err);
        setError(err instanceof Error ? err.message : 'Failed to load session');
      } finally {
        setIsLoading(false);
      }
    };

    loadSession();
  }, [sessionId, navigate, setCurrentSession, sessions, setNodes, setEdges, session?.title]);

  // Handle orchestration start
  const handleStartOrchestration = useCallback(async () => {
    if (!sessionId) return;

    try {
      await orchestrationService.start({
        requirements: '', // Should be provided from session
        session_title: session?.title,
      });

      addNotification({
        type: 'info',
        title: 'Orchestration Started',
        message: 'AI agents are now processing your requirements',
      });
    } catch (err) {
      addNotification({
        type: 'error',
        title: 'Failed to Start',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }, [sessionId, session?.title, addNotification]);

  // Handle orchestration cancel
  const handleCancelOrchestration = useCallback(async () => {
    if (!sessionId) return;

    try {
      await orchestrationService.cancel(sessionId);
      addNotification({
        type: 'warning',
        title: 'Orchestration Cancelled',
        message: 'The orchestration process has been stopped',
      });
    } catch (err) {
      addNotification({
        type: 'error',
        title: 'Failed to Cancel',
        message: err instanceof Error ? err.message : 'Unknown error',
      });
    }
  }, [sessionId, addNotification]);

  // Get selected node
  const selectedNode = useMemo(() => {
    if (!selectedNodeId) return null;
    return nodes.find((n) => n.id === selectedNodeId) || null;
  }, [nodes, selectedNodeId]);

  // Loading state
  if (isLoading) {
    return <LoadingOverlay message="Loading project..." />;
  }

  // Error state
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <AlertCircle className="h-12 w-12 mx-auto text-red-400 mb-4" />
          <h2 className="text-lg font-medium text-gray-900 mb-2">
            Failed to load project
          </h2>
          <p className="text-sm text-gray-500 mb-4">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
          >
            Go to Dashboard
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 bg-white border-b border-gray-200">
        {/* Left: View mode toggles */}
        <div className="flex items-center gap-2">
          <ViewModeToggle
            mode="block"
            currentMode={viewMode}
            icon={Grid3X3}
            label="Block View"
            onClick={() => setViewMode('block')}
          />
          <ViewModeToggle
            mode="mindmap"
            currentMode={viewMode}
            icon={GitBranch}
            label="Mind Map"
            onClick={() => setViewMode('mindmap')}
          />
          <ViewModeToggle
            mode="list"
            currentMode={viewMode}
            icon={List}
            label="List View"
            onClick={() => setViewMode('list')}
          />
        </div>

        {/* Center: Search and filters */}
        <div className="flex items-center gap-2">
          <SearchBar className="w-64" />
          <FilterPanel />
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          <button
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Refresh"
          >
            <RefreshCw className="h-4 w-4 text-gray-600" />
          </button>
          <button
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Export"
          >
            <Download className="h-4 w-4 text-gray-600" />
          </button>
          <button
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Share"
          >
            <Share2 className="h-4 w-4 text-gray-600" />
          </button>
          <button
            className="p-2 rounded-lg hover:bg-gray-100 transition-colors"
            title="Settings"
          >
            <Settings className="h-4 w-4 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Visualization area */}
        <div className="flex-1 relative">
          {viewMode === 'block' && (
            <BlockCanvasLazy
              onNodeClick={(node) => {
                selectNode(node.id);
                setShowDetailPanel(true);
              }}
            />
          )}
          {viewMode === 'mindmap' && <MindMapViewLazy />}
          {viewMode === 'list' && (
            <div className="p-4">
              <p className="text-gray-500">List view coming soon...</p>
            </div>
          )}

          {/* Orchestration progress overlay */}
          {sessionId && (
            <div className="absolute bottom-4 left-4 w-80">
              <OrchestrationProgressPanel
                sessionId={sessionId}
                onStart={handleStartOrchestration}
                onCancel={handleCancelOrchestration}
              />
            </div>
          )}
        </div>

        {/* Detail panel */}
        <AnimatePresence>
          {showDetailPanel && (
            <DetailPanel
              node={selectedNode}
              onClose={() => setShowDetailPanel(false)}
            />
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}

export default ProjectVisualization;
