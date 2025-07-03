Based on my review of the FileViewer component in `frontend/src/components/files/FileViewer.jsx`, I can see it already has good mobile and desktop support with features like syntax highlighting, theme switching, font size controls, and line wrapping. Here are my recommendations for enhancing the component:

## Summary

I've reviewed the FileViewer component and created a comprehensive enhancement plan. The current component already has good responsive design with mobile-specific features, but there are several areas for improvement:

### Key Enhancements Recommended:

1. **Search Functionality** (High Priority)
   - In-file search with keyboard shortcuts (Cmd/Ctrl+F)
   - Search result navigation with highlighting
   - Match counter showing current position

2. **Navigation Improvements**
   - Go to line feature (Cmd/Ctrl+G)
   - Breadcrumb navigation for file paths
   - Keyboard shortcuts for common actions

3. **File Information Panel**
   - Display file size, line count, word count
   - Show encoding and language information
   - Quick access from toolbar or menu

4. **Enhanced Accessibility**
   - ARIA labels and live regions
   - Better keyboard navigation
   - Screen reader announcements
   - Focus management for modals

5. **Performance Optimizations**
   - Virtual scrolling for large files (10,000+ lines)
   - Lazy syntax highlighting
   - Optimized search for large files

6. **Additional Mobile Features**
   - Swipe gestures for navigation
   - Enhanced touch targets
   - Better modal handling on small screens

### Implementation Strategy:

I've provided **four** artifacts:

1. **Enhancement Plan** – Detailed breakdown of all proposed features
2. **Enhanced FileViewer Component** – Complete implementation with core features
3. **Migration Guide** – Step-by-step approach to implement changes gradually
4. **Enhanced Styles** – CSS additions for new features

The enhanced component maintains backward compatibility while adding search, file info, go-to-line, and improved accessibility. The migration can be done in phases to minimize risk, with a feature flag approach for easy rollback if needed.

### Next Steps:

1. Start with Phase 1 (search functionality) as it provides the most immediate value
2. Test thoroughly on both mobile and desktop browsers
3. Gather user feedback before proceeding to additional phases
4. Monitor performance metrics after deployment

The enhancements focus on improving developer productivity while maintaining the clean, responsive design that already exists in the component.


---

# FileViewer Component Enhancement Plan

## Current Features Analysis

### Already Implemented ✓
- **Mobile-First Design**: Responsive layout with touch-friendly controls
- **Syntax Highlighting**: Support for 30+ languages with light/dark themes
- **Font Controls**: Zoom in/out functionality (10px-24px range)
- **Line Features**: Toggle line numbers, line wrapping, line highlighting
- **Sharing**: Native share API integration for mobile
- **Theme Switching**: Light/dark mode support
- **Mobile Toolbar**: Dedicated mobile UI with collapsible header
- **Error Handling**: Loading states and error boundaries

## Proposed Enhancements

### 1. Search & Navigation (High Priority)
```jsx
// Add search functionality
const [searchOpen, setSearchOpen] = useState(false);
const [searchText, setSearchText] = useState('');
const [searchResults, setSearchResults] = useState([]);
const [currentMatch, setCurrentMatch] = useState(0);

// Search implementation
const performSearch = (text) => {
  if (!text) {
    setSearchResults([]);
    return;
  }
  
  const lines = fileContent.split('\n');
  const results = [];
  
  lines.forEach((line, index) => {
    if (line.toLowerCase().includes(text.toLowerCase())) {
      results.push({
        line: index + 1,
        content: line,
        matches: [...line.matchAll(new RegExp(text, 'gi'))]
      });
    }
  });
  
  setSearchResults(results);
};

// Keyboard shortcut for search
useEffect(() => {
  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
      e.preventDefault();
      setSearchOpen(true);
    }
  };
  
  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, []);
```

### 2. Enhanced Navigation Features
```jsx
// Add breadcrumb navigation
const Breadcrumbs = ({ path }) => {
  const parts = path.split('/');
  
  return (
    <nav className="flex items-center space-x-1 text-sm">
      {parts.map((part, index) => (
        <React.Fragment key={index}>
          {index > 0 && <ChevronRight className="w-4 h-4 text-gray-400" />}
          <button
            onClick={() => navigateToPath(parts.slice(0, index + 1).join('/'))}
            className={`hover:text-blue-600 ${
              index === parts.length - 1 ? 'font-medium' : ''
            }`}
          >
            {part}
          </button>
        </React.Fragment>
      ))}
    </nav>
  );
};

// Goto line functionality
const [gotoLineOpen, setGotoLineOpen] = useState(false);

const gotoLine = (lineNumber) => {
  const element = document.getElementById(`line-${lineNumber}`);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    highlightLine(lineNumber);
  }
};
```

### 3. Performance Optimizations for Large Files
```jsx
// Virtual scrolling for files > 10,000 lines
const LARGE_FILE_THRESHOLD = 10000;
const shouldVirtualize = fileContent.split('\n').length > LARGE_FILE_THRESHOLD;

// Lazy loading with intersection observer
const useLazyHighlighting = (content, language) => {
  const [highlightedSections, setHighlightedSections] = useState(new Map());
  const observerRef = useRef();
  
  useEffect(() => {
    if (!shouldVirtualize) return;
    
    observerRef.current = new IntersectionObserver((entries) => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          const sectionId = entry.target.dataset.sectionId;
          highlightSection(sectionId);
        }
      });
    });
    
    return () => observerRef.current?.disconnect();
  }, [content]);
  
  return highlightedSections;
};
```

