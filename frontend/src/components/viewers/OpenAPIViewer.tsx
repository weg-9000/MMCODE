/**
 * OpenAPIViewer component
 * Renders OpenAPI/Swagger documentation in a readable format
 */

import { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronDown,
  ChevronRight,
  Code,
  Server,
  Tag,
  Lock,
  Copy,
  Check,
} from 'lucide-react';
import { clsx } from 'clsx';

/**
 * HTTP method colors
 */
const methodColors: Record<string, string> = {
  get: 'bg-blue-500',
  post: 'bg-green-500',
  put: 'bg-amber-500',
  patch: 'bg-orange-500',
  delete: 'bg-red-500',
  options: 'bg-gray-500',
  head: 'bg-purple-500',
};

/**
 * OpenAPI specification type (simplified)
 */
interface OpenAPISpec {
  openapi: string;
  info: {
    title: string;
    version: string;
    description?: string;
  };
  servers?: Array<{ url: string; description?: string }>;
  paths: Record<string, Record<string, PathOperation>>;
  tags?: Array<{ name: string; description?: string }>;
  components?: {
    schemas?: Record<string, any>;
    securitySchemes?: Record<string, any>;
  };
}

interface PathOperation {
  summary?: string;
  description?: string;
  operationId?: string;
  tags?: string[];
  parameters?: Parameter[];
  requestBody?: RequestBody;
  responses?: Record<string, Response>;
  security?: Array<Record<string, string[]>>;
}

interface Parameter {
  name: string;
  in: 'query' | 'path' | 'header' | 'cookie';
  description?: string;
  required?: boolean;
  schema?: any;
}

interface RequestBody {
  description?: string;
  required?: boolean;
  content?: Record<string, { schema?: any }>;
}

interface Response {
  description?: string;
  content?: Record<string, { schema?: any }>;
}

/**
 * Props for OpenAPIViewer
 */
interface OpenAPIViewerProps {
  spec: OpenAPISpec;
  className?: string;
}

/**
 * Single endpoint component
 */
