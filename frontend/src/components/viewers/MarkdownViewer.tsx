/**
 * MarkdownViewer component
 * Renders markdown content with syntax highlighting
 */

import { useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { clsx } from 'clsx';

/**
 * Props for MarkdownViewer
 */
interface MarkdownViewerProps {
  content: string;
  className?: string;
}

/**
 * MarkdownViewer component
 */
export function MarkdownViewer({ content, className }: MarkdownViewerProps) {
  // Memoize components to prevent re-renders
  const components = useMemo(
    () => ({
      // Custom heading styles
      h1: ({ children, ...props }: any) => (
        <h1
          className="text-2xl font-bold text-gray-900 mt-8 mb-4 pb-2 border-b border-gray-200"
          {...props}
        >
          {children}
        </h1>
      ),
      h2: ({ children, ...props }: any) => (
        <h2
          className="text-xl font-semibold text-gray-800 mt-6 mb-3"
          {...props}
        >
          {children}
        </h2>
      ),
      h3: ({ children, ...props }: any) => (
        <h3
          className="text-lg font-medium text-gray-800 mt-4 mb-2"
          {...props}
        >
          {children}
        </h3>
      ),
      h4: ({ children, ...props }: any) => (
        <h4
          className="text-base font-medium text-gray-700 mt-3 mb-2"
          {...props}
        >
          {children}
        </h4>
      ),

      // Paragraph
      p: ({ children, ...props }: any) => (
        <p className="text-gray-700 leading-relaxed mb-4" {...props}>
          {children}
        </p>
      ),

      // Lists
      ul: ({ children, ...props }: any) => (
        <ul className="list-disc list-inside space-y-1 mb-4 text-gray-700" {...props}>
          {children}
        </ul>
      ),
      ol: ({ children, ...props }: any) => (
        <ol className="list-decimal list-inside space-y-1 mb-4 text-gray-700" {...props}>
          {children}
        </ol>
      ),
      li: ({ children, ...props }: any) => (
        <li className="text-gray-700" {...props}>
          {children}
        </li>
      ),

      // Code blocks
      code: ({ inline, className: codeClassName, children, ...props }: any) => {
        if (inline) {
          return (
            <code
              className="px-1.5 py-0.5 bg-gray-100 text-gray-800 rounded text-sm font-mono"
              {...props}
            >
              {children}
            </code>
          );
        }
        return (
          <code
            className={clsx(
              'block bg-gray-900 text-gray-100 p-4 rounded-lg overflow-x-auto text-sm font-mono',
              codeClassName
            )}
            {...props}
          >
            {children}
          </code>
        );
      },
      pre: ({ children, ...props }: any) => (
        <pre className="mb-4" {...props}>
          {children}
        </pre>
      ),

      // Blockquote
      blockquote: ({ children, ...props }: any) => (
        <blockquote
          className="border-l-4 border-primary-500 pl-4 py-2 my-4 bg-primary-50 text-gray-700 italic"
          {...props}
        >
          {children}
        </blockquote>
      ),

      // Table
      table: ({ children, ...props }: any) => (
        <div className="overflow-x-auto mb-4">
          <table className="min-w-full divide-y divide-gray-200" {...props}>
            {children}
          </table>
        </div>
      ),
      thead: ({ children, ...props }: any) => (
        <thead className="bg-gray-50" {...props}>
          {children}
        </thead>
      ),
      tbody: ({ children, ...props }: any) => (
        <tbody className="bg-white divide-y divide-gray-200" {...props}>
          {children}
        </tbody>
      ),
      tr: ({ children, ...props }: any) => (
        <tr {...props}>{children}</tr>
      ),
      th: ({ children, ...props }: any) => (
        <th
          className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"
          {...props}
        >
          {children}
        </th>
      ),
      td: ({ children, ...props }: any) => (
        <td className="px-4 py-3 text-sm text-gray-700" {...props}>
          {children}
        </td>
      ),

      // Links
      a: ({ children, href, ...props }: any) => (
        <a
          href={href}
          className="text-primary-600 hover:text-primary-700 underline"
          target="_blank"
          rel="noopener noreferrer"
          {...props}
        >
          {children}
        </a>
      ),

      // Horizontal rule
      hr: (props: any) => (
        <hr className="my-6 border-gray-200" {...props} />
      ),

      // Images
      img: ({ src, alt, ...props }: any) => (
        <img
          src={src}
          alt={alt}
          className="max-w-full h-auto rounded-lg shadow-sm my-4"
          {...props}
        />
      ),
    }),
    []
  );

  return (
    <div className={clsx('prose prose-gray max-w-none', className)}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {content}
      </ReactMarkdown>
    </div>
  );
}

export default MarkdownViewer;