### 4. Enhanced Accessibility
```jsx
// ARIA live regions for search results
<div 
  aria-live="polite" 
  aria-atomic="true"
  className="sr-only"
>
  {searchResults.length > 0 
    ? `Found ${searchResults.length} matches for "${searchText}"`
    : searchText ? 'No matches found' : ''
  }
</div>

// Keyboard navigation
const keyboardShortcuts = {
  'Cmd+F': 'Search in file',
  'Cmd+G': 'Go to line',
  'Cmd+L': 'Toggle line numbers',
  'Cmd+W': 'Toggle word wrap',
  'Cmd+D': 'Download file',
  'Cmd+P': 'Print',
  'Escape': 'Close search/dialogs'
};

// Focus management
const trapFocus = (container) => {
  const focusableElements = container.querySelectorAll(
    'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
  );
  const firstElement = focusableElements[0];
  const lastElement = focusableElements[focusableElements.length - 1];
  
  container.addEventListener('keydown', (e) => {
    if (e.key === 'Tab') {
      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault();
        lastElement.focus();
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault();
        firstElement.focus();
      }
    }
  });
};
```

### 5. File Metadata & Info Panel
```jsx
const FileInfoPanel = ({ path, content, language }) => {
  const fileSize = new Blob([content]).size;
  const lineCount = content.split('\n').length;
  const wordCount = content.split(/\s+/).filter(Boolean).length;
  
  return (
    <div className="p-4 bg-gray-50 dark:bg-gray-800 rounded-lg">
      <h3 className="font-medium mb-2">File Information</h3>
      <dl className="space-y-1 text-sm">
        <div className="flex justify-between">
          <dt className="text-gray-500">Size:</dt>
          <dd>{formatBytes(fileSize)}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">Lines:</dt>
          <dd>{lineCount.toLocaleString()}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">Words:</dt>
          <dd>{wordCount.toLocaleString()}</dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-500">Language:</dt>
          <dd>{language}</dd>
        </div>
      </dl>
    </div>
  );
};
```

### 6. Enhanced Mobile Experience
```jsx
// Gesture support
const useSwipeGesture = (onSwipeLeft, onSwipeRight) => {
  const touchStart = useRef({ x: 0, y: 0 });
  
  const handleTouchStart = (e) => {
    touchStart.current = {
      x: e.touches[0].clientX,
      y: e.touches[0].clientY
    };
  };
  
  const handleTouchEnd = (e) => {
    const deltaX = e.changedTouches[0].clientX - touchStart.current.x;
    const deltaY = Math.abs(e.changedTouches[0].clientY - touchStart.current.y);
    
    if (Math.abs(deltaX) > 50 && deltaY < 50) {
      if (deltaX > 0) onSwipeRight?.();
      else onSwipeLeft?.();
    }
  };
  
  return { handleTouchStart, handleTouchEnd };
};

// Pull-to-refresh for mobile
const usePullToRefresh = (onRefresh) => {
  const [isPulling, setIsPulling] = useState(false);
  const startY = useRef(0);
  
  const handleTouchStart = (e) => {
    if (window.scrollY === 0) {
      startY.current = e.touches[0].clientY;
      setIsPulling(true);
    }
  };
  
  const handleTouchMove = (e) => {
    if (!isPulling) return;
    
    const deltaY = e.touches[0].clientY - startY.current;
    if (deltaY > 100) {
      onRefresh();
      setIsPulling(false);
    }
  };
  
  return { handleTouchStart, handleTouchMove };
};
```

### 7. Print Optimization
```jsx
// Print-specific styles
const PrintView = ({ content, language, path }) => {
  return (
    <div className="print-only">
      <style>{`
        @media print {
          .no-print { display: none !important; }
          .print-only { display: block !important; }
          
          pre { 
            page-break-inside: avoid;
            font-size: 10pt;
            line-height: 1.2;
          }
          
          .line-number {
            color: #666;
            font-size: 9pt;
          }
          
          @page {
            margin: 1cm;
            size: A4;
          }
          
          header {
            position: fixed;
            top: 0;
            font-size: 10pt;
            border-bottom: 1px solid #ccc;
          }
        }
      `}</style>
      
      <header className="mb-4">
        <h1>{path}</h1>
        <p className="text-sm text-gray-600">
          Printed on {new Date().toLocaleDateString()}
        </p>
      </header>
      
      <SyntaxHighlighter
        language={language}
        style={oneLight}
        showLineNumbers={true}
        customStyle={{ fontSize: '10pt' }}
      >
        {content}
      </SyntaxHighlighter>
    </div>
  );
};
```

### 8. Selection-Based Features
```jsx
// Text selection actions
const useTextSelection = () => {
  const [selectedText, setSelectedText] = useState('');
  const [selectionRange, setSelectionRange] = useState(null);
  
  const handleSelectionChange = () => {
    const selection = window.getSelection();
    const text = selection.toString();
    
    if (text) {
      setSelectedText(text);
      setSelectionRange({
        start: selection.anchorOffset,
        end: selection.focusOffset
      });
    }
  };
  
  useEffect(() => {
    document.addEventListener('selectionchange', handleSelectionChange);
    return () => document.removeEventListener('selectionchange', handleSelectionChange);
  }, []);
  
  return { selectedText, selectionRange };
};

// Selection context menu
const SelectionMenu = ({ selectedText, position }) => {
  if (!selectedText) return null;
  
  return (
    <div 
      className="absolute bg-white shadow-lg rounded-lg p-1 z-50"
      style={{ top: position.y, left: position.x }}
    >
      <button onClick={() => copySelection(selectedText)}>
        Copy
      </button>
      <button onClick={() => searchFor(selectedText)}>
        Search for "{selectedText}"
      </button>
      <button onClick={() => findSimilar(selectedText)}>
        Find similar
      </button>
    </div>
  );
};
```