function EndpointItem({
  path,
  method,
  operation,
}: {
  path: string;
  method: string;
  operation: PathOperation;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [copied, setCopied] = useState(false);

  const handleCopyPath = () => {
    navigator.clipboard.writeText(path);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-3 p-3 hover:bg-gray-50 transition-colors"
      >
        {/* Method badge */}
        <span
          className={clsx(
            'px-2 py-1 text-xs font-bold text-white uppercase rounded',
            methodColors[method.toLowerCase()] || 'bg-gray-500'
          )}
        >
          {method}
        </span>

        {/* Path */}
        <code className="flex-1 text-sm text-gray-700 text-left font-mono">
          {path}
        </code>

        {/* Summary */}
        {operation.summary && (
          <span className="text-sm text-gray-500 truncate max-w-xs">
            {operation.summary}
          </span>
        )}

        {/* Security indicator */}
        {operation.security && operation.security.length > 0 && (
          <Lock className="h-4 w-4 text-amber-500" />
        )}

        {/* Expand icon */}
        {isExpanded ? (
          <ChevronDown className="h-4 w-4 text-gray-400" />
        ) : (
          <ChevronRight className="h-4 w-4 text-gray-400" />
        )}
      </button>

      {/* Expanded content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden"
          >
            <div className="p-4 border-t border-gray-200 bg-gray-50 space-y-4">
              {/* Description */}
              {operation.description && (
                <p className="text-sm text-gray-600">{operation.description}</p>
              )}

              {/* Copy path button */}
              <button
                onClick={handleCopyPath}
                className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700"
              >
                {copied ? (
                  <Check className="h-3 w-3 text-green-500" />
                ) : (
                  <Copy className="h-3 w-3" />
                )}
                {copied ? 'Copied!' : 'Copy path'}
              </button>

              {/* Parameters */}
              {operation.parameters && operation.parameters.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Parameters</h4>
                  <div className="space-y-2">
                    {operation.parameters.map((param, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-2 text-sm bg-white p-2 rounded border border-gray-100"
                      >
                        <code className="font-mono text-gray-800">{param.name}</code>
                        <span
                          className={clsx(
                            'px-1.5 py-0.5 text-xs rounded',
                            param.in === 'path'
                              ? 'bg-blue-100 text-blue-700'
                              : param.in === 'query'
                              ? 'bg-green-100 text-green-700'
                              : 'bg-gray-100 text-gray-700'
                          )}
                        >
                          {param.in}
                        </span>
                        {param.required && (
                          <span className="text-xs text-red-500">required</span>
                        )}
                        {param.description && (
                          <span className="text-gray-500 text-xs">
                            {param.description}
                          </span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Request Body */}
              {operation.requestBody && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">
                    Request Body
                    {operation.requestBody.required && (
                      <span className="ml-2 text-xs text-red-500">required</span>
                    )}
                  </h4>
                  {operation.requestBody.description && (
                    <p className="text-xs text-gray-500 mb-2">
                      {operation.requestBody.description}
                    </p>
                  )}
                  {operation.requestBody.content && (
                    <div className="text-xs text-gray-500">
                      Content types:{' '}
                      {Object.keys(operation.requestBody.content).join(', ')}
                    </div>
                  )}
                </div>
              )}

              {/* Responses */}
              {operation.responses && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">Responses</h4>
                  <div className="space-y-1">
                    {Object.entries(operation.responses).map(([code, response]) => (
                      <div
                        key={code}
                        className="flex items-center gap-2 text-sm"
                      >
                        <span
                          className={clsx(
                            'px-2 py-0.5 text-xs font-mono rounded',
                            code.startsWith('2')
                              ? 'bg-green-100 text-green-700'
                              : code.startsWith('4')
                              ? 'bg-amber-100 text-amber-700'
                              : code.startsWith('5')
                              ? 'bg-red-100 text-red-700'
                              : 'bg-gray-100 text-gray-700'
                          )}
                        >
                          {code}
                        </span>
                        <span className="text-gray-600">
                          {response.description}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tags */}
              {operation.tags && operation.tags.length > 0 && (
                <div className="flex items-center gap-2">
                  <Tag className="h-3 w-3 text-gray-400" />
                  <div className="flex gap-1">
                    {operation.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * OpenAPIViewer component
 */
export function OpenAPIViewer({ spec, className }: OpenAPIViewerProps) {
  const [filterTag, setFilterTag] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');

  // Group endpoints by tag
  const endpointsByTag = useMemo(() => {
    const grouped: Record<string, Array<{ path: string; method: string; operation: PathOperation }>> = {};

    Object.entries(spec.paths).forEach(([path, methods]) => {
      Object.entries(methods).forEach(([method, operation]) => {
        if (typeof operation !== 'object') return;

        const tags = operation.tags || ['untagged'];
        tags.forEach((tag) => {
          if (!grouped[tag]) grouped[tag] = [];
          grouped[tag].push({ path, method, operation });
        });
      });
    });

    return grouped;
  }, [spec.paths]);

  // Filter endpoints
  const filteredEndpoints = useMemo(() => {
    let endpoints = filterTag
      ? { [filterTag]: endpointsByTag[filterTag] || [] }
      : endpointsByTag;

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      const filtered: typeof endpoints = {};

      Object.entries(endpoints).forEach(([tag, ops]) => {
        const matchingOps = ops.filter(
          ({ path, operation }) =>
            path.toLowerCase().includes(query) ||
            operation.summary?.toLowerCase().includes(query) ||
            operation.description?.toLowerCase().includes(query)
        );
        if (matchingOps.length > 0) {
          filtered[tag] = matchingOps;
        }
      });

      endpoints = filtered;
    }

    return endpoints;
  }, [endpointsByTag, filterTag, searchQuery]);

  return (
    <div className={clsx('flex flex-col h-full bg-white', className)}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-start justify-between mb-2">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              {spec.info.title}
            </h2>
            <p className="text-sm text-gray-500">
              Version {spec.info.version} | OpenAPI {spec.openapi}
            </p>
          </div>
          {spec.servers && spec.servers.length > 0 && (
            <div className="flex items-center gap-2 text-sm text-gray-500">
              <Server className="h-4 w-4" />
              <span>{spec.servers[0].url}</span>
            </div>
          )}
        </div>
        {spec.info.description && (
          <p className="text-sm text-gray-600">{spec.info.description}</p>
        )}
      </div>

      {/* Filters */}
      <div className="p-4 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-4">
          {/* Search */}
          <div className="flex-1">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search endpoints..."
              className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>

          {/* Tag filter */}
          {spec.tags && spec.tags.length > 0 && (
            <select
              value={filterTag || ''}
              onChange={(e) => setFilterTag(e.target.value || null)}
              className="px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500"
            >
              <option value="">All tags</option>
              {spec.tags.map((tag) => (
                <option key={tag.name} value={tag.name}>
                  {tag.name}
                </option>
              ))}
            </select>
          )}
        </div>
      </div>

      {/* Endpoints list */}
      <div className="flex-1 overflow-auto p-4">
        <div className="space-y-6">
          {Object.entries(filteredEndpoints).map(([tag, endpoints]) => (
            <div key={tag}>
              <h3 className="text-sm font-medium text-gray-500 uppercase mb-3">
                {tag}
              </h3>
              <div className="space-y-2">
                {endpoints.map(({ path, method, operation }, idx) => (
                  <EndpointItem
                    key={`${path}-${method}-${idx}`}
                    path={path}
                    method={method}
                    operation={operation}
                  />
                ))}
              </div>
            </div>
          ))}

          {Object.keys(filteredEndpoints).length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <Code className="h-12 w-12 mx-auto mb-2 opacity-50" />
              <p className="text-sm">No endpoints found</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default OpenAPIViewer;
