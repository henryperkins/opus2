import React, { useState, useEffect, useRef } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { tomorrow, oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { 
  ChevronLeft, 
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
  Settings
} from 'lucide-react';
import LoadingSpinner from '../common/LoadingSpinner';
import { useMediaQuery } from '../../hooks/useMediaQuery';

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
  
  const { isMobile, isTablet } = useMediaQuery();
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
        
        setFileContent(response.content || '');
        setLanguage(response.language || detectLanguage(decodedPath));
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

  const getHighlightedLines = () => {
    if (targetLine > 1) {
      return [targetLine];
    }
    return [];
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

  const toggleLineNumbers = () => {
    setShowLineNumbers(prev => !prev);
  };

  const toggleLineWrap = () => {
    setWrapLines(prev => !prev);
  };

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  };

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
          
          <hr className="my-1" />
          
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
                <h1 className={`font-medium text-gray-900 truncate ${
                  isMobile ? 'text-base' : 'text-lg'
                }`}>
                  {decodedPath}
                </h1>
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

      {/* File Content */}
      <div className={`flex-1 min-h-0 overflow-auto ${
        theme === 'light' ? 'bg-white' : 'bg-gray-900'
      }`}>
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
        >
          {fileContent}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}