## Implementation Priority

1. **Phase 1 (Immediate)**
   - Search functionality with keyboard shortcuts
   - Goto line feature
   - File info panel
   - Enhanced keyboard navigation

2. **Phase 2 (Short-term)**
   - Breadcrumb navigation
   - Selection-based features
   - Print optimization
   - Performance optimizations for large files

3. **Phase 3 (Long-term)**
   - Virtual scrolling
   - Code folding
   - Split view/diff capabilities
   - Minimap for navigation

## Mobile-Specific Considerations

- Maintain touch-friendly controls (minimum 44x44px tap targets)
- Optimize search UI for mobile keyboards
- Implement swipe gestures for navigation
- Ensure smooth scrolling performance
- Consider battery usage for syntax highlighting

## Accessibility Checklist

- [ ] All interactive elements have proper ARIA labels
- [ ] Keyboard navigation works for all features
- [ ] Screen reader announcements for state changes
- [ ] High contrast mode support
- [ ] Focus indicators are visible
- [ ] Reduced motion preferences respected

## Testing Strategy

1. **Performance Testing**
   - Test with files up to 1MB
   - Measure initial render time
   - Monitor memory usage during scrolling
   - Test search performance on large files

2. **Mobile Testing**
   - Test on iOS Safari, Chrome Android
   - Verify touch gestures work correctly
   - Check landscape/portrait transitions
   - Test with various screen sizes

3. **Accessibility Testing**
   - Screen reader testing (NVDA, JAWS, VoiceOver)
   - Keyboard-only navigation
   - Color contrast validation
   - Focus management verification


---

