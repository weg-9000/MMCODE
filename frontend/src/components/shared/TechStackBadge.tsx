/**
 * TechStackBadge component
 * Displays technology name with optional icon
 */

import { clsx } from 'clsx';

/**
 * Technology category for color coding
 */
export type TechCategory =
  | 'language'
  | 'framework'
  | 'database'
  | 'infrastructure'
  | 'ai'
  | 'devops'
  | 'default';

/**
 * Map technology names to categories
 */
const techCategoryMap: Record<string, TechCategory> = {
  // Languages
  python: 'language',
  javascript: 'language',
  typescript: 'language',
  java: 'language',
  go: 'language',
  rust: 'language',

  // Frameworks
  react: 'framework',
  vue: 'framework',
  angular: 'framework',
  fastapi: 'framework',
  django: 'framework',
  flask: 'framework',
  express: 'framework',
  nextjs: 'framework',
  'next.js': 'framework',
  spring: 'framework',

  // Databases
  postgresql: 'database',
  mysql: 'database',
  mongodb: 'database',
  redis: 'database',
  sqlite: 'database',
  pgvector: 'database',
  elasticsearch: 'database',

  // Infrastructure
  docker: 'infrastructure',
  kubernetes: 'infrastructure',
  aws: 'infrastructure',
  gcp: 'infrastructure',
  azure: 'infrastructure',
  terraform: 'infrastructure',

  // AI/ML
  langchain: 'ai',
  openai: 'ai',
  anthropic: 'ai',
  'gpt-4': 'ai',
  claude: 'ai',
  huggingface: 'ai',

  // DevOps
  github: 'devops',
  gitlab: 'devops',
  jenkins: 'devops',
  'ci/cd': 'devops',
};

/**
 * Get category for technology
 */
function getTechCategory(tech: string): TechCategory {
  const normalized = tech.toLowerCase().replace(/\s+/g, '').replace(/[^a-z0-9]/g, '');
  return techCategoryMap[normalized] || 'default';
}

/**
 * Category color classes
 */
const categoryColors: Record<TechCategory, string> = {
  language: 'bg-purple-100 text-purple-700 border-purple-200',
  framework: 'bg-blue-100 text-blue-700 border-blue-200',
  database: 'bg-green-100 text-green-700 border-green-200',
  infrastructure: 'bg-orange-100 text-orange-700 border-orange-200',
  ai: 'bg-pink-100 text-pink-700 border-pink-200',
  devops: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  default: 'bg-gray-100 text-gray-700 border-gray-200',
};

export interface TechStackBadgeProps {
  tech?: string;
  name?: string; // alias for tech
  version?: string;
  size?: 'sm' | 'md' | 'lg';
  category?: TechCategory;
  showCategory?: boolean;
  className?: string;
  onClick?: () => void;
}

export function TechStackBadge({
  tech,
  name,
  version,
  size = 'sm',
  category: categoryProp,
  showCategory = false,
  className,
  onClick,
}: TechStackBadgeProps) {
  // Use name as fallback for tech
  const techName = tech || name || '';
  const category = categoryProp || getTechCategory(techName);
  const colorClasses = categoryColors[category];

  const sizeClasses = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-2.5 py-1 text-sm',
    lg: 'px-3 py-1.5 text-sm',
  };

  return (
    <span
      className={clsx(
        'tech-badge inline-flex items-center gap-1 rounded-full border font-medium transition-colors',
        colorClasses,
        sizeClasses[size],
        onClick && 'cursor-pointer hover:opacity-80',
        className
      )}
      onClick={onClick}
      title={showCategory ? `${techName} (${category})` : techName}
    >
      <span>{techName}</span>
      {version && (
        <span className="opacity-60 text-[0.85em]">{version}</span>
      )}
    </span>
  );
}

/**
 * TechStackBadgeList component
 * Displays a list of tech badges with overflow handling
 */
interface TechStackBadgeListProps {
  technologies: string[];
  maxVisible?: number;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export function TechStackBadgeList({
  technologies,
  maxVisible = 5,
  size = 'sm',
  className,
}: TechStackBadgeListProps) {
  const visibleTechs = technologies.slice(0, maxVisible);
  const hiddenCount = technologies.length - maxVisible;

  return (
    <div className={clsx('flex flex-wrap gap-1', className)}>
      {visibleTechs.map((tech) => (
        <TechStackBadge key={tech} tech={tech} size={size} />
      ))}
      {hiddenCount > 0 && (
        <span
          className={clsx(
            'inline-flex items-center rounded-full bg-gray-100 text-gray-600 font-medium',
            size === 'sm' && 'px-2 py-0.5 text-xs',
            size === 'md' && 'px-2.5 py-1 text-sm',
            size === 'lg' && 'px-3 py-1.5 text-sm'
          )}
          title={technologies.slice(maxVisible).join(', ')}
        >
          +{hiddenCount}
        </span>
      )}
    </div>
  );
}

export default TechStackBadge;
