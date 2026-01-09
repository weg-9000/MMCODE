/**
 * ERDViewer component
 * Renders Entity Relationship Diagrams using Mermaid
 */

import { useEffect, useRef, useState } from 'react';
import { clsx } from 'clsx';
import { Database, ZoomIn, ZoomOut, Maximize2, Download } from 'lucide-react';

/**
 * Entity definition
 */
interface Entity {
  name: string;
  attributes: Array<{
    name: string;
    type: string;
    isPrimaryKey?: boolean;
    isForeignKey?: boolean;
    isNullable?: boolean;
  }>;
}

/**
 * Relationship definition
 */
interface Relationship {
  from: string;
  to: string;
  type: 'one-to-one' | 'one-to-many' | 'many-to-many';
  label?: string;
}

/**
 * ERD data structure
 */
interface ERDData {
  entities: Entity[];
  relationships: Relationship[];
}

/**
 * Props for ERDViewer
 */
interface ERDViewerProps {
  data: ERDData;
  className?: string;
  mermaidCode?: string;
}

/**
 * Generate Mermaid ERD code from data
 */
function generateMermaidERD(data: ERDData): string {
  const lines = ['erDiagram'];

  // Add entities with attributes
  data.entities.forEach((entity) => {
    lines.push(`    ${entity.name} {`);
    entity.attributes.forEach((attr) => {
      const pk = attr.isPrimaryKey ? 'PK' : '';
      const fk = attr.isForeignKey ? 'FK' : '';
      const key = pk || fk || '';
      lines.push(`        ${attr.type} ${attr.name} ${key}`.trimEnd());
    });
    lines.push('    }');
  });

  // Add relationships
  data.relationships.forEach((rel) => {
    let relationSymbol: string;
    switch (rel.type) {
      case 'one-to-one':
        relationSymbol = '||--||';
        break;
      case 'one-to-many':
        relationSymbol = '||--o{';
        break;
      case 'many-to-many':
        relationSymbol = '}o--o{';
        break;
      default:
        relationSymbol = '||--||';
    }
    const label = rel.label ? ` : "${rel.label}"` : '';
    lines.push(`    ${rel.from} ${relationSymbol} ${rel.to}${label}`);
  });

  return lines.join('\n');
}

/**
 * ERDViewer component
 */
export function ERDViewer({ data, className, mermaidCode }: ERDViewerProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [zoom, setZoom] = useState(1);
  const [svgContent, setSvgContent] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Generate Mermaid code
  const code = mermaidCode || generateMermaidERD(data);

  // Render Mermaid diagram
  useEffect(() => {
    const renderDiagram = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Dynamic import of mermaid for code splitting
        const mermaid = (await import('mermaid')).default;

        mermaid.initialize({
          startOnLoad: false,
          theme: 'default',
          er: {
            diagramPadding: 20,
            layoutDirection: 'TB',
            minEntityWidth: 100,
            minEntityHeight: 75,
            entityPadding: 15,
            useMaxWidth: true,
          },
          securityLevel: 'loose',
        });

        const { svg } = await mermaid.render('erd-diagram', code);
        setSvgContent(svg);
      } catch (err) {
        console.error('Mermaid rendering error:', err);
        setError(err instanceof Error ? err.message : 'Failed to render diagram');
      } finally {
        setIsLoading(false);
      }
    };

    renderDiagram();
  }, [code]);

  // Zoom controls
  const handleZoomIn = () => setZoom((z) => Math.min(z + 0.25, 3));
  const handleZoomOut = () => setZoom((z) => Math.max(z - 0.25, 0.25));
  const handleResetZoom = () => setZoom(1);

  // Download SVG
  const handleDownload = () => {
    if (!svgContent) return;

    const blob = new Blob([svgContent], { type: 'image/svg+xml' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'erd-diagram.svg';
    link.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className={clsx('flex flex-col h-full bg-white rounded-lg border border-gray-200', className)}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-purple-500" />
          <span className="text-sm font-medium text-gray-700">
            Entity Relationship Diagram
          </span>
          <span className="text-xs text-gray-500">
            ({data.entities.length} entities, {data.relationships.length} relationships)
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleZoomOut}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors"
            title="Zoom Out"
          >
            <ZoomOut className="h-4 w-4 text-gray-600" />
          </button>
          <span className="text-xs text-gray-500 w-12 text-center">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={handleZoomIn}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors"
            title="Zoom In"
          >
            <ZoomIn className="h-4 w-4 text-gray-600" />
          </button>
          <button
            onClick={handleResetZoom}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors"
            title="Reset Zoom"
          >
            <Maximize2 className="h-4 w-4 text-gray-600" />
          </button>
          <div className="w-px h-4 bg-gray-300 mx-1" />
          <button
            onClick={handleDownload}
            disabled={!svgContent}
            className="p-1.5 rounded hover:bg-gray-200 transition-colors disabled:opacity-50"
            title="Download SVG"
          >
            <Download className="h-4 w-4 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Diagram container */}
      <div
        ref={containerRef}
        className="flex-1 overflow-auto p-4"
        style={{
          backgroundImage: 'radial-gradient(circle, #d1d5db 1px, transparent 1px)',
          backgroundSize: '20px 20px',
        }}
      >
        {isLoading && (
          <div className="flex items-center justify-center h-full">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary-500" />
          </div>
        )}

        {error && (
          <div className="flex flex-col items-center justify-center h-full text-red-500">
            <Database className="h-12 w-12 mb-2 opacity-50" />
            <p className="text-sm">Failed to render diagram</p>
            <p className="text-xs text-gray-500 mt-1">{error}</p>
          </div>
        )}

        {!isLoading && !error && svgContent && (
          <div
            className="transition-transform duration-200 origin-top-left"
            style={{ transform: `scale(${zoom})` }}
            dangerouslySetInnerHTML={{ __html: svgContent }}
          />
        )}
      </div>

      {/* Code preview toggle */}
      <details className="border-t border-gray-200">
        <summary className="px-4 py-2 text-xs text-gray-500 cursor-pointer hover:bg-gray-50">
          View Mermaid Code
        </summary>
        <pre className="p-4 bg-gray-900 text-gray-100 text-xs overflow-x-auto max-h-48">
          {code}
        </pre>
      </details>
    </div>
  );
}

export default ERDViewer;