```jsx
import React, { useState, useEffect, useRef, useCallback } from 'react';
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
  Settings,
  X,
  ChevronUp,
  ChevronDown,
  Info,
  Download,
  Hash,
  FileText
} from 'lucide-react';
import LoadingSpinner from '../common/LoadingSpinner';
import { useMediaQuery } from '../../hooks/useMediaQuery';

export default function EnhancedFileViewer() {
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
  
  // New enhanced features state
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchText, setSearchText] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [currentMatch, setCurrentMatch] = useState(0);
  const [showInfo, setShowInfo] = useState(false);
  const [gotoLineOpen, setGotoLineOpen] = useState(false);
  const [gotoLineNumber, setGotoLineNumber] = useState('');
  
  const { isMobile, isTablet } = useMediaQuery();
  const containerRef = useRef(null);
  const syntaxHighlighterRef = useRef(null);
  const searchInputRef = useRef(null);

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
      setTheme('light');
    }
  }, [isMobile]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Search shortcut (Cmd/Ctrl + F)
      if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
        e.preventDefault();
        setSearchOpen(true);
      }
      
      // Goto line shortcut (Cmd/Ctrl + G)
      if ((e.metaKey || e.ctrlKey) && e.key === 'g') {
        e.preventDefault();
        setGotoLineOpen(true);
      }
      
      // Close search/dialogs (Escape)
      if (e.key === 'Escape') {
        setSearchOpen(false);
        setGotoLineOpen(false);
        setShowMobileMenu(false);
      }
      
      // Copy shortcut (Cmd/Ctrl + C) when no text selected
      if ((e.metaKey || e.ctrlKey) && e.key === 'c' && !window.getSelection()?.toString()) {
        e.preventDefault();
        copyContent();
      }
    };
    
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  // Auto-focus search input when opened
  useEffect(() => {
    if (searchOpen && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [searchOpen]);

  useEffect(() => {
    const fetchFileContent = async () => {
      try {
        setLoading(true);
        setError(null);
        
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

  // Search functionality
  const performSearch = useCallback((text) => {
    if (!text || !fileContent) {
      setSearchResults([]);
      setCurrentMatch(0);
      return;
    }
    
    const lines = fileContent.split('\n');
    const results = [];
    const searchRegex = new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
    
    lines.forEach((line, index) => {
      const matches = [...line.matchAll(searchRegex)];
      if (matches.length > 0) {
        results.push({
          lineNumber: index + 1,
          line: line,
          matches: matches.map(m => ({ index: m.index, text: m[0] }))
        });
      }
    });
    
    setSearchResults(results);
    setCurrentMatch(results.length > 0 ? 0 : -1);
    
    // Jump to first result
    if (results.length > 0) {
      jumpToLine(results[0].lineNumber);
    }
  }, [fileContent]);

  useEffect(() => {
    performSearch(searchText);
  }, [searchText, performSearch]);

  const jumpToLine = (lineNumber) => {
    const element = document.getElementById(`line-${lineNumber}`);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
      // Highlight the line temporarily
      element.style.backgroundColor = theme === 'light' ? '#ffeb3b' : '#ffc107';
      setTimeout(() => {
        element.style.backgroundColor = '';
      }, 2000);
    }
  };

  const navigateSearch = (direction) => {
    if (searchResults.length === 0) return;
    
    let newIndex = currentMatch;
    if (direction === 'next') {
      newIndex = (currentMatch + 1) % searchResults.length;
    } else {
      newIndex = currentMatch === 0 ? searchResults.length - 1 : currentMatch - 1;
    }
    
    setCurrentMatch(newIndex);
    jumpToLine(searchResults[newIndex].lineNumber);
  };

  const handleGotoLine = () => {
    const lineNum = parseInt(gotoLineNumber);
    const maxLines = fileContent.split('\n').length;
    
    if (lineNum && lineNum > 0 && lineNum <= maxLines) {
      jumpToLine(lineNum);
      setGotoLineOpen(false);
      setGotoLineNumber('');
    }
  };

  // File info calculations
  const getFileInfo = () => {
    const bytes = new Blob([fileContent]).size;
    const lines = fileContent.split('\n').length;
    const words = fileContent.split(/\s+/).filter(Boolean).length;
    const chars = fileContent.length;
    
    return {
      size: formatBytes(bytes),
      lines: lines.toLocaleString(),
      words: words.toLocaleString(),
      characters: chars.toLocaleString(),
      encoding: 'UTF-8', // Could be detected
      language: language
    };
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

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
    const highlighted = [];
    
    // Highlight target line
    if (targetLine > 1) {
      highlighted.push(targetLine);
    }
    
    // Highlight current search result
    if (searchResults.length > 0 && currentMatch >= 0) {
      highlighted.push(searchResults[currentMatch].lineNumber);
    }
    
    return highlighted;
  };

  const downloadFile = () => {
    const blob = new Blob([fileContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = decodedPath.split('/').pop() || 'file.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
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
      await navigator.clipboard.writeText(window.location.href);
    }
  };

  const toggleLineNumbers = () => setShowLineNumbers(prev => !prev);
  const toggleLineWrap = () => setWrapLines(prev => !prev);
  const toggleTheme = () => setTheme(prev => prev === 'dark' ? 'light' : 'dark');
  const increaseFontSize = () => setFontSize(prev => Math.min(prev + 2, 24));
  const decreaseFontSize = () => setFontSize(prev => Math.max(prev - 2, 10));

  // Enhanced Mobile toolbar component
  const MobileToolbar = () => (
    <div className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 lg:hidden">
      <div className="flex items-center space-x-2">
        <button
          onClick={decreaseFontSize}
          className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-gray-300 dark:border-gray-600 touch-manipulation"
          disabled={fontSize <= 10}
          aria-label="Decrease font size"
        >
          <ZoomOut className="w-4 h-4" />
        </button>
        <span className="text-sm font-medium min-w-[2rem] text-center" aria-live="polite">
          {fontSize}px
        </span>
        <button
          onClick={increaseFontSize}
          className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-gray-300 dark:border-gray-600 touch-manipulation"
          disabled={fontSize >= 24}
          aria-label="Increase font size"
        >
          <ZoomIn className="w-4 h-4" />
        </button>
      </div>
      
      <div className="flex items-center space-x-2">
        <button
          onClick={() => setSearchOpen(true)}
          className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-gray-300 dark:border-gray-600 touch-manipulation"
          aria-label="Search in file"
        >
          <Search className="w-4 h-4" />
        </button>
        
        <button
          onClick={toggleLineNumbers}
          className={`p-2 rounded-lg border touch-manipulation ${
            showLineNumbers 
              ? 'bg-blue-100 dark:bg-blue-900 border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300' 
              : 'bg-white dark:bg-gray-700 border-gray-300 dark:border-gray-600'
          }`}
          aria-label={showLineNumbers ? "Hide line numbers" : "Show line numbers"}
        >
          {showLineNumbers ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
        </button>
        
        <button
          onClick={copyContent}
          className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-gray-300 dark:border-gray-600 touch-manipulation"
          aria-label="Copy file content"
        >
          <Copy className="w-4 h-4" />
        </button>
        
        <button
          onClick={() => setShowMobileMenu(!showMobileMenu)}
          className="p-2 bg-white dark:bg-gray-700 rounded-lg border border-gray-300 dark:border-gray-600 touch-manipulation"
          aria-label="More options"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
      </div>
    </div>
  );

  // Enhanced Mobile menu component
  const MobileMenu = () => (
    showMobileMenu && (
      <div className="absolute top-full right-2 mt-1 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 z-50 lg:hidden">
        <div className="py-2">
          <button
            onClick={() => {
              toggleLineWrap();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between"
          >
            <span>Wrap Lines</span>
            <span className={`text-xs ${wrapLines ? 'text-green-600 dark:text-green-400' : 'text-gray-400'}`}>
              {wrapLines ? 'ON' : 'OFF'}
            </span>
          </button>
          
          <button
            onClick={() => {
              toggleTheme();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center justify-between"
          >
            <span>Theme</span>
            <span className="text-xs text-gray-600 dark:text-gray-400 capitalize">{theme}</span>
          </button>
          
          <button
            onClick={() => {
              setGotoLineOpen(true);
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2"
          >
            <Hash className="w-4 h-4" />
            <span>Go to Line</span>
          </button>
          
          <button
            onClick={() => {
              setShowInfo(true);
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2"
          >
            <Info className="w-4 h-4" />
            <span>File Info</span>
          </button>
          
          <hr className="my-1 border-gray-200 dark:border-gray-700" />
          
          <button
            onClick={() => {
              downloadFile();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2"
          >
            <Download className="w-4 h-4" />
            <span>Download</span>
          </button>
          
          <button
            onClick={() => {
              shareFile();
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2"
          >
            <Share className="w-4 h-4" />
            <span>Share</span>
          </button>
          
          <button
            onClick={() => {
              setShowMobileMenu(false);
            }}
            className="w-full px-4 py-2 text-left text-sm hover:bg-gray-50 dark:hover:bg-gray-700 flex items-center space-x-2"
          >
            <Bookmark className="w-4 h-4" />
            <span>Bookmark</span>
          </button>
        </div>
      </div>
    )
  );

  // Search overlay component
  const SearchOverlay = () => (
    searchOpen && (
      <div className="absolute top-0 left-0 right-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 p-2 z-40 shadow-lg">
        <div className="flex items-center space-x-2">
          <div className="flex-1 relative">
            <input
              ref={searchInputRef}
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder="Search in file..."
              className="w-full px-3 py-2 pr-20 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-800"
              aria-label="Search text"
            />
            {searchResults.length > 0 && (
              <span className="absolute right-3 top-1/2 transform -translate-y-1/2 text-sm text-gray-500">
                {currentMatch + 1}/{searchResults.length}
              </span>
            )}
          </div>
          
          <button
            onClick={() => navigateSearch('prev')}
            className="p-2 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
            disabled={searchResults.length === 0}
            aria-label="Previous match"
          >
            <ChevronUp className="w-4 h-4" />
          </button>
          
          <button
            onClick={() => navigateSearch('next')}
            className="p-2 bg-gray-100 dark:bg-gray-700 rounded hover:bg-gray-200 dark:hover:bg-gray-600"
            disabled={searchResults.length === 0}
            aria-label="Next match"
          >
            <ChevronDown className="w-4 h-4" />
          </button>
          
          <button
            onClick={() => {
              setSearchOpen(false);
              setSearchText('');
              setSearchResults([]);
            }}
            className="p-2 text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
            aria-label="Close search"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
        
        {/* Screen reader announcement */}
        <div aria-live="polite" aria-atomic="true" className="sr-only">
          {searchResults.length > 0 
            ? `Found ${searchResults.length} matches for "${searchText}"`
            : searchText ? 'No matches found' : ''
          }
        </div>
      </div>
    )
  );

  // Goto line dialog
  const GotoLineDialog = () => (
    gotoLineOpen && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-sm">
          <h3 className="text-lg font-medium mb-4">Go to Line</h3>
          <input
            type="number"
            value={gotoLineNumber}
            onChange={(e) => setGotoLineNumber(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleGotoLine()}
            placeholder={`1-${fileContent.split('\n').length}`}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 dark:bg-gray-700"
            autoFocus
          />
          <div className="flex justify-end space-x-2 mt-4">
            <button
              onClick={() => {
                setGotoLineOpen(false);
                setGotoLineNumber('');
              }}
              className="px-4 py-2 text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
            >
              Cancel
            </button>
            <button
              onClick={handleGotoLine}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Go
            </button>
          </div>
        </div>
      </div>
    )
  );

  // File info modal
  const FileInfoModal = () => {
    const info = getFileInfo();
    
    return showInfo && (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md">
          <div className="flex items-start justify-between mb-4">
            <h3 className="text-lg font-medium flex items-center">
              <FileText className="w-5 h-5 mr-2" />
              File Information
            </h3>
            <button
              onClick={() => setShowInfo(false)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-gray-500 dark:text-gray-400">Path:</dt>
              <dd className="text-sm font-mono truncate max-w-xs" title={decodedPath}>
                {decodedPath}
              </dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500 dark:text-gray-400">Size:</dt>
              <dd>{info.size}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500 dark:text-gray-400">Lines:</dt>
              <dd>{info.lines}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500 dark:text-gray-400">Words:</dt>
              <dd>{info.words}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500 dark:text-gray-400">Characters:</dt>
              <dd>{info.characters}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500 dark:text-gray-400">Language:</dt>
              <dd className="capitalize">{info.language}</dd>
            </div>
            <div className="flex justify-between">
              <dt className="text-gray-500 dark:text-gray-400">Encoding:</dt>
              <dd>{info.encoding}</dd>
            </div>
          </dl>
          
          <div className="mt-6 flex justify-end">
            <button
              onClick={() => setShowInfo(false)}
              className="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex justify-center items-center py-12">
        <LoadingSpinner label="Loading file..." showLabel={true} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4 m-4">
        <div className="flex">
          <div className="flex-shrink-0">
            <svg className="h-5 w-5 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-red-800 dark:text-red-200">Error loading file</h3>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div 
      ref={containerRef}
      className={`h-full flex flex-col relative ${isMobile ? 'pb-safe' : ''} ${theme === 'dark' ? 'dark' : ''}`}
      onClick={() => showMobileMenu && setShowMobileMenu(false)}
    >
      {/* Search Overlay */}
      <SearchOverlay />
      
      {/* Enhanced Header */}
      <div className={`bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 transition-all duration-200 ${
        headerCollapsed && isMobile ? 'px-2 py-2' : 'px-4 py-3'
      } ${searchOpen ? 'pt-16' : ''}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3 min-w-0 flex-1">
            <button
              onClick={() => window.history.back()}
              className={`flex-shrink-0 p-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 touch-manipulation ${
                isMobile ? 'text-gray-600' : 'text-gray-700'
              }`}
              aria-label="Go back"
            >
              <ChevronLeft className={`${isMobile ? 'w-5 h-5' : 'w-4 h-4'}`} />
            </button>
            
            <div className="min-w-0 flex-1">
              {!headerCollapsed && (
                <nav aria-label="File path">
                  <h1 className={`font-medium text-gray-900 dark:text-gray-100 truncate ${
                    isMobile ? 'text-base' : 'text-lg'
                  }`}>
                    {decodedPath}
                  </h1>
                </nav>
              )}
              {headerCollapsed && isMobile && (
                <span className="text-sm text-gray-600 dark:text-gray-400 truncate">
                  {decodedPath.split('/').pop()}
                </span>
              )}
              {targetLine > 1 && !headerCollapsed && (
                <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Showing line {targetLine}
                </p>
              )}
            </div>
          </div>
          
          <div className="flex items-center space-x-2 flex-shrink-0">
            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 ${
              isMobile && headerCollapsed ? 'hidden' : ''
            }`}>
              {language}
            </span>
            
            {/* Desktop controls */}
            {!isMobile && (
              <>
                <button
                  onClick={() => setSearchOpen(true)}
                  className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                  title="Search (Cmd/Ctrl + F)"
                >
                  <Search className="w-4 h-4" />
                </button>
                
                <button
                  onClick={() => setGotoLineOpen(true)}
                  className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                  title="Go to line (Cmd/Ctrl + G)"
                >
                  <Hash className="w-4 h-4" />
                </button>
                
                <button
                  onClick={toggleLineNumbers}
                  className={`p-2 rounded-lg border touch-manipulation ${
                    showLineNumbers 
                      ? 'bg-blue-100 dark:bg-blue-900 border-blue-300 dark:border-blue-700 text-blue-700 dark:text-blue-300' 
                      : 'bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600'
                  }`}
                  title="Toggle line numbers"
                >
                  {showLineNumbers ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
                </button>
                
                <button
                  onClick={copyContent}
                  className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                  title="Copy content"
                >
                  <Copy className="w-4 h-4" />
                </button>
                
                <button
                  onClick={() => setShowInfo(true)}
                  className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-50 dark:hover:bg-gray-700"
                  title="File info"
                >
                  <Info className="w-4 h-4" />
                </button>
              </>
            )}
            
            {/* Mobile header collapse toggle */}
            {isMobile && (
              <button
                onClick={() => setHeaderCollapsed(!headerCollapsed)}
                className="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-300 dark:border-gray-600 touch-manipulation"
                aria-label={headerCollapsed ? "Expand header" : "Collapse header"}
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
      
      {/* Modals */}
      <GotoLineDialog />
      <FileInfoModal />
      
      {/* Keyboard shortcuts hint for desktop */}
      {!isMobile && !searchOpen && !gotoLineOpen && (
        <div className="absolute bottom-4 right-4 text-xs text-gray-500 dark:text-gray-400 bg-white dark:bg-gray-800 px-3 py-2 rounded-lg shadow-md">
          Press <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded text-xs">⌘F</kbd> to search
        </div>
      )}
    </div>
  );
}
```

