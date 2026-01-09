/**
 * FilterPanel component
 * Provides filtering controls for visualization views
 */

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Filter, X, Check, ChevronDown } from 'lucide-react';
import { clsx } from 'clsx';
import { useVisualizationStore } from '@/stores';
import type { BlockType, BlockStatus } from '@/types';

/**
 * Block type options with labels and colors
 */
const blockTypeOptions: Array<{
  value: BlockType;
  label: string;
  color: string;
}> = [
  { value: 'analysis', label: 'Analysis', color: 'bg-purple-500' },
  { value: 'architecture', label: 'Architecture', color: 'bg-cyan-500' },
  { value: 'stack', label: 'Tech Stack', color: 'bg-emerald-500' },
  { value: 'document', label: 'Documents', color: 'bg-amber-500' },
  { value: 'session', label: 'Sessions', color: 'bg-indigo-500' },
];

/**
 * Block status options
 */
const blockStatusOptions: Array<{
  value: BlockStatus;
  label: string;
  color: string;
}> = [
  { value: 'pending', label: 'Pending', color: 'bg-gray-400' },
  { value: 'processing', label: 'Processing', color: 'bg-blue-500' },
  { value: 'completed', label: 'Completed', color: 'bg-green-500' },
  { value: 'failed', label: 'Failed', color: 'bg-red-500' },
];

/**
 * Props for FilterPanel
 */
interface FilterPanelProps {
  className?: string;
}

/**
 * FilterPanel component
 */
export function FilterPanel({ className }: FilterPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [showTypeDropdown, setShowTypeDropdown] = useState(false);
  const [showStatusDropdown, setShowStatusDropdown] = useState(false);

  // Use individual selectors to prevent infinite re-renders
  const filterOptions = useVisualizationStore((state) => state.filterOptions);
  const setFilterOptions = useVisualizationStore((state) => state.setFilterOptions);
  const resetFilters = useVisualizationStore((state) => state.resetFilters);

  // Toggle type filter
  const handleToggleType = (type: BlockType) => {
    const currentTypes = filterOptions.types;
    const newTypes = currentTypes.includes(type)
      ? currentTypes.filter((t) => t !== type)
      : [...currentTypes, type];
    setFilterOptions({ types: newTypes });
  };

  // Toggle status filter
  const handleToggleStatus = (status: BlockStatus) => {
    const currentStatuses = filterOptions.statuses;
    const newStatuses = currentStatuses.includes(status)
      ? currentStatuses.filter((s) => s !== status)
      : [...currentStatuses, status];
    setFilterOptions({ statuses: newStatuses });
  };

  // Count active filters
  const activeFilterCount =
    filterOptions.types.length + filterOptions.statuses.length;

  return (
    <div className={clsx('relative', className)}>
      {/* Filter toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={clsx(
          'flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors',
          isOpen || activeFilterCount > 0
            ? 'bg-primary-50 border-primary-200 text-primary-700'
            : 'bg-white border-gray-200 text-gray-700 hover:bg-gray-50'
        )}
      >
        <Filter className="h-4 w-4" />
        <span className="text-sm font-medium">Filters</span>
        {activeFilterCount > 0 && (
          <span className="flex items-center justify-center w-5 h-5 text-xs font-semibold bg-primary-500 text-white rounded-full">
            {activeFilterCount}
          </span>
        )}
        <ChevronDown
          className={clsx(
            'h-4 w-4 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {/* Filter dropdown */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            transition={{ duration: 0.15 }}
            className="absolute top-full left-0 mt-2 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-50"
          >
            <div className="p-4 space-y-4">
              {/* Block Type Filter */}
              <div>
                <button
                  onClick={() => setShowTypeDropdown(!showTypeDropdown)}
                  className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2"
                >
                  <span>Block Type</span>
                  <ChevronDown
                    className={clsx(
                      'h-4 w-4 transition-transform',
                      showTypeDropdown && 'rotate-180'
                    )}
                  />
                </button>
                <AnimatePresence>
                  {showTypeDropdown && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="space-y-1 overflow-hidden"
                    >
                      {blockTypeOptions.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => handleToggleType(option.value)}
                          className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer w-full text-left"
                        >
                          <div
                            className={clsx(
                              'w-4 h-4 rounded border-2 flex items-center justify-center transition-colors',
                              filterOptions.types.includes(option.value)
                                ? 'bg-primary-500 border-primary-500'
                                : 'border-gray-300'
                            )}
                          >
                            {filterOptions.types.includes(option.value) && (
                              <Check className="h-3 w-3 text-white" />
                            )}
                          </div>
                          <span
                            className={clsx('w-2 h-2 rounded-full', option.color)}
                          />
                          <span className="text-sm text-gray-700">
                            {option.label}
                          </span>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Status Filter */}
              <div>
                <button
                  onClick={() => setShowStatusDropdown(!showStatusDropdown)}
                  className="flex items-center justify-between w-full text-sm font-medium text-gray-700 mb-2"
                >
                  <span>Status</span>
                  <ChevronDown
                    className={clsx(
                      'h-4 w-4 transition-transform',
                      showStatusDropdown && 'rotate-180'
                    )}
                  />
                </button>
                <AnimatePresence>
                  {showStatusDropdown && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="space-y-1 overflow-hidden"
                    >
                      {blockStatusOptions.map((option) => (
                        <button
                          key={option.value}
                          type="button"
                          onClick={() => handleToggleStatus(option.value)}
                          className="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-gray-50 cursor-pointer w-full text-left"
                        >
                          <div
                            className={clsx(
                              'w-4 h-4 rounded border-2 flex items-center justify-center transition-colors',
                              filterOptions.statuses.includes(option.value)
                                ? 'bg-primary-500 border-primary-500'
                                : 'border-gray-300'
                            )}
                          >
                            {filterOptions.statuses.includes(option.value) && (
                              <Check className="h-3 w-3 text-white" />
                            )}
                          </div>
                          <span
                            className={clsx('w-2 h-2 rounded-full', option.color)}
                          />
                          <span className="text-sm text-gray-700">
                            {option.label}
                          </span>
                        </button>
                      ))}
                    </motion.div>
                  )}
                </AnimatePresence>
              </div>

              {/* Reset button */}
              {activeFilterCount > 0 && (
                <button
                  onClick={resetFilters}
                  className="flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700"
                >
                  <X className="h-3 w-3" />
                  Clear all filters
                </button>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default FilterPanel;
