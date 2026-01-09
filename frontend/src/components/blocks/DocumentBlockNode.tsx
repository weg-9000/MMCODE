/**
 * DocumentBlockNode component
 * Displays generated documentation in block format
 */

import { memo } from 'react';
import { NodeProps } from 'reactflow';
import { FileText, Book, Code, FileJson, Table2 } from 'lucide-react';
import { clsx } from 'clsx';
import { BaseBlockNode } from './BaseBlockNode';
import type { DocumentBlockSummary } from '@/types';

/**
 * Props extending BlockNodeData with document-specific data
 */
interface DocumentNodeData extends DocumentBlockSummary {
  title: string;
  type: 'document';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  qualityScore?: number;
}

/**
 * Document type icons and colors
 */
const documentTypes: Record<string, {
  icon: React.ComponentType<{ className?: string }>;
  color: string;
  bgColor: string;
}> = {
  api: {
    icon: Code,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
  },
  openapi: {
    icon: FileJson,
    color: 'text-green-600',
    bgColor: 'bg-green-50',
  },
  erd: {
    icon: Table2,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
  },
  readme: {
    icon: Book,
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
  },
  guide: {
    icon: FileText,
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
  },
  markdown: {
    icon: FileText,
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
  },
};

/**
 * Get document type config
 */
function getDocTypeConfig(docType: string) {
  const key = docType.toLowerCase();
  return documentTypes[key] || documentTypes.markdown;
}

/**
 * DocumentBlockNode - Displays generated documentation
 */
export const DocumentBlockNode = memo(function DocumentBlockNode(
  props: NodeProps<DocumentNodeData>
) {
  const { data } = props;
  const {
    documentTypes: docTypes = [],
    totalPages = 0,
    sections = [],
    formats = [],
  } = data;

  return (
    <BaseBlockNode
      {...props}
      icon={<FileText className="h-4 w-4 text-amber-600" />}
      headerColor="bg-amber-50"
    >
      <div className="space-y-3">
        {/* Document Types */}
        {docTypes.length > 0 && (
          <div>
            <span className="text-xs font-medium text-gray-700 mb-1.5 block">
              Documents ({docTypes.length})
            </span>
            <div className="space-y-1.5">
              {docTypes.slice(0, 4).map((docType, idx) => {
                const name = typeof docType === 'string' ? docType : docType.name;
                const config = getDocTypeConfig(name);
                const IconComponent = config.icon;
                return (
                  <div
                    key={idx}
                    className={clsx(
                      'flex items-center gap-2 px-2 py-1.5 rounded',
                      config.bgColor
                    )}
                  >
                    <IconComponent className={clsx('h-3.5 w-3.5', config.color)} />
                    <span className="text-xs font-medium text-gray-700">{name}</span>
                  </div>
                );
              })}
              {docTypes.length > 4 && (
                <div className="text-xs text-gray-500 text-center py-1">
                  +{docTypes.length - 4} more documents
                </div>
              )}
            </div>
          </div>
        )}

        {/* Sections Preview */}
        {sections.length > 0 && (
          <div>
            <span className="text-xs font-medium text-gray-700 mb-1.5 block">
              Sections ({sections.length})
            </span>
            <div className="flex flex-wrap gap-1">
              {sections.slice(0, 5).map((section, idx) => {
                const name = typeof section === 'string' ? section : section.title;
                return (
                  <span
                    key={idx}
                    className="px-2 py-0.5 text-xs bg-amber-50 text-amber-700 rounded border border-amber-200"
                  >
                    {name}
                  </span>
                );
              })}
              {sections.length > 5 && (
                <span className="px-2 py-0.5 text-xs bg-gray-100 text-gray-500 rounded-full">
                  +{sections.length - 5}
                </span>
              )}
            </div>
          </div>
        )}

        {/* Formats */}
        {formats.length > 0 && (
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-500">Formats:</span>
            <div className="flex gap-1">
              {formats.map((format, idx) => (
                <span
                  key={idx}
                  className="px-1.5 py-0.5 text-xs bg-gray-100 text-gray-600 rounded font-mono"
                >
                  .{format}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Summary */}
        <div className="flex items-center justify-between pt-2 border-t border-gray-100">
          <span className="text-xs text-gray-500">
            {totalPages > 0 ? `${totalPages} pages` : 'Generated'}
          </span>
          {data.status === 'completed' && (
            <span className="text-xs text-green-600 font-medium">Ready to view</span>
          )}
        </div>
      </div>
    </BaseBlockNode>
  );
});

export default DocumentBlockNode;