---

# FileViewer Migration & Implementation Guide

## Overview

This guide provides a step-by-step approach to migrate from the current FileViewer component to the enhanced version with minimal disruption.

## Phase 1: Core Enhancements (1-2 days)

### 1.1 Add Search Functionality

First, add the search feature without changing existing functionality:

```jsx
// Add to existing FileViewer.jsx
const [searchOpen, setSearchOpen] = useState(false);
const [searchText, setSearchText] = useState('');
const [searchResults, setSearchResults] = useState([]);
const [currentMatch, setCurrentMatch] = useState(0);

// Add search functionality
const performSearch = useCallback((text) => {
  if (!text || !fileContent) {
    setSearchResults([]);
    return;
  }
  
  const lines = fileContent.split('\n');
  const results = [];
  const searchRegex = new RegExp(text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
  
  lines.forEach((line, index) => {
    const matches = [...line.matchAll(searchRegex)];
    if (matches.length > 0) {
      results.push({
        lineNumber: index + 1,
        line: line,
        matches: matches
      });
    }
  });
  
  setSearchResults(results);
  if (results.length > 0) {
    jumpToLine(results[0].lineNumber);
  }
}, [fileContent]);
```

### 1.2 Add Keyboard Shortcuts

```jsx
// Add keyboard event handler
useEffect(() => {
  const handleKeyDown = (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
      e.preventDefault();
      setSearchOpen(true);
    }
    if (e.key === 'Escape') {
      setSearchOpen(false);
      setShowMobileMenu(false);
    }
  };
  
  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}, []);
```

