/**
 * Header component
 * Main navigation header with logo, navigation, and user menu
 */

import { Search, Bell, Settings, User, ChevronDown, PanelLeftClose, PanelLeft } from 'lucide-react';
import { useUIStore } from '@/stores';
import { Link, useLocation } from 'react-router-dom';
import { clsx } from 'clsx';

/**
 * Navigation item definition
 */
interface NavItem {
  label: string;
  href: string;
  icon?: React.ReactNode;
}

const navItems: NavItem[] = [
  { label: 'Dashboard', href: '/' },
  { label: 'New Analysis', href: '/new' },
  { label: 'Projects', href: '/projects' },
];

export function Header() {
  const location = useLocation();
  // Use individual selectors to prevent infinite re-renders
  const sidebarOpen = useUIStore((state) => state.sidebarOpen);
  const toggleSidebar = useUIStore((state) => state.toggleSidebar);

  return (
    <header className="sticky top-0 z-40 flex h-16 items-center gap-4 border-b border-gray-200 bg-white px-4 lg:px-6">
      {/* Sidebar toggle */}
      <button
        onClick={toggleSidebar}
        className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors lg:hidden"
        aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
      >
        {sidebarOpen ? <PanelLeftClose size={20} /> : <PanelLeft size={20} />}
      </button>

      {/* Logo */}
      <Link to="/" className="flex items-center gap-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary-600 text-white font-bold text-sm">
          MM
        </div>
        <span className="hidden font-semibold text-gray-900 sm:inline-block">
          MMCODE
        </span>
      </Link>

      {/* Navigation */}
      <nav className="hidden md:flex items-center gap-1 ml-6">
        {navItems.map((item) => (
          <Link
            key={item.href}
            to={item.href}
            className={clsx(
              'px-3 py-2 text-sm font-medium rounded-lg transition-colors',
              location.pathname === item.href
                ? 'bg-primary-50 text-primary-700'
                : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
            )}
          >
            {item.label}
          </Link>
        ))}
      </nav>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Search */}
      <div className="relative hidden lg:block">
        <Search
          className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400"
          size={16}
        />
        <input
          type="search"
          placeholder="Search sessions..."
          className="h-9 w-64 rounded-lg border border-gray-200 bg-gray-50 pl-9 pr-4 text-sm focus:bg-white focus:border-primary-500 focus:outline-none focus:ring-1 focus:ring-primary-500"
        />
        <kbd className="absolute right-3 top-1/2 -translate-y-1/2 hidden h-5 items-center gap-1 rounded border border-gray-200 bg-white px-1.5 text-[10px] font-medium text-gray-400 xl:flex">
          <span className="text-xs">⌘</span>K
        </kbd>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-2">
        {/* Search button (mobile) */}
        <button
          className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors lg:hidden"
          aria-label="Search"
        >
          <Search size={20} />
        </button>

        {/* Notifications */}
        <button
          className="relative flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
          aria-label="Notifications"
        >
          <Bell size={20} />
          {/* Notification badge */}
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
        </button>

        {/* Settings */}
        <button
          className="flex h-9 w-9 items-center justify-center rounded-lg text-gray-500 hover:bg-gray-100 hover:text-gray-700 transition-colors"
          aria-label="Settings"
        >
          <Settings size={20} />
        </button>

        {/* User menu */}
        <button className="flex items-center gap-2 rounded-lg border border-gray-200 px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors">
          <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary-100 text-primary-700">
            <User size={14} />
          </div>
          <span className="hidden sm:inline-block">User</span>
          <ChevronDown size={14} className="text-gray-400" />
        </button>
      </div>
    </header>
  );
}

export default Header;
