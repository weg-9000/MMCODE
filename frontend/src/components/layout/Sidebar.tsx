/**
 * Sidebar component
 * Session list and quick actions panel
 */

import { useState, useMemo } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Plus,
  FolderOpen,
  Clock,
  Star,
  Archive,
  ChevronRight,
  MoreHorizontal,
  Search,
  Filter,
} from 'lucide-react';
import { clsx } from 'clsx';
import { useSessionStore, useUIStore } from '@/stores';
import type { Session, SessionStatus } from '@/types';

/**
 * Sidebar section props
 */
interface SidebarSectionProps {
  title: string;
  icon: React.ReactNode;
  children: React.ReactNode;
  collapsible?: boolean;
  defaultOpen?: boolean;
}

/**
 * Collapsible sidebar section
 */
function SidebarSection({
  title,
  icon,
  children,
  collapsible = true,
  defaultOpen = true,
}: SidebarSectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  return (
    <div className="py-2">
      <button
        onClick={() => collapsible && setIsOpen(!isOpen)}
        className={clsx(
          'flex w-full items-center gap-2 px-3 py-2 text-xs font-semibold uppercase tracking-wider text-gray-500',
          collapsible && 'hover:text-gray-700 cursor-pointer'
        )}
      >
        {icon}
        <span className="flex-1 text-left">{title}</span>
        {collapsible && (
          <ChevronRight
            size={14}
            className={clsx('transition-transform', isOpen && 'rotate-90')}
          />
        )}
      </button>
      {isOpen && <div className="mt-1">{children}</div>}
    </div>
  );
}

/**
 * Session item in sidebar
 */
interface SessionItemProps {
  session: Session;
  isActive: boolean;
}

function SessionItem({ session, isActive }: SessionItemProps) {
  const getStatusColor = (status: SessionStatus) => {
    switch (status) {
      case 'active':
        return 'bg-green-500';
      case 'completed':
        return 'bg-blue-500';
      case 'archived':
        return 'bg-gray-400';
      default:
        return 'bg-gray-400';
    }
  };

  return (
    <Link
      to={`/session/${session.id}`}
      className={clsx(
        'group flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors',
        isActive
          ? 'bg-primary-50 text-primary-700'
          : 'text-gray-700 hover:bg-gray-100'
      )}
    >
      <span className={clsx('h-2 w-2 rounded-full', getStatusColor(session.status))} />
      <span className="flex-1 truncate">{session.title}</span>
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          // TODO: Open session menu
        }}
        className="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-gray-200 transition-opacity"
      >
        <MoreHorizontal size={14} />
      </button>
    </Link>
  );
}

export function Sidebar() {
  const location = useLocation();
  const navigate = useNavigate();

  // Use individual selectors to prevent infinite re-renders
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const sidebarWidth = useUIStore((state) => state.sidebarWidth);

  // Select raw data and memoize derived values
  const sessionsRecord = useSessionStore((state) => state.sessions);
  const recentSessionIds = useSessionStore((state) => state.recentSessionIds);

  // Memoize derived arrays to prevent re-renders
  const sessions = useMemo(() => Object.values(sessionsRecord), [sessionsRecord]);
  const recentSessions = useMemo(
    () => recentSessionIds.map((id) => sessionsRecord[id]).filter(Boolean) as Session[],
    [recentSessionIds, sessionsRecord]
  );

  // Filter sessions by status
  const activeSessions = sessions.filter((s) => s.status === 'active');
  const completedSessions = sessions.filter((s) => s.status === 'completed');

  if (!sidebarOpen) {
    return null;
  }

  return (
    <aside
      className="fixed left-0 top-16 z-30 h-[calc(100vh-4rem)] border-r border-gray-200 bg-white overflow-hidden flex flex-col lg:sticky"
      style={{ width: sidebarWidth }}
    >
      {/* New Analysis Button */}
      <div className="p-3 border-b border-gray-100">
        <button
          onClick={() => navigate('/new')}
          className="flex w-full items-center justify-center gap-2 rounded-lg bg-primary-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-primary-700 transition-colors"
        >
          <Plus size={18} />
          <span>New Analysis</span>
        </button>
      </div>

      {/* Search */}
      <div className="p-3 border-b border-gray-100">
        <div className="relative">
          <Search
            className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
            size={14}
          />
          <input
            type="search"
            placeholder="Search sessions..."
            className="h-8 w-full rounded-lg border border-gray-200 bg-gray-50 pl-9 pr-8 text-sm focus:bg-white focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
          />
          <button className="absolute right-2 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-gray-200">
            <Filter size={12} className="text-gray-400" />
          </button>
        </div>
      </div>

      {/* Sessions List */}
      <div className="flex-1 overflow-y-auto px-2">
        {/* Recent Sessions */}
        {recentSessions.length > 0 && (
          <SidebarSection
            title="Recent"
            icon={<Clock size={14} />}
            defaultOpen={true}
          >
            <div className="space-y-0.5">
              {recentSessions.slice(0, 5).map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={location.pathname === `/session/${session.id}`}
                />
              ))}
            </div>
          </SidebarSection>
        )}

        {/* Active Sessions */}
        <SidebarSection
          title="Active"
          icon={<FolderOpen size={14} />}
          defaultOpen={true}
        >
          {activeSessions.length > 0 ? (
            <div className="space-y-0.5">
              {activeSessions.map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={location.pathname === `/session/${session.id}`}
                />
              ))}
            </div>
          ) : (
            <p className="px-3 py-2 text-sm text-gray-500">No active sessions</p>
          )}
        </SidebarSection>

        {/* Completed Sessions */}
        <SidebarSection
          title="Completed"
          icon={<Star size={14} />}
          defaultOpen={false}
        >
          {completedSessions.length > 0 ? (
            <div className="space-y-0.5">
              {completedSessions.slice(0, 10).map((session) => (
                <SessionItem
                  key={session.id}
                  session={session}
                  isActive={location.pathname === `/session/${session.id}`}
                />
              ))}
            </div>
          ) : (
            <p className="px-3 py-2 text-sm text-gray-500">No completed sessions</p>
          )}
        </SidebarSection>

        {/* Archive Link */}
        <div className="py-2">
          <Link
            to="/archive"
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-gray-600 hover:bg-gray-100 transition-colors"
          >
            <Archive size={14} />
            <span>View Archive</span>
          </Link>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t border-gray-100 p-3">
        <div className="text-xs text-gray-400 text-center">
          {sessions.length} total sessions
        </div>
      </div>
    </aside>
  );
}

export default Sidebar;