### 1.3 Add Search UI Component

```jsx
// Add SearchOverlay component inside FileViewer
const SearchOverlay = () => (
  searchOpen && (
    <div className="absolute top-0 left-0 right-0 bg-white dark:bg-gray-900 border-b p-2 z-40">
      <div className="flex items-center space-x-2">
        <input
          type="text"
          value={searchText}
          onChange={(e) => setSearchText(e.target.value)}
          placeholder="Search..."
          className="flex-1 px-3 py-2 border rounded-lg"
          autoFocus
        />
        <button onClick={() => setSearchOpen(false)}>
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  )
);
```

## Phase 2: File Information & Navigation (1 day)

### 2.1 Add File Info Modal

```jsx
const [showInfo, setShowInfo] = useState(false);

const getFileInfo = () => {
  const bytes = new Blob([fileContent]).size;
  const lines = fileContent.split('\n').length;
  const words = fileContent.split(/\s+/).filter(Boolean).length;
  
  return {
    size: formatBytes(bytes),
    lines: lines.toLocaleString(),
    words: words.toLocaleString(),
    language: language
  };
};
```

### 2.2 Add Go to Line Feature

```jsx
const [gotoLineOpen, setGotoLineOpen] = useState(false);
const [gotoLineNumber, setGotoLineNumber] = useState('');

const jumpToLine = (lineNumber) => {
  const element = document.getElementById(`line-${lineNumber}`);
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }
};
```

