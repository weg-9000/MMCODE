/**
 * Dashboard page
 * Overview of sessions, recent activities, and quick actions
 */

import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  Plus,
  FolderKanban,
  Clock,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  FileSearch,
  Layers,
  Package,
  FileText,
  ArrowRight,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useSessionStore } from '@/stores';
import type { Session, SessionStatus } from '@/types';

/**
 * Stat card component
 */
function StatCard({
  icon: Icon,
  label,
  value,
  trend,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  label: string;
  value: string | number;
  trend?: { value: number; label: string };
  color: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="bg-white rounded-xl border border-gray-200 p-4 shadow-sm hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between">
        <div className={clsx('p-2 rounded-lg', color)}>
          <Icon className="h-5 w-5" />
        </div>
        {trend && (
          <div
            className={clsx(
              'flex items-center gap-1 text-xs font-medium',
              trend.value >= 0 ? 'text-green-600' : 'text-red-600'
            )}
          >
            <TrendingUp
              className={clsx(
                'h-3 w-3',
                trend.value < 0 && 'rotate-180'
              )}
            />
            {Math.abs(trend.value)}%
          </div>
        )}
      </div>
      <div className="mt-3">
        <p className="text-2xl font-semibold text-gray-900">{value}</p>
        <p className="text-sm text-gray-500">{label}</p>
      </div>
    </motion.div>
  );
}

/**
 * Recent session card
 */
function SessionCard({ session }: { session: Session }) {
  const statusColors: Record<SessionStatus, string> = {
    active: 'bg-blue-100 text-blue-600',
    completed: 'bg-green-100 text-green-600',
    archived: 'bg-gray-100 text-gray-600',
  };

  return (
    <Link
      to={`/sessions/${session.id}`}
      className="block bg-white rounded-lg border border-gray-200 p-4 hover:shadow-md hover:border-gray-300 transition-all"
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          <FolderKanban className="h-4 w-4 text-indigo-500" />
          <h3 className="font-medium text-gray-900 truncate max-w-[200px]">
            {session.title}
          </h3>
        </div>
        <span
          className={clsx(
            'px-2 py-0.5 text-xs font-medium rounded-full',
            statusColors[session.status]
          )}
        >
          {session.status}
        </span>
      </div>

      {session.description && (
        <p className="text-sm text-gray-500 mb-3 line-clamp-2">
          {session.description}
        </p>
      )}

      <div className="flex items-center justify-between text-xs text-gray-400">
        <div className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {new Date(session.updated_at).toLocaleDateString()}
        </div>
        <ArrowRight className="h-3 w-3" />
      </div>
    </Link>
  );
}

/**
 * Quick action card
 */
function QuickActionCard({
  icon: Icon,
  title,
  description,
  to,
  color,
}: {
  icon: React.ComponentType<{ className?: string }>;
  title: string;
  description: string;
  to: string;
  color: string;
}) {
  return (
    <Link
      to={to}
      className="flex items-start gap-3 p-4 bg-white rounded-lg border border-gray-200 hover:shadow-md hover:border-gray-300 transition-all group"
    >
      <div className={clsx('p-2 rounded-lg', color)}>
        <Icon className="h-5 w-5" />
      </div>
      <div className="flex-1">
        <h4 className="font-medium text-gray-900 group-hover:text-primary-600 transition-colors">
          {title}
        </h4>
        <p className="text-sm text-gray-500">{description}</p>
      </div>
      <ArrowRight className="h-4 w-4 text-gray-400 group-hover:text-primary-500 transition-colors" />
    </Link>
  );
}

/**
 * Dashboard page component
 */
export function Dashboard() {
  // Use individual selectors to prevent infinite re-renders
  const sessions = useSessionStore((state) => state.sessions);
  const recentSessionIds = useSessionStore((state) => state.recentSessionIds);

  // Calculate stats
  const stats = useMemo(() => {
    const sessionsArray = Object.values(sessions);
    const completed = sessionsArray.filter((s) => s.status === 'completed').length;
    const active = sessionsArray.filter((s) => s.status === 'active').length;
    const archived = sessionsArray.filter((s) => s.status === 'archived').length;

    return {
      total: sessionsArray.length,
      completed,
      active,
      archived,
    };
  }, [sessions]);

  // Get recent sessions
  const recentSessions = useMemo(() => {
    return recentSessionIds
      .slice(0, 5)
      .map((id) => sessions[id])
      .filter(Boolean);
  }, [sessions, recentSessionIds]);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Dashboard</h1>
          <p className="text-sm text-gray-500 mt-1">
            Welcome back! Here's an overview of your projects.
          </p>
        </div>
        <Link
          to="/new"
          className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
        >
          <Plus className="h-4 w-4" />
          New Project
        </Link>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          icon={FolderKanban}
          label="Total Projects"
          value={stats.total}
          color="bg-indigo-100 text-indigo-600"
        />
        <StatCard
          icon={Clock}
          label="Active"
          value={stats.active}
          color="bg-blue-100 text-blue-600"
        />
        <StatCard
          icon={CheckCircle2}
          label="Completed"
          value={stats.completed}
          trend={{ value: 12, label: 'vs last month' }}
          color="bg-green-100 text-green-600"
        />
        <StatCard
          icon={AlertCircle}
          label="Archived"
          value={stats.archived}
          color="bg-gray-100 text-gray-600"
        />
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Recent Sessions */}
        <div className="lg:col-span-2">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-medium text-gray-900">Recent Projects</h2>
            <Link
              to="/sessions"
              className="text-sm text-primary-600 hover:text-primary-700"
            >
              View all
            </Link>
          </div>
          <div className="space-y-3">
            {recentSessions.length > 0 ? (
              recentSessions.map((session) => (
                <SessionCard key={session.id} session={session} />
              ))
            ) : (
              <div className="bg-white rounded-lg border border-gray-200 p-8 text-center">
                <FolderKanban className="h-12 w-12 mx-auto text-gray-300 mb-3" />
                <p className="text-gray-500 mb-4">No projects yet</p>
                <Link
                  to="/new"
                  className="inline-flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                >
                  <Plus className="h-4 w-4" />
                  Create your first project
                </Link>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div>
          <h2 className="text-lg font-medium text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <QuickActionCard
              icon={FileSearch}
              title="Analyze Requirements"
              description="Start with requirement analysis"
              to="/new?step=analysis"
              color="bg-purple-100 text-purple-600"
            />
            <QuickActionCard
              icon={Layers}
              title="Design Architecture"
              description="Create system architecture"
              to="/new?step=architecture"
              color="bg-cyan-100 text-cyan-600"
            />
            <QuickActionCard
              icon={Package}
              title="Recommend Stack"
              description="Get technology recommendations"
              to="/new?step=stack"
              color="bg-emerald-100 text-emerald-600"
            />
            <QuickActionCard
              icon={FileText}
              title="Generate Docs"
              description="Create documentation"
              to="/new?step=documents"
              color="bg-amber-100 text-amber-600"
            />
          </div>
        </div>
      </div>

      {/* Activity Timeline (placeholder) */}
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Recent Activity</h2>
        <div className="text-center text-gray-500 py-8">
          <Clock className="h-12 w-12 mx-auto text-gray-300 mb-3" />
          <p className="text-sm">Activity timeline will appear here</p>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
