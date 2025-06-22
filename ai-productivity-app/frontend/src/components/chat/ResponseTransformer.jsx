// components/chat/ResponseTransformer.jsx
import React, { useState } from 'react';
import {
  FileText, Code, List, Hash, Globe,
  FileJson, Type, Zap, Download, Copy, Check
} from 'lucide-react';
import { toast } from '../common/Toast';
import { copyToClipboard } from '../../utils/clipboard';

const transformOptions = [
  {
    id: 'markdown',
    name: 'To Markdown',
    description: 'Convert to properly formatted Markdown',
    icon: <FileText className="w-4 h-4" />,
    outputFormat: 'markdown',
    transform: async (content) => {
      // Clean up and format as proper markdown
      return content
        .replace(/^- /gm, '* ') // Convert dashes to asterisks for lists
        .replace(/```(\w*)\n/g, '\n```$1\n') // Fix code block formatting
        .replace(/\n{3,}/g, '\n\n'); // Remove excessive newlines
    }
  },
  {
    id: 'json',
    name: 'Extract JSON',
    description: 'Extract and format JSON data',
    icon: <FileJson className="w-4 h-4" />,
    outputFormat: 'json',
    transform: async (content) => {
      // Extract JSON from content
      const jsonMatch = content.match(/\{[\s\S]*\}|\[[\s\S]*\]/);
      if (jsonMatch) {
        try {
          const json = JSON.parse(jsonMatch[0]);
          return JSON.stringify(json, null, 2);
        } catch {
          throw new Error('Invalid JSON in content');
        }
      }

      // Try to convert content to JSON structure
      const lines = content.split('\n').filter(line => line.trim());
      const data = {};

      lines.forEach(line => {
        const match = line.match(/^([^:]+):\s*(.+)$/);
        if (match) {
          data[match[1].trim()] = match[2].trim();
        }
      });

      return JSON.stringify(data, null, 2);
    }
  },
  {
    id: 'code',
    name: 'Extract Code',
    description: 'Extract all code blocks',
    icon: <Code className="w-4 h-4" />,
    outputFormat: 'code',
    transform: async (content) => {
      const codeBlocks = content.match(/```[\s\S]*?```/g) || [];
      return codeBlocks
        .map(block => block.replace(/```\w*\n?/g, '').trim())
        .join('\n\n---\n\n');
    }
  },
  {
    id: 'list',
    name: 'To List',
    description: 'Convert to bullet points',
    icon: <List className="w-4 h-4" />,
    outputFormat: 'text',
    transform: async (content) => {
      const sentences = content
        .split(/[.!?]+/)
        .map(s => s.trim())
        .filter(s => s.length > 0);

      return sentences.map(s => `• ${s}`).join('\n');
    }
  },
  {
    id: 'summary',
    name: 'Summarize',
    description: 'Extract key points',
    icon: <Zap className="w-4 h-4" />,
    outputFormat: 'text',
    transform: async (content) => {
      // Extract headers and first sentences
      const lines = content.split('\n');
      const keyPoints = [];

      lines.forEach((line, i) => {
        // Headers
        if (line.match(/^#+\s/)) {
          keyPoints.push(line.replace(/^#+\s/, '• '));
        }
        // First sentence after header
        else if (i > 0 && lines[i-1].match(/^#+\s/) && line.trim()) {
          keyPoints.push(`  - ${line.split('.')[0]}.`);
        }
        // Bullet points
        else if (line.match(/^[-*•]\s/)) {
          keyPoints.push(line);
        }
      });

      return keyPoints.length > 0
        ? keyPoints.join('\n')
        : content.split('.').slice(0, 3).join('.') + '.';
    }
  },
  {
    id: 'table',
    name: 'To Table',
    description: 'Convert list data to table',
    icon: <Hash className="w-4 h-4" />,
    outputFormat: 'markdown',
    transform: async (content) => {
      const lines = content.split('\n').filter(line => line.trim());

      // Try to detect key-value pairs
      const rows = [];
      lines.forEach(line => {
        const match = line.match(/^([^:]+):\s*(.+)$/);
        if (match) {
          rows.push([match[1].trim(), match[2].trim()]);
        }
      });

      if (rows.length > 0) {
        const table = [
          '| Key | Value |',
          '|-----|-------|',
          ...rows.map(row => `| ${row[0]} | ${row[1]} |`)
        ];
        return table.join('\n');
      }

      // Fallback: create a simple table
      return '| Item |\n|------|\n' + lines.map(line => `| ${line} |`).join('\n');
    }
  },
  {
    id: 'plain',
    name: 'Plain Text',
    description: 'Remove all formatting',
    icon: <Type className="w-4 h-4" />,
    outputFormat: 'text',
    transform: async (content) => {
      return content
        .replace(/```[\s\S]*?```/g, '') // Remove code blocks
        .replace(/\*\*(.*?)\*\*/g, '$1') // Remove bold
        .replace(/\*(.*?)\*/g, '$1') // Remove italic
        .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1') // Remove links
        .replace(/^#+\s/gm, '') // Remove headers
        .replace(/^[-*]\s/gm, '') // Remove list markers
        .trim();
    }
  },
  {
    id: 'translate',
    name: 'Translate',
    description: 'Translate to another language',
    icon: <Globe className="w-4 h-4" />,
    outputFormat: 'text',
    transform: async (content) => {
      // This would call a translation API
      // For demo, just return a message
      throw new Error('Translation requires API configuration');
    }
  }
];

export default function ResponseTransformer({
  content,
  onTransform,
  allowedTransforms
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [transforming, setTransforming] = useState(null);
  const [copiedFormat, setCopiedFormat] = useState(null);

  const availableOptions = allowedTransforms
    ? transformOptions.filter(opt => allowedTransforms.includes(opt.id))
    : transformOptions;

  const handleTransform = async (option) => {
    setTransforming(option.id);

    try {
      const transformed = await option.transform(content);
      onTransform?.(transformed, option.outputFormat || 'text');
      toast.success(`Transformed to ${option.name}`);
      setIsOpen(false);
    } catch (error) {
      toast.error(error.message || `Failed to transform to ${option.name}`);
    } finally {
      setTransforming(null);
    }
  };

  const handleCopy = async (option) => {
    try {
      const transformed = await option.transform(content);
      const success = await copyToClipboard(transformed);
      if (success) {
        setCopiedFormat(option.id);
        setTimeout(() => setCopiedFormat(null), 2000);
        toast.success(`Copied as ${option.name}`);
      } else {
        toast.error('Failed to copy');
      }
    } catch (error) {
      toast.error('Failed to copy');
    }
  };

  const handleDownload = async (option) => {
    try {
      const transformed = await option.transform(content);
      const blob = new Blob([transformed], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `response.${option.outputFormat || 'txt'}`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      toast.success(`Downloaded as ${option.name}`);
    } catch (error) {
      toast.error('Failed to download');
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="text-sm text-gray-600 hover:text-gray-800 flex items-center space-x-1"
      >
        <Zap className="w-4 h-4" />
        <span>Transform</span>
      </button>

      {isOpen && (
        <div className="absolute bottom-full mb-2 right-0 w-72 bg-white rounded-lg shadow-lg border border-gray-200 p-2 z-50">
          <div className="text-sm font-medium text-gray-700 px-2 py-1 mb-1">
            Transform Response
          </div>

          <div className="space-y-1 max-h-96 overflow-y-auto">
            {availableOptions.map(option => (
              <div
                key={option.id}
                className="flex items-center justify-between p-2 hover:bg-gray-50 rounded group"
              >
                <button
                  onClick={() => handleTransform(option)}
                  disabled={transforming !== null}
                  className="flex-1 flex items-start space-x-3 text-left"
                >
                  <div className="mt-0.5 text-gray-600">
                    {option.icon}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-sm text-gray-900">
                      {option.name}
                    </div>
                    <div className="text-xs text-gray-500">
                      {option.description}
                    </div>
                  </div>
                  {transforming === option.id && (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
                  )}
                </button>

                <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => handleCopy(option)}
                    className="p-1 text-gray-500 hover:text-gray-700"
                    title="Copy transformed"
                  >
                    {copiedFormat === option.id ? (
                      <Check className="w-4 h-4 text-green-600" />
                    ) : (
                      <Copy className="w-4 h-4" />
                    )}
                  </button>
                  <button
                    onClick={() => handleDownload(option)}
                    className="p-1 text-gray-500 hover:text-gray-700"
                    title="Download"
                  >
                    <Download className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
