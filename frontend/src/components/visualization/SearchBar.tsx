/**
 * SearchBar component
 * Search functionality for visualization views
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Search, X, Command } from 'lucide-react';
import { clsx } from 'clsx';
import { useVisualizationStore } from '@/stores';

/**
 * Props for SearchBar
 */
interface SearchBarProps {
  className?: string;
  placeholder?: string;
  autoFocus?: boolean;
}

/**
 * SearchBar component
 */
export function SearchBar({
  className,
  placeholder = 'Search blocks...',
  autoFocus = false,
}: SearchBarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [isFocused, setIsFocused] = useState(false);

  // Use individual selectors to prevent infinite re-renders
  const searchQuery = useVisualizationStore((state) => state.searchQuery);
  const setSearchQuery = useVisualizationStore((state) => state.setSearchQuery);

  // Handle clear
  const handleClear = useCallback(() => {
    setSearchQuery('');
    inputRef.current?.focus();
  }, [setSearchQuery]);

  // Handle keyboard shortcut (Cmd/Ctrl + K)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        inputRef.current?.blur();
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className={clsx('relative', className)}>
      <div
        className={clsx(
          'flex items-center gap-2 px-3 py-2 bg-white rounded-lg border transition-all',
          isFocused
            ? 'border-primary-300 ring-2 ring-primary-100'
            : 'border-gray-200 hover:border-gray-300'
        )}
      >
        <Search
          className={clsx(
            'h-4 w-4 transition-colors',
            isFocused ? 'text-primary-500' : 'text-gray-400'
          )}
        />
        <input
          ref={inputRef}
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          placeholder={placeholder}
          autoFocus={autoFocus}
          className="flex-1 text-sm bg-transparent outline-none placeholder-gray-400"
        />

        {/* Clear button or keyboard shortcut hint */}
        <AnimatePresence mode="wait">
          {searchQuery ? (
            <motion.button
              key="clear"
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.8 }}
              onClick={handleClear}
              className="p-1 rounded hover:bg-gray-100 transition-colors"
            >
              <X className="h-3 w-3 text-gray-400" />
            </motion.button>
          ) : (
            <motion.div
              key="hint"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="hidden sm:flex items-center gap-1 text-xs text-gray-400"
            >
              <Command className="h-3 w-3" />
              <span>K</span>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Search suggestions/results count */}
      <AnimatePresence>
        {isFocused && searchQuery && (
          <motion.div
            initial={{ opacity: 0, y: -5 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -5 }}
            className="absolute top-full left-0 right-0 mt-1 px-3 py-2 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
          >
            <p className="text-xs text-gray-500">
              Press <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-600">Enter</kbd> to search or{' '}
              <kbd className="px-1 py-0.5 bg-gray-100 rounded text-gray-600">Esc</kbd> to close
            </p>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default SearchBar;
