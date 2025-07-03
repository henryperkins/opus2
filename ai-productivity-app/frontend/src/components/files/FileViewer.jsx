import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, useSearchParams, useNavigate } from 'react-router-dom';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { 
  ChevronLeft, 
  ChevronRight,
  Search, 
  Copy, 
  ZoomIn, 
  ZoomOut, 
  Smartphone,
  Monitor,
  Eye,
  EyeOff,
  MoreVertical,
  Share,
  Bookmark,
  X,
  ChevronUp,
  ChevronDown,
  Info,
  Hash,
  Download,
  Printer
} from 'lucide-react';
import LoadingSpinner from '../common/LoadingSpinner';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import useTextSelection from '../../hooks/useTextSelection';

// ------------------------------------------------------------
// Small helpers
// ------------------------------------------------------------

function Breadcrumbs({ path, onNavigate }) {
  const parts = path.split('/');
  const assembled = [];
  return (
    <nav className="file-breadcrumbs" aria-label="Breadcrumb">
      {parts.map((part, idx) => {
        assembled.push(part);
        const subPath = assembled.join('/');
        const isLast = idx === parts.length - 1;
        return (
          <span key={idx} className="flex items-center">
            {idx !== 0 && (
              <ChevronRight className="w-3 h-3 text-gray-400 mx-0.5" />
            )}
            {isLast ? (
              <span className="breadcrumb-item font-medium truncate max-w-[8rem]" title={part}>{part}</span>
            ) : (
              <button
                className="breadcrumb-item text-blue-600 hover:underline truncate max-w-[8rem]"
                title={part}
                onClick={() => onNavigate(subPath)}
              >
                {part}
              </button>
            )}
          </span>
        );
      })}
    </nav>
  );
}

