/* eslint-disable */
// components/chat/RichMessageRenderer.jsx
import React, { useState, useMemo, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import mermaid from 'mermaid';
import 'katex/dist/katex.min.css';
import {
  Copy, Check, Play, ExternalLink, Maximize2,
  FileText, Table, BarChart2, Code, Hash
} from 'lucide-react';

mermaid.initialize({ startOnLoad: false, theme: 'dark' });

// Custom code block with enhanced features
const CodeBlock = ({
  inline,
  className,
  children,
  onRun,
  onApply,
  ...props
}) => {
  const [copied, setCopied] = useState(false);
  const match = /language-(\w+)/.exec(className || '');
  const language = match ? match[1] : '';
  const codeString = String(children).replace(/\n$/, '');

  const handleCopy = async () => {
    await navigator.clipboard.writeText(codeString);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!inline && language) {
    return (
      <div className="group relative my-4">
        <div className="absolute top-0 right-0 flex items-center space-x-1 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
          {['python', 'javascript', 'typescript'].includes(language) && onRun && (
            <button
              onClick={() => onRun(codeString, language)}
              className="p-1 bg-green-600 text-white rounded hover:bg-green-700"
              title="Run code"
            >
              <Play className="w-4 h-4" />
            </button>
          )}
          {onApply && (
            <button
              onClick={() => onApply(codeString, language)}
              className="p-1 bg-blue-600 text-white rounded hover:bg-blue-700"
              title="Apply to editor"
            >
              <ExternalLink className="w-4 h-4" />
            </button>
          )}
          <button
            onClick={handleCopy}
            className="p-1 bg-gray-700 text-white rounded hover:bg-gray-600"
            title="Copy code"
          >
            {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
          </button>
        </div>
        <SyntaxHighlighter
          style={oneDark}
          language={language}
          PreTag="div"
          customStyle={{
            margin: 0,
            borderRadius: '0.5rem',
            fontSize: '0.875rem'
          }}
          {...props}
        >
          {codeString}
        </SyntaxHighlighter>
        <div className="absolute bottom-2 left-2 text-xs text-gray-400 opacity-60">
          {language}
        </div>
      </div>
    );
  }

  return (
    <code className="bg-gray-100 dark:bg-gray-800 px-1 py-0.5 rounded text-sm" {...props}>
      {children}
    </code>
  );
};

// Mermaid diagram renderer
const MermaidDiagram = ({ chart, onClick }) => {
  const [svg, setSvg] = useState('');
  const [error, setError] = useState(null);

  React.useEffect(() => {
    const renderDiagram = async () => {
      try {
        const id = `mermaid-${Date.now()}`;
        const { svg } = await mermaid.render(id, chart);
        setSvg(svg);
      } catch (err) {
        setError('Failed to render diagram');
        console.error('Mermaid error:', err);
      }
    };

    renderDiagram();
  }, [chart]);

  if (error) {
    return (
      <div className="p-4 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-600 dark:text-red-400">
        {error}
      </div>
    );
  }

  return (
    <div
      className="my-4 bg-gray-50 dark:bg-gray-800 rounded-lg p-4 overflow-x-auto cursor-pointer"
      onClick={onClick}
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
};

// Interactive table component
const InteractiveTable = ({ data }) => {
  const [sortColumn, setSortColumn] = useState(null);
  const [sortDirection, setSortDirection] = useState('asc');

  const sortedData = useMemo(() => {
    if (sortColumn === null || data.length < 2) return data;

    const [header, ...rows] = data;
    const sorted = [...rows].sort((a, b) => {
      const aVal = a[sortColumn];
      const bVal = b[sortColumn];

      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortDirection === 'asc' ? aVal - bVal : bVal - aVal;
      }

      return sortDirection === 'asc'
        ? String(aVal).localeCompare(String(bVal))
        : String(bVal).localeCompare(String(aVal));
    });

    return [header, ...sorted];
  }, [data, sortColumn, sortDirection]);

  const handleSort = (columnIndex) => {
    if (sortColumn === columnIndex) {
      setSortDirection(prev => prev === 'asc' ? 'desc' : 'asc');
    } else {
      setSortColumn(columnIndex);
      setSortDirection('asc');
    }
  };

  if (data.length === 0) return null;

  const [header, ...rows] = sortedData;

  return (
    <div className="my-4 overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
        <thead className="bg-gray-50 dark:bg-gray-800">
          <tr>
            {header.map((cell, idx) => (
              <th
                key={idx}
                onClick={() => handleSort(idx)}
                className="px-4 py-2 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-700"
              >
                <div className="flex items-center space-x-1">
                  <span>{cell}</span>
                  <Hash className="w-3 h-3 opacity-50" />
                </div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className="hover:bg-gray-50 dark:hover:bg-gray-800">
              {row.map((cell, cellIdx) => (
                <td key={cellIdx} className="px-4 py-2 text-sm text-gray-900 dark:text-gray-100">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// Chart renderer (placeholder - would integrate with a charting library)
const ChartRenderer = ({ type, data }) => {
  return (
    <div className="my-4 p-8 bg-gray-50 dark:bg-gray-800 rounded-lg text-center">
      <BarChart2 className="w-12 h-12 mx-auto mb-2 text-gray-400" />
      <p className="text-sm text-gray-600 dark:text-gray-400">
        {type} chart visualization would appear here
      </p>
    </div>
  );
};

export default function RichMessageRenderer({
  content,
  metadata,
  onCodeRun,
  onCodeApply,
  onDiagramClick
}) {
  const [activeTab, setActiveTab] = useState('rendered');

  // Parse special content blocks
  const { processedContent, specialBlocks } = useMemo(() => {
    let processed = content;
    const blocks = [];

    // Extract mermaid diagrams
    const mermaidRegex = /```mermaid\n([\s\S]*?)```/g;
    processed = processed.replace(mermaidRegex, (match, diagram) => {
      const id = `mermaid-${blocks.length}`;
      blocks.push({ type: 'mermaid', id, content: diagram.trim() });
      return `<div id="${id}"></div>`;
    });

    // Extract tables (simple markdown tables)
    const tableRegex = /\|(.+)\|[\s\S]*?\n\|(.+)\|/g;
    const tables = processed.match(tableRegex);
    if (tables) {
      tables.forEach((table, idx) => {
        const rows = table.trim().split('\n')
          .filter(row => row.includes('|') && !row.match(/^\|[-:\s|]+\|$/))
          .map(row => row.split('|').slice(1, -1).map(cell => cell.trim()));

        if (rows.length > 1) {
          const id = `table-${idx}`;
          blocks.push({ type: 'table', id, content: rows });
        }
      });
    }

    return { processedContent: processed, specialBlocks: blocks };
  }, [content]);

  // Custom renderers for ReactMarkdown
  const renderers = {
    code: (props) => (
      <CodeBlock
        {...props}
        onRun={onCodeRun}
        onApply={onCodeApply}
      />
    ),
    // Override default table rendering with interactive table
    table: ({ children }) => {
      const tableData = extractTableData(children);
      return <InteractiveTable data={tableData} />;
    }
  };

  // Extract table data from markdown AST
  const extractTableData = (children) => {
    // Parse table AST and extract data
    try {
      if (!children || !Array.isArray(children)) return [];

      const tableData = [];

      // Find thead and tbody elements
      children.forEach(child => {
        if (child.type === 'thead' && child.children) {
          const headerRow = [];
          child.children.forEach(row => {
            if (row.type === 'tr' && row.children) {
              row.children.forEach(cell => {
                if (cell.type === 'th' && cell.children) {
                  headerRow.push(cell.children.map(c => c.value || '').join(''));
                }
              });
            }
          });
          if (headerRow.length > 0) tableData.push(headerRow);
        }

        if (child.type === 'tbody' && child.children) {
          child.children.forEach(row => {
            if (row.type === 'tr' && row.children) {
              const dataRow = [];
              row.children.forEach(cell => {
                if (cell.type === 'td' && cell.children) {
                  dataRow.push(cell.children.map(c => c.value || '').join(''));
                }
              });
              if (dataRow.length > 0) tableData.push(dataRow);
            }
          });
        }
      });

      return tableData;
    } catch (error) {
      console.error('Error parsing table data:', error);
      return [];
    }
  };

  // Render special blocks
  const renderSpecialBlock = (block) => {
    switch (block.type) {
      case 'mermaid':
        return (
          <MermaidDiagram
            key={block.id}
            chart={block.content}
            onClick={() => onDiagramClick?.(block.content)}
          />
        );
      case 'table':
        return (
          <InteractiveTable
            key={block.id}
            data={block.content}
          />
        );
      case 'chart':
        return (
          <ChartRenderer
            key={block.id}
            type={block.chartType}
            data={block.content}
          />
        );
      default:
        return null;
    }
  };

  return (
    <div className="rich-message-renderer">
      {/* Tab switcher for raw/rendered view */}
      <div className="flex items-center justify-end mb-2 space-x-2">
        <button
          onClick={() => setActiveTab('rendered')}
          className={`text-xs px-2 py-1 rounded ${
            activeTab === 'rendered'
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <FileText className="w-3 h-3 inline mr-1" />
          Rendered
        </button>
        <button
          onClick={() => setActiveTab('raw')}
          className={`text-xs px-2 py-1 rounded ${
            activeTab === 'raw'
              ? 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-100'
              : 'text-gray-500 hover:text-gray-700'
          }`}
        >
          <Code className="w-3 h-3 inline mr-1" />
          Raw
        </button>
      </div>

      {activeTab === 'rendered' ? (
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm, remarkMath]}
            rehypePlugins={[rehypeKatex]}
            components={renderers}
          >
            {processedContent}
          </ReactMarkdown>

          {/* Render special blocks */}
          {specialBlocks.map(block => renderSpecialBlock(block))}

          {/* Render metadata charts/tables if any */}
          {metadata?.charts?.map((chart, idx) => (
            <ChartRenderer
              key={`meta-chart-${idx}`}
              type={chart.type}
              data={chart.data}
            />
          ))}

          {metadata?.tables?.map((table, idx) => (
            <InteractiveTable
              key={`meta-table-${idx}`}
              data={table}
            />
          ))}
        </div>
      ) : (
        <pre className="bg-gray-100 dark:bg-gray-800 p-4 rounded-lg overflow-x-auto">
          <code className="text-sm">{content}</code>
        </pre>
      )}
    </div>
  );
}