## Phase 3: Enhanced Mobile Features (1 day)

### 3.1 Update Mobile Toolbar

Add search button to mobile toolbar:

```jsx
<button
  onClick={() => setSearchOpen(true)}
  className="p-2 bg-white rounded-lg border touch-manipulation"
>
  <Search className="w-4 h-4" />
</button>
```

### 3.2 Enhanced Mobile Menu

Add new menu items:

```jsx
<button onClick={() => setGotoLineOpen(true)}>
  <Hash className="w-4 h-4" />
  <span>Go to Line</span>
</button>

<button onClick={() => setShowInfo(true)}>
  <Info className="w-4 h-4" />
  <span>File Info</span>
</button>

<button onClick={downloadFile}>
  <Download className="w-4 h-4" />
  <span>Download</span>
</button>
```

## Testing Checklist

### Functionality Testing
- [ ] Search works correctly on desktop and mobile
- [ ] Keyboard shortcuts function properly
- [ ] Go to line navigates correctly
- [ ] File info displays accurate data
- [ ] Download functionality works
- [ ] All existing features still work

### Mobile Testing
- [ ] Touch targets are at least 44x44px
- [ ] Search UI is mobile-friendly
- [ ] Modals are responsive
- [ ] Performance is acceptable on mobile devices

### Accessibility Testing
- [ ] Keyboard navigation works throughout
- [ ] Screen reader announcements are present
- [ ] Focus management is correct
- [ ] ARIA labels are descriptive

### Performance Testing
- [ ] Test with files up to 500KB
- [ ] Search performance is acceptable
- [ ] Scrolling remains smooth
- [ ] Memory usage is reasonable

## Rollback Plan

If issues arise, the migration can be rolled back by:

1. Keep the original `FileViewer.jsx` as `FileViewer.backup.jsx`
2. Deploy enhanced version as `FileViewerEnhanced.jsx`
3. Use feature flag to toggle between versions:

```jsx
// In FileViewerPage.jsx
import FileViewer from '../components/files/FileViewer';
import FileViewerEnhanced from '../components/files/FileViewerEnhanced';

const useEnhancedViewer = process.env.REACT_APP_USE_ENHANCED_VIEWER === 'true';

export default function FileViewerPage() {
  const Component = useEnhancedViewer ? FileViewerEnhanced : FileViewer;
  
  return (
    <div className="h-screen flex flex-col">
      <Component />
    </div>
  );
}
```

## Monitoring

After deployment, monitor:

1. **Performance Metrics**
   - Initial load time
   - Search response time
   - Memory usage trends

2. **Error Tracking**
   - JavaScript errors
   - Failed file loads
   - Browser compatibility issues

3. **User Feedback**
   - Feature usage analytics
   - User-reported issues
   - Performance complaints

## Future Enhancements

Once the core enhancements are stable, consider:

1. **Virtual Scrolling** - For files with 10,000+ lines
2. **Code Folding** - Collapse/expand code blocks
3. **Multi-file Diff View** - Compare files side-by-side
4. **Minimap Navigation** - Visual file overview
5. **Syntax Error Highlighting** - Basic linting
6. **Custom Themes** - User-defined color schemes

## Configuration

Consider adding user preferences:

```jsx
// Add to user settings
const fileViewerSettings = {
  defaultTheme: 'dark',
  defaultFontSize: 14,
  showLineNumbers: true,
  wrapLines: false,
  searchCaseSensitive: false,
  searchRegex: false
};
```

## Success Metrics

- Search feature used by >50% of users
- File load time remains under 2 seconds
- Mobile usage increases by 20%
- Zero critical bugs in first week
- Positive user feedback on new features

---