export default function FileViewer() {
  const { path } = useParams();
  const [searchParams] = useSearchParams();
  const [fileContent, setFileContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [language, setLanguage] = useState('text');
  
  // Mobile-specific state
  const [fontSize, setFontSize] = useState(14);
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [wrapLines, setWrapLines] = useState(false);
  const [headerCollapsed, setHeaderCollapsed] = useState(false);
  const [showMobileMenu, setShowMobileMenu] = useState(false);
  const [theme, setTheme] = useState('dark');

  // Enhanced features state (Phase 1)
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [currentMatch, setCurrentMatch] = useState(0);
  const [searchCaseSensitive, setSearchCaseSensitive] = useState(false);
  const [searchRegex, setSearchRegex] = useState(false);

  const [gotoLineOpen, setGotoLineOpen] = useState(false);
  const [gotoLineNumber, setGotoLineNumber] = useState('');

  const [showInfo, setShowInfo] = useState(false);

  // New for Phase-2 -------------------------------------------
  const [performanceMode, setPerformanceMode] = useState(false);
  
  const { isMobile } = useMediaQuery();
  const navigate = useNavigate();

  // selection tracking for context-menu
  const { selectionText, position: selectionPos } = useTextSelection();
  const containerRef = useRef(null);
  const syntaxHighlighterRef = useRef(null);

  const targetLine = parseInt(searchParams.get('line')) || 1;
  const decodedPath = decodeURIComponent(path);
  
  // Responsive font size
  const responsiveFontSize = isMobile ? Math.max(fontSize, 12) : fontSize;

  // Initialize mobile-friendly defaults
  useEffect(() => {
    if (isMobile) {
      setFontSize(16);
      setWrapLines(true);
      setHeaderCollapsed(true);
      setTheme('light'); // Better for mobile reading
    }
  }, [isMobile]);

  useEffect(() => {
    const fetchFileContent = async () => {
      try {
        setLoading(true);
        setError(null);
        
        // Import codeAPI dynamically to avoid ESLint restriction
        const { codeAPI } = await import('../../api/code');
        const response = await codeAPI.getFileContent(decodedPath);
        
        const content = response.content || '';
        setFileContent(content);
        setLanguage(response.language || detectLanguage(decodedPath));

        // Performance heuristics
        const large = content.length > 1_000_000 || content.split('\n').length > 10_000;
        setPerformanceMode(large);
        if (large) {
          setShowLineNumbers(false);
        }
      } catch (err) {
        setError(err.response?.data?.detail || err.message || 'Failed to load file');
      } finally {
        setLoading(false);
      }
    };

    fetchFileContent();
  }, [decodedPath]);

  // Scroll to target line after content loads
  useEffect(() => {
    if (!loading && fileContent && targetLine > 1) {
      const timer = setTimeout(() => {
        const lineElement = document.getElementById(`line-${targetLine}`);
        if (lineElement) {
          lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [loading, fileContent, targetLine]);

  const detectLanguage = (filePath) => {
    const ext = filePath.split('.').pop()?.toLowerCase();
    const languageMap = {
      'js': 'javascript',
      'jsx': 'jsx',
      'ts': 'typescript',
      'tsx': 'tsx',
      'py': 'python',
      'java': 'java',
      'cpp': 'cpp',
      'c': 'c',
      'cs': 'csharp',
      'php': 'php',
      'rb': 'ruby',
      'go': 'go',
      'rs': 'rust',
      'swift': 'swift',
      'kt': 'kotlin',
      'scala': 'scala',
      'sh': 'bash',
      'sql': 'sql',
      'json': 'json',
      'xml': 'xml',
      'html': 'html',
      'css': 'css',
      'scss': 'scss',
      'sass': 'sass',
      'less': 'less',
      'md': 'markdown',
      'yaml': 'yaml',
      'yml': 'yaml',
      'toml': 'toml',
      'ini': 'ini',
      'conf': 'ini',
      'dockerfile': 'dockerfile',
    };
    return languageMap[ext] || 'text';
  };

  // compute lines needing highlight (target line & current search match)
  const getHighlightedLines = () => {
    const highlighted = [];
    if (targetLine > 1) highlighted.push(targetLine);
    if (searchResults.length && currentMatch >= 0) {
      highlighted.push(searchResults[currentMatch]?.lineNumber);
    }
    return highlighted;
  };

  // Helper to highlight search matches within line text
  const highlightSearchMatches = (lineText, lineNumber) => {
    if (!searchOpen || !searchText || !searchResults.length) {
      return lineText;
    }

    // Find if this line has matches
    const lineResult = searchResults.find(result => result.lineNumber === lineNumber);
    if (!lineResult) {
      return lineText;
    }

    try {
      let regex;
      if (searchRegex) {
        const flags = searchCaseSensitive ? 'g' : 'gi';
        regex = new RegExp(searchText, flags);
      } else {
        const escaped = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const flags = searchCaseSensitive ? 'g' : 'gi';
        regex = new RegExp(escaped, flags);
      }

      return lineText.replace(regex, (match) => {
        // Determine if this is the current match line
        const isCurrentMatch = searchResults[currentMatch]?.lineNumber === lineNumber;
        const className = isCurrentMatch ? 'search-highlight current' : 'search-highlight';
        return `<span class="${className}">${match}</span>`;
      });
    } catch (error) {
      return lineText;
    }
  };

  // Mobile-specific functions
  const increaseFontSize = () => {
    setFontSize(prev => Math.min(prev + 2, 24));
  };

  const decreaseFontSize = () => {
    setFontSize(prev => Math.max(prev - 2, 10));
  };

  const copyContent = async () => {
    try {
      await navigator.clipboard.writeText(fileContent);
      // Could add toast notification here
    } catch (err) {
      console.warn('Copy failed:', err);
    }
  };

  // Helpers for the inline selection context-menu ---------------------------
  const copySelection = async (text) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.warn('copySelection failed', err);
    }
  };

  const searchFor = (txt) => {
    if (!txt) return;
    setSearchOpen(true);
    setSearchText(txt);
  };

  const shareFile = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: `Code: ${decodedPath}`,
          text: fileContent,
          url: window.location.href
        });
      } catch (err) {
        console.warn('Share failed:', err);
      }
    } else {
      // Fallback to copy link
      await navigator.clipboard.writeText(window.location.href);
    }
  };

  // Download file helper
  const downloadFile = () => {
    const blob = new Blob([fileContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = decodedPath.split('/').pop() || 'file.txt';
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const printFile = () => {
    const printWindow = window.open('', '_blank');
    const fileName = decodedPath.split('/').pop() || 'file.txt';
    
    printWindow.document.write(`
      <!DOCTYPE html>
      <html>
        <head>
          <title>Print: ${fileName}</title>
          <style>
            @media print {
              @page { margin: 1in; }
              body { font-family: 'Courier New', monospace; font-size: 10pt; line-height: 1.2; }
              .print-header { border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
              .print-header h1 { margin: 0; font-size: 14pt; }
              .print-header .meta { font-size: 8pt; color: #666; margin-top: 5px; }
              .line-number { display: inline-block; width: 4em; color: #666; font-size: 9pt; }
              pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; }
              .highlight { background-color: #ffffcc !important; }
            }
            @media screen {
              body { font-family: 'Courier New', monospace; font-size: 12pt; padding: 20px; }
              .print-header { border-bottom: 1px solid #333; padding-bottom: 10px; margin-bottom: 20px; }
              .print-header h1 { margin: 0; font-size: 16pt; }
              .print-header .meta { font-size: 10pt; color: #666; margin-top: 5px; }
              .line-number { display: inline-block; width: 4em; color: #666; font-size: 11pt; }
              pre { margin: 0; white-space: pre-wrap; word-wrap: break-word; }
              .highlight { background-color: #ffffcc; }
            }
          </style>
        </head>
        <body>
          <div class="print-header">
            <h1>${fileName}</h1>
            <div class="meta">
              Path: ${decodedPath}<br>
              Language: ${language}<br>
              Lines: ${fileContent.split('\n').length}<br>
              Printed: ${new Date().toLocaleString()}
            </div>
          </div>
          <pre>${fileContent.split('\n').map((line, i) => 
            `<span class="line-number">${(i + 1).toString().padStart(4, ' ')}</span>${line}`
          ).join('\n')}</pre>
        </body>
      </html>
    `);
    
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => {
      printWindow.print();
      printWindow.close();
    }, 250);
  };

  const toggleLineNumbers = () => {
    setShowLineNumbers(prev => !prev);
  };

  const toggleLineWrap = () => {
    setWrapLines(prev => !prev);
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

  // ---------------------------------------------------------------------
  // Selection floating context-menu component definition
  // ---------------------------------------------------------------------

  const SelectionMenu = () => {
    // Do not show when search/dialogs are open or no text selected
    if (!selectionText || searchOpen || gotoLineOpen) return null;

    // Clamp inside viewport a bit
    const left = Math.min(window.innerWidth - 120, Math.max(60, selectionPos.x));
    const top = Math.max(50, selectionPos.y);

    return (
      <div
        style={{ left, top, transform: 'translate(-50%, -100%)' }}
        className="fixed z-50 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg shadow-lg flex divide-x divide-gray-200 dark:divide-gray-700 select-none"
      >
        <button
          onClick={() => copySelection(selectionText)}
          className="px-3 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Copy
        </button>
        <button
          onClick={() => searchFor(selectionText)}
          className="px-3 py-1.5 text-xs hover:bg-gray-50 dark:hover:bg-gray-700"
        >
          Search
        </button>
      </div>
    );
  };

  // -----------------------
  // File info helper
  // -----------------------
  const getFileInfo = () => {
    const bytes = new Blob([fileContent]).size;
    const kbSizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes || 1) / Math.log(1024));
    const sizeReadable = (bytes / Math.pow(1024, i)).toFixed(2) + ' ' + kbSizes[i];

    return {
      size: sizeReadable,
      lines: fileContent.split('\n').length,
      words: fileContent.split(/\s+/).filter(Boolean).length,
      characters: fileContent.length,
      language,
    };
  };

  // -----------------------
  // Goto line
  // -----------------------
  const jumpToLine = (line) => {
    const el = document.getElementById(`line-${line}`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  // -----------------------
  // Search helpers
  // -----------------------

  const performSearch = (text) => {
    if (!text || !fileContent) {
      setSearchResults([]);
      setCurrentMatch(0);
      return;
    }

    try {
      let regex;
      if (searchRegex) {
        // Use regex as-is if regex mode is enabled
        const flags = searchCaseSensitive ? 'g' : 'gi';
        regex = new RegExp(text, flags);
      } else {
        // Escape special characters for literal search
        const escaped = text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const flags = searchCaseSensitive ? 'g' : 'gi';
        regex = new RegExp(escaped, flags);
      }

      const lines = fileContent.split('\n');
      const matches = [];

      lines.forEach((line, idx) => {
        const lineMatches = [...line.matchAll(regex)];
        if (lineMatches.length > 0) {
          matches.push({ 
            lineNumber: idx + 1,
            matchCount: lineMatches.length,
            matches: lineMatches.map(m => ({ index: m.index, text: m[0] }))
          });
        }
      });

      setSearchResults(matches);
      setCurrentMatch(matches.length ? 0 : -1);

      if (matches.length) jumpToLine(matches[0].lineNumber);
    } catch (error) {
      // Invalid regex - clear results but don't show error to avoid interrupting typing
      if (searchRegex) {
        setSearchResults([]);
        setCurrentMatch(-1);
      }
    }
  };

  const navigateSearch = useCallback((direction) => {
    if (!searchResults.length) return;
    setCurrentMatch((prev) => {
      const len = searchResults.length;
      let idx = prev;
      idx = direction === 'next' ? (idx + 1) % len : (idx - 1 + len) % len;
      jumpToLine(searchResults[idx].lineNumber);
      return idx;
    });
  }, [searchResults]);

  // Run search when text or options change
  useEffect(() => {
    if (searchOpen) {
      performSearch(searchText);
    }
  }, [searchText, searchOpen, fileContent, searchCaseSensitive, searchRegex]);

  // -----------------------
  // Keyboard shortcuts
  // -----------------------
  useEffect(() => {
    const handleKeyDown = (e) => {
      const metaOrCtrl = e.metaKey || e.ctrlKey;

      // Cmd/Ctrl + F => open search
      if (metaOrCtrl && e.key === 'f') {
        e.preventDefault();
        setSearchOpen(true);
        return;
      }

      // Cmd/Ctrl + G => goto line
      if (metaOrCtrl && e.key === 'g') {
        e.preventDefault();
        setGotoLineOpen(true);
        return;
      }

      // Esc closes overlays
      if (e.key === 'Escape') {
        setSearchOpen(false);
        setGotoLineOpen(false);
        setShowMobileMenu(false);
      }

      // Cmd/Ctrl + C with no selection => copy file
      if (metaOrCtrl && e.key === 'c' && !window.getSelection()?.toString()) {
        e.preventDefault();
        copyContent();
      }

      // Search navigation: F3 / Enter navigate next
      if (searchOpen) {
        if (e.key === 'Enter' || e.key === 'F3') {
          e.preventDefault();
          navigateSearch('next');
        }
        if (metaOrCtrl && e.shiftKey && e.key.toLowerCase() === 'g') {
          e.preventDefault();
          navigateSearch('prev');
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [searchOpen, navigateSearch]);

  // Mobile toolbar component
  const MobileToolbar = () => (
    <div className="flex items-center justify-between p-2 bg-gray-50 border-b border-gray-200 lg:hidden">
      <div className="flex items-center space-x-2">
        <button
          onClick={decreaseFontSize}
          className="p-2 bg-white rounded-lg border border-gray-300 touch-manipulation"
          disabled={fontSize <= 10}
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-sm font-medium min-w-[2rem] text-center">
          {fontSize}px
        </span>
        <button
          onClick={increaseFontSize}
          className="p-2 bg-white rounded-lg border border-gray-300 touch-manipulation"
          disabled={fontSize >= 24}
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>
      
      <div className="flex items-center space-x-2">
        {/* Search (mobile) */}
        <button
          onClick={() => setSearchOpen(true)}
          className="p-2 bg-white rounded-lg border border-gray-300 touch-manipulation"
          aria-label="Search"
        >
          <Search className="w-4 h-4" />
        </button>

        <button
          onClick={toggleLineNumbers}
          className={`p-2 rounded-lg border touch-manipulation ${
            showLineNumbers 
              ? 'bg-blue-100 border-blue-300 text-blue-700' 
              : 'bg-white border-gray-300'
          }`}
          title="Toggle line numbers"
        >
          {showLineNumbers ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
        </button>
        
        <button
          onClick={copyContent}
          className="p-2 bg-white rounded-lg border border-gray-300 touch-manipulation"
          title="Copy content"
        >
          <Copy className="w-4 h-4" />
        </button>
        
        <button
          onClick={() => setShowMobileMenu(!showMobileMenu)}
          className="p-2 bg-white rounded-lg border border-gray-300 touch-manipulation"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
      </div>
    </div>
  );

  // Mobile menu component
  const MobileMenu = () => (
    showMobileMenu && (
      <div className="absolute top-full right-2 mt-1 w-48 bg-white rounded-lg shadow-lg border border-gray-200 z-50 lg:hidden">
        <div className="py-2">
          <button
            onClick={() => {
              toggleLineWrap();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between"
          >
            <span>Wrap Lines</span>
            <span className={`text-xs ${wrapLines ? 'text-green-600' : 'text-gray-400'}`}>
              {wrapLines ? 'ON' : 'OFF'}
            </span>
          </button>
          
          <button
            onClick={() => {
              toggleTheme();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center justify-between"
          >
            <span>Theme</span>
            <span className="text-xs text-gray-600 capitalize">{theme}</span>
          </button>
          
          <button
            onClick={() => {
              setGotoLineOpen(true);
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2"
          >
            <Hash className="w-4 h-4" />
            <span>Go to Line</span>
          </button>
          
          <button
            onClick={() => {
              setShowInfo(true);
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2"
          >
            <Info className="w-4 h-4" />
            <span>File Info</span>
          </button>
          
          <hr className="my-1" />
          
          <button
            onClick={() => {
              downloadFile();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Download</span>
          </button>

          <button
            onClick={() => {
              printFile();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2"
          >
            <Printer className="w-4 h-4" />
            <span>Print</span>
          </button>
          
          <button
            onClick={() => {
              shareFile();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2"
          >
            <Share className="w-4 h-4" />
            <span>Share</span>
          </button>
          
          <button
            onClick={() => {
              // Could implement bookmarking
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 flex items-center space-x-2"
          >
            <Bookmark className="w-4 h-4" />
            <span>Bookmark</span>
          </button>
        </div>
      </div>
    )
  );

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner label="Loading file..." showLabel={true} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-md p-4 m-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800">Error loading file</h3>
            <p className="text-sm text-red-700 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`h-full flex flex-col relative ${isMobile ? 'pb-safe' : ''}`}
      onClick={() => showMobileMenu && setShowMobileMenu(false)}
    >
      {/* Search overlay */}
      {searchOpen && (
        <div className="absolute top-0 inset-x-0 z-40 bg-white/90 backdrop-blur dark:bg-gray-900/90 border-b border-gray-200 dark:border-gray-700 p-2 space-y-2">
          <div className="flex items-center space-x-2">
            <input
              autoFocus
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder={searchRegex ? "Search with regex…" : "Search in file…"}
              className="flex-1 px-3 py-2 rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm"
            />
            {searchResults.length > 0 && (
              <span className="text-xs text-gray-600 dark:text-gray-400 select-none">
                {currentMatch + 1}/{searchResults.length}
              </span>
            )}
            <button
              onClick={() => navigateSearch('prev')}
              disabled={!searchResults.length}
              className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40"
              title="Previous match"
            >
              <ChevronUp className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigateSearch('next')}
              disabled={!searchResults.length}
              className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-40"
              title="Next match"
            >
              <ChevronDown className="w-4 h-4" />
            </button>
            <button
              onClick={() => {
                setSearchOpen(false);
                setSearchText('');
                setSearchResults([]);
              }}
              className="p-2 rounded hover:bg-gray-100 dark:hover:bg-gray-700"
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
          <div className="flex items-center space-x-4 text-xs">
            <label className="flex items-center space-x-1 cursor-pointer">
              <input
                type="checkbox"
                checked={searchCaseSensitive}
                onChange={(e) => setSearchCaseSensitive(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-700 dark:text-gray-300">Case sensitive</span>
            </label>
            <label className="flex items-center space-x-1 cursor-pointer">
              <input
                type="checkbox"
                checked={searchRegex}
                onChange={(e) => setSearchRegex(e.target.checked)}
                className="rounded border-gray-300 dark:border-gray-600 text-blue-600 focus:ring-blue-500"
              />
              <span className="text-gray-700 dark:text-gray-300">Regular expression</span>
            </label>
          </div>
        </div>
      )}
      {/* Enhanced Header */}
      <div className={`bg-white border-b border-gray-200 transition-all duration-200 ${
        headerCollapsed && isMobile ? 'px-2 py-2' : 'px-4 py-3'
      }`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 min-w-0 flex-1">
            <button
              onClick={() => window.history.back()}
              className={`flex-shrink-0 p-2 rounded-lg border border-gray-300 bg-white hover:bg-gray-50 touch-manipulation ${
                isMobile ? 'text-gray-600' : 'text-gray-700'
              }`}
            >
              <ChevronLeft className={`${isMobile ? 'w-5 h-5' : 'w-4 h-4'}`} />
            </button>
            
            <div className="min-w-0 flex-1">
              {!headerCollapsed && (
                <Breadcrumbs
                  path={decodedPath}
                  onNavigate={(sub) => navigate(`/viewer/${encodeURIComponent(sub)}`)}
                />
              )}
              {headerCollapsed && isMobile && (
                <span className="text-sm text-gray-600 truncate">
                  {decodedPath.split('/').pop()}
                </span>
              )}
              {targetLine > 1 && !headerCollapsed && (
                <p className="text-sm text-gray-500 mt-1">
                  Showing line {targetLine}
                </p>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2 flex-shrink-0">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800 ${
              isMobile && headerCollapsed ? 'hidden' : ''
            }`}>
              {language}
            </span>
            
            {/* Desktop controls */}
            {!isMobile && (
              <>
                <button
                  onClick={toggleLineNumbers}
                  className={`p-2 rounded-lg border touch-manipulation ${
                    showLineNumbers 
                      ? 'bg-blue-100 border-blue-300 text-blue-700' 
                      : 'bg-white border-gray-300'
                  }`}
                  title="Toggle line numbers"
                >
                  {showLineNumbers ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </button>
                
                <button
                  onClick={copyContent}
                  className="p-2 bg-white rounded-lg border border-gray-300 hover:bg-gray-50"
                  title="Copy content"
                >
                  <Copy className="w-4 h-4" />
                </button>

                <button
                  onClick={() => setShowInfo(true)}
                  className="p-2 bg-white rounded-lg border border-gray-300 hover:bg-gray-50"
                  title="File info"
                >
                  <Info className="w-4 h-4" />
                </button>

                <button
                  onClick={downloadFile}
                  className="p-2 bg-white rounded-lg border border-gray-300 hover:bg-gray-50"
                  title="Download file"
                >
                  <Download className="w-4 h-4" />
                </button>

                <button
                  onClick={printFile}
                  className="p-2 bg-white rounded-lg border border-gray-300 hover:bg-gray-50"
                  title="Print file"
                >
                  <Printer className="w-4 h-4" />
                </button>
              </>
            )}
            
            {/* Mobile header collapse toggle */}
            {isMobile && (
              <button
                onClick={() => setHeaderCollapsed(!headerCollapsed)}
                className="p-2 bg-white rounded-lg border border-gray-300 touch-manipulation"
              >
                {headerCollapsed ? <Monitor className="w-4 h-4" /> : <Smartphone className="w-4 h-4" />}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Mobile Toolbar */}
      <MobileToolbar />
      
      {/* Mobile Menu */}
      <MobileMenu />

      {/* Keyboard hint */}
      {!isMobile && !searchOpen && (
        <div className="absolute bottom-4 right-4 text-xs text-gray-500 dark:text-gray-400 bg-white/80 dark:bg-gray-800/80 backdrop-blur px-3 py-1.5 rounded-md shadow-md select-none">
          Press <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">⌘F</kbd> to search
        </div>
      )}

      {/* Floating selection context menu */}
      <SelectionMenu />

      {/* File Content */}
      <div className={`flex-1 min-h-0 overflow-auto ${
        theme === 'light' ? 'bg-white' : 'bg-gray-900'
      }`}>
        <style>
          {`
            .search-highlight {
              background-color: #fef08a !important;
              padding: 0 2px;
              border-radius: 2px;
            }
            .search-highlight.current {
              background-color: #f59e0b !important;
              color: white;
            }
          `}
        </style>
        <SyntaxHighlighter
          ref={syntaxHighlighterRef}
          language={language}
          style={theme === 'light' ? oneLight : tomorrow}
          showLineNumbers={showLineNumbers}
          wrapLines={wrapLines || isMobile}
          lineNumberStyle={{ 
            minWidth: isMobile ? '2.5em' : '3em',
            paddingRight: '1em',
            color: theme === 'light' ? '#6b7280' : '#9ca3af',
            fontSize: isMobile ? `${Math.max(responsiveFontSize - 2, 10)}px` : `${responsiveFontSize - 2}px`
          }}
          lineProps={(lineNumber) => ({
            style: {
              display: 'block',
              backgroundColor: getHighlightedLines().includes(lineNumber) 
                ? (theme === 'light' ? '#fef3c7' : '#451a03')
                : 'transparent',
              paddingLeft: isMobile ? '0.5rem' : '1rem',
              paddingRight: isMobile ? '0.5rem' : '1rem',
              minHeight: isMobile ? '1.5rem' : 'auto',
            },
            id: `line-${lineNumber}`,
          })}
          customStyle={{
            margin: 0,
            padding: 0,
            fontSize: `${responsiveFontSize}px`,
            lineHeight: isMobile ? '1.4' : '1.5',
            background: 'transparent',
            fontFamily: 'ui-monospace, SFMono-Regular, "SF Mono", Consolas, "Liberation Mono", Menlo, monospace',
          }}
          codeTagProps={{
            style: {
              fontSize: `${responsiveFontSize}px`,
              lineHeight: isMobile ? '1.4' : '1.5',
            }
          }}
          renderer={({ rows, stylesheet, useInlineStyles }) => {
            return rows.map((row, i) => {
              const lineNumber = i + 1;
              let lineContent = row.map((node, j) => {
                if (node.type === 'text') {
                  // Apply search highlighting to text nodes
                  const highlightedText = highlightSearchMatches(node.value, lineNumber);
                  if (highlightedText !== node.value) {
                    return <span key={j} dangerouslySetInnerHTML={{ __html: highlightedText }} />;
                  }
                }
                return <span key={j} style={useInlineStyles ? node.properties.style : undefined} className={node.properties.className}>
                  {node.children ? node.children.map((child, k) => {
                    if (child.type === 'text') {
                      const highlightedText = highlightSearchMatches(child.value, lineNumber);
                      if (highlightedText !== child.value) {
                        return <span key={k} dangerouslySetInnerHTML={{ __html: highlightedText }} />;
                      }
                    }
                    return child.value;
                  }) : node.value}
                </span>;
              });

              return (
                <div key={i} style={{
                  display: 'block',
                  backgroundColor: getHighlightedLines().includes(lineNumber) 
                    ? (theme === 'light' ? '#fef3c7' : '#451a03')
                    : 'transparent',
                  paddingLeft: isMobile ? '0.5rem' : '1rem',
                  paddingRight: isMobile ? '0.5rem' : '1rem',
                  minHeight: isMobile ? '1.5rem' : 'auto',
                }} id={`line-${lineNumber}`}>
                  {lineContent}
                </div>
              );
            });
          }}
        >
          {fileContent}
        </SyntaxHighlighter>
      </div>

      {/* Goto line dialog */}
      {gotoLineOpen && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 p-4" onClick={() => setGotoLineOpen(false)}>
          <div
            className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-sm w-full shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-sm font-medium mb-4 text-gray-900 dark:text-gray-100">Go to line</h2>
            <input
              type="number"
              min={1}
              value={gotoLineNumber}
              onChange={(e) => setGotoLineNumber(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  const line = parseInt(gotoLineNumber, 10);
                  if (line) jumpToLine(line);
                  setGotoLineOpen(false);
                  setGotoLineNumber('');
                }
              }}
              placeholder="Line number"
              className="w-full border border-gray-300 dark:border-gray-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              autoFocus
            />
            <div className="mt-4 flex justify-end space-x-2">
              <button
                onClick={() => {
                  setGotoLineOpen(false);
                  setGotoLineNumber('');
                }}
                className="px-3 py-1.5 text-sm rounded-md bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  const line = parseInt(gotoLineNumber, 10);
                  if (line) jumpToLine(line);
                  setGotoLineOpen(false);
                  setGotoLineNumber('');
                }}
                className="px-3 py-1.5 text-sm rounded-md bg-blue-600 text-white hover:bg-blue-700"
              >
                Go
              </button>
            </div>
          </div>
        </div>
      )}

      {/* File info modal */}
      {showInfo && (
        <div className="fixed inset-0 flex items-center justify-center bg-black/40 z-50 p-4" onClick={() => setShowInfo(false)}>
          <div
            className="bg-white dark:bg-gray-800 rounded-lg p-6 w-full max-w-md shadow-lg"
            onClick={(e) => e.stopPropagation()}
          >
            <h2 className="text-base font-medium text-gray-900 dark:text-gray-100 mb-4 flex items-center space-x-2">
              <Info className="w-5 h-5" />
              <span>File information</span>
            </h2>
            {(() => {
              const info = getFileInfo();
              return (
                <dl className="text-sm divide-y divide-gray-200 dark:divide-gray-700">
                  <div className="flex justify-between py-2">
                    <dt className="text-gray-500 dark:text-gray-400">Path</dt>
                    <dd className="font-mono truncate max-w-[12rem]" title={decodedPath}>{decodedPath}</dd>
                  </div>
                  <div className="flex justify-between py-2">
                    <dt className="text-gray-500 dark:text-gray-400">Size</dt>
                    <dd>{info.size}</dd>
                  </div>
                  <div className="flex justify-between py-2">
                    <dt className="text-gray-500 dark:text-gray-400">Lines</dt>
                    <dd>{info.lines}</dd>
                  </div>
                  <div className="flex justify-between py-2">
                    <dt className="text-gray-500 dark:text-gray-400">Words</dt>
                    <dd>{info.words}</dd>
                  </div>
                  <div className="flex justify-between py-2">
                    <dt className="text-gray-500 dark:text-gray-400">Characters</dt>
                    <dd>{info.characters}</dd>
                  </div>
                  <div className="flex justify-between py-2">
                    <dt className="text-gray-500 dark:text-gray-400">Language</dt>
                    <dd className="capitalize">{info.language}</dd>
                  </div>
                </dl>
              );
            })()}
            <div className="flex justify-end mt-6">
              <button
                onClick={() => setShowInfo(false)}
                className="px-4 py-2 rounded-md bg-blue-600 text-white hover:bg-blue-700 text-sm"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}