```css
/* FileViewer Enhanced Styles - Add to globals.css */

/* ========================================================================
   Enhanced File Viewer Styles
   ======================================================================== */

/* Search Overlay */
.file-search-overlay {
  @apply absolute top-0 left-0 right-0 bg-white dark:bg-gray-900;
  @apply border-b border-gray-200 dark:border-gray-700;
  @apply p-2 z-40 shadow-lg;
  animation: slideDown 0.2s ease-out;
}

@keyframes slideDown {
  from {
    transform: translateY(-100%);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

/* Search Results Counter */
.search-results-counter {
  @apply absolute right-3 top-1/2 transform -translate-y-1/2;
  @apply text-sm text-gray-500 dark:text-gray-400;
  @apply pointer-events-none;
}

/* File Info Modal */
.file-info-modal {
  @apply bg-white dark:bg-gray-800 rounded-lg shadow-xl;
  @apply p-6 w-full max-w-md;
  animation: fadeInScale 0.2s ease-out;
}

@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.95);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

/* Enhanced Line Highlighting */
.line-highlight-search {
  @apply bg-yellow-200 dark:bg-yellow-900/30;
  animation: pulseHighlight 2s ease-out;
}

.line-highlight-target {
  @apply bg-blue-100 dark:bg-blue-900/30;
}

@keyframes pulseHighlight {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.5;
  }
}

/* Go to Line Dialog */
.goto-line-input {
  @apply w-full px-3 py-2;
  @apply border border-gray-300 dark:border-gray-600;
  @apply rounded-lg;
  @apply focus:outline-none focus:ring-2 focus:ring-blue-500;
  @apply dark:bg-gray-700;
}

/* Enhanced Mobile Menu */
.mobile-menu-enhanced {
  @apply absolute top-full right-2 mt-1 w-56;
  @apply bg-white dark:bg-gray-800 rounded-lg shadow-lg;
  @apply border border-gray-200 dark:border-gray-700;
  @apply z-50 lg:hidden;
  animation: fadeIn 0.15s ease-out;
}

.mobile-menu-item {
  @apply w-full px-4 py-2 text-left text-sm;
  @apply hover:bg-gray-50 dark:hover:bg-gray-700;
  @apply flex items-center space-x-2;
  @apply transition-colors;
}

/* Keyboard Shortcut Badge */
.kbd-shortcut {
  @apply inline-block px-1.5 py-0.5;
  @apply bg-gray-200 dark:bg-gray-700;
  @apply text-xs font-mono rounded;
  @apply border border-gray-300 dark:border-gray-600;
  @apply shadow-sm;
}

/* File Path Breadcrumbs */
.file-breadcrumbs {
  @apply flex items-center space-x-1 text-sm;
  @apply overflow-x-auto scrollbar-hide;
}

.breadcrumb-item {
  @apply hover:text-blue-600 dark:hover:text-blue-400;
  @apply transition-colors whitespace-nowrap;
}

.breadcrumb-separator {
  @apply text-gray-400 dark:text-gray-600;
}

/* Performance Mode Indicator */
.performance-mode-badge {
  @apply inline-flex items-center px-2 py-1;
  @apply text-xs font-medium rounded-full;
  @apply bg-amber-100 text-amber-800;
  @apply dark:bg-amber-900/30 dark:text-amber-400;
}

/* Enhanced Toolbar */
.enhanced-toolbar {
  @apply flex items-center justify-between p-2;
  @apply bg-gray-50 dark:bg-gray-800;
  @apply border-b border-gray-200 dark:border-gray-700;
}

.toolbar-group {
  @apply flex items-center space-x-2;
}

.toolbar-button {
  @apply p-2 rounded-lg border;
  @apply bg-white dark:bg-gray-700;
  @apply border-gray-300 dark:border-gray-600;
  @apply hover:bg-gray-50 dark:hover:bg-gray-600;
  @apply touch-manipulation transition-colors;
  @apply disabled:opacity-50 disabled:cursor-not-allowed;
}

.toolbar-button-active {
  @apply bg-blue-100 dark:bg-blue-900;
  @apply border-blue-300 dark:border-blue-700;
  @apply text-blue-700 dark:text-blue-300;
}

/* Search Highlighting in Code */
.search-match {
  @apply bg-yellow-300 dark:bg-yellow-700;
  @apply rounded px-0.5;
  box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.4);
}

/* Accessibility Improvements */
.sr-only-focusable:focus {
  @apply not-sr-only absolute left-2 top-2;
  @apply bg-white dark:bg-gray-800;
  @apply px-4 py-2 rounded-lg shadow-lg;
  @apply text-sm font-medium;
  @apply z-50;
}

/* Print Styles */
@media print {
  .no-print {
    display: none !important;
  }
  
  .file-content {
    font-size: 10pt !important;
    line-height: 1.2 !important;
  }
  
  .line-number {
    color: #666 !important;
    font-size: 9pt !important;
  }
  
  pre {
    page-break-inside: avoid;
  }
  
  @page {
    margin: 1cm;
    size: A4;
  }
}

/* Dark Mode Adjustments */
.dark {
  /* Search overlay */
  .file-search-overlay {
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3);
  }
  
  /* Modals */
  .file-info-modal,
  .goto-line-modal {
    box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.3);
  }
  
  /* Code highlighting */
  .search-match {
    box-shadow: 0 0 0 2px rgba(251, 191, 36, 0.3);
  }
}

/* Responsive Adjustments */
@media (max-width: 768px) {
  /* Mobile-optimized search */
  .file-search-overlay input {
    font-size: 16px; /* Prevent iOS zoom */
  }
  
  /* Touch-friendly modals */
  .modal-backdrop {
    -webkit-tap-highlight-color: transparent;
  }
  
  /* Improved contrast for outdoor use */
  @media (prefers-contrast: high) {
    .search-match {
      @apply bg-yellow-400 dark:bg-yellow-600;
      @apply text-black dark:text-white;
      font-weight: bold;
    }
  }
}

/* Animation Performance */
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* Scrollbar Styling */
.file-content::-webkit-scrollbar {
  width: 12px;
  height: 12px;
}

.file-content::-webkit-scrollbar-track {
  @apply bg-gray-100 dark:bg-gray-800;
}

.file-content::-webkit-scrollbar-thumb {
  @apply bg-gray-400 dark:bg-gray-600;
  @apply rounded-full;
}

.file-content::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-500 dark:bg-gray-500;
}

/* Firefox Scrollbar */
.file-content {
  scrollbar-width: thin;
  scrollbar-color: theme('colors.gray.400') theme('colors.gray.100');
}

.dark .file-content {
  scrollbar-color: theme('colors.gray.600') theme('colors.gray.800');
}
```
