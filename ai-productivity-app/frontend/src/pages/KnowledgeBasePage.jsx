/* KnowledgeBasePage.jsx – CRUD browser for project knowledge entries
 *
 * Minimal first version: fetch list of entries and render table.  
 * Later iterations will add create/edit modal, search, pagination.
 */

import React, { useState, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import useSWR from 'swr';
import { ChevronRight, Search, Filter, Download, Upload, GitBranch, FileText, MessageSquare, ExternalLink, Copy, Plus, X, RotateCcw } from 'lucide-react';
import knowledgeAPI from '../api/knowledge';
import { useKnowledgeChat } from '../hooks/useKnowledgeContext';
import { copyToClipboard } from '../utils/clipboard';

import SkeletonLines from '../components/common/SkeletonLines';
import ErrorBanner from '../components/common/ErrorBanner';
import Badge from '../components/common/Badge';

export default function KnowledgeBasePage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFilter, setSelectedFilter] = useState('all');
  const [reRankMode, setReRankMode] = useState(false);
  const [contextBasket, setContextBasket] = useState([]);
  const [showBasket, setShowBasket] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  
  const { addToCitations } = useKnowledgeChat(projectId);
  
  const searchKey = searchQuery || '*';
  const { data: entries = [], error, isLoading, mutate } = useSWR(
    projectId ? ['kb', projectId, searchKey, selectedFilter, reRankMode] : null,
    ([, id, query, filter, reRank]) => {
      const options = {
        limit: 100,
        reRank,
        ...(filter !== 'all' && { source_type: filter })
      };
      return knowledgeAPI.semanticSearch(id, query, options);
    },
    {
      suspense: false,
      revalidateOnFocus: false,
      fallbackData: [],
    },
  );
  
  const { data: projectStats } = useSWR(
    projectId ? ['kb-stats', projectId] : null,
    ([, id]) => knowledgeAPI.getKnowledgeStats(id),
    {
      suspense: false,
      revalidateOnFocus: false,
    },
  );
  
  const { data: projectSummary } = useSWR(
    projectId ? ['kb-summary', projectId] : null,
    ([, id]) => knowledgeAPI.getSummary(id),
    {
      suspense: false,
      revalidateOnFocus: false,
    },
  );

  // Action handlers
  const handleSendToChat = useCallback((entry) => {
    const contextSummary = {
      documents: [{ id: entry.id, title: entry.title, path: entry.source }],
      codeSnippets: [],
      citations: addToCitations([entry])
    };
    navigate(`/projects/${projectId}/chat`, { 
      state: { contextToAdd: contextSummary }
    });
  }, [navigate, projectId, addToCitations]);
  
  const handleCopyCitation = useCallback(async (entry) => {
    const citation = `${entry.title || 'Untitled'}. ${entry.source || 'Unknown source'}. Score: ${entry.score?.toFixed(2) || 'N/A'}.`;
    await copyToClipboard(citation);
  }, []);
  
  const handleOpenSource = useCallback((entry) => {
    if (entry.url) {
      window.open(entry.url, '_blank');
    } else if (entry.source?.startsWith('code:')) {
      const [, filePath, lineRange] = entry.source.match(/code:(.+?)(?::(\d+-\d+))?$/) || [];
      if (filePath) {
        const [startLine] = lineRange?.split('-') || [];
        navigate(`/projects/${projectId}/files?path=${encodeURIComponent(filePath)}${startLine ? `&line=${startLine}` : ''}`);
      }
    }
  }, [navigate, projectId]);
  
  const handleAddToBasket = useCallback((entry) => {
    setContextBasket(prev => {
      if (prev.find(item => item.id === entry.id)) return prev;
      return [...prev, entry];
    });
  }, []);
  
  const handleRemoveFromBasket = useCallback((entryId) => {
    setContextBasket(prev => prev.filter(item => item.id !== entryId));
  }, []);
  
  const handleInjectContext = useCallback(() => {
    const contextSummary = {
      documents: contextBasket.map(item => ({ id: item.id, title: item.title, path: item.source })),
      codeSnippets: [],
      citations: addToCitations(contextBasket)
    };
    navigate(`/projects/${projectId}/chat`, { 
      state: { contextToAdd: contextSummary }
    });
    setContextBasket([]);
    setShowBasket(false);
  }, [contextBasket, navigate, projectId, addToCitations]);
  
  const filteredEntries = entries.filter(entry => {
    if (selectedFilter === 'all') return true;
    const source = entry.source?.toLowerCase() || '';
    switch (selectedFilter) {
      case 'docs': return source.includes('doc') || source.includes('md') || source.includes('txt');
      case 'code': return source.includes('code:') || source.includes('.js') || source.includes('.py') || source.includes('.ts');
      case 'git': return source.includes('git') || source.includes('repo');
      case 'manual': return source.includes('manual') || source.includes('user');
      default: return true;
    }
  });

  return (
    <main className="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      {/* Header with Project Switcher */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-2">
          <button
            onClick={() => navigate(`/projects/${projectId}`)}
            className="text-gray-500 hover:text-gray-700 transition-colors"
          >
            Project {projectId}
          </button>
          <ChevronRight className="w-4 h-4 text-gray-400" />
          <h1 className="text-3xl font-bold text-gray-900">Knowledge Base</h1>
        </div>
        
        {/* Search Bar */}
        <div className="flex items-center space-x-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Search knowledge base..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10 pr-4 py-2 w-80 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          
          {/* Context Basket Button */}
          <button
            onClick={() => setShowBasket(true)}
            className="relative p-2 text-gray-500 hover:text-gray-700 transition-colors"
            title="Context Basket"
          >
            <Plus className="w-5 h-5" />
            {contextBasket.length > 0 && (
              <Badge className="absolute -top-2 -right-2 min-w-[1.25rem] h-5">
                {contextBasket.length}
              </Badge>
            )}
          </button>
        </div>
      </div>
      
      {/* Stats Widget */}
      {projectStats?.data && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-4 rounded-lg shadow-sm border">
            <div className="text-2xl font-bold text-blue-600">{projectStats.data.total_entries}</div>
            <div className="text-sm text-gray-500">Total Entries</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border">
            <div className="text-2xl font-bold text-green-600">{projectStats.data.recent_additions}</div>
            <div className="text-sm text-gray-500">Recent Additions</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border">
            <div className="text-2xl font-bold text-purple-600">{(projectStats.data.hit_rate * 100).toFixed(0)}%</div>
            <div className="text-sm text-gray-500">Hit Rate</div>
          </div>
          <div className="bg-white p-4 rounded-lg shadow-sm border">
            <div className="text-2xl font-bold text-orange-600">{projectStats.data.search_volume}</div>
            <div className="text-sm text-gray-500">Search Volume</div>
          </div>
        </div>
      )}
      
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-4">
          {/* Filter Chips */}
          <div className="flex items-center space-x-2">
            <Filter className="w-4 h-4 text-gray-500" />
            {['all', 'docs', 'code', 'git', 'manual'].map(filter => (
              <button
                key={filter}
                onClick={() => setSelectedFilter(filter)}
                className={`px-3 py-1 rounded-full text-sm font-medium transition-colors ${
                  selectedFilter === filter
                    ? 'bg-blue-100 text-blue-800 border border-blue-200'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                }`}
              >
                {filter.charAt(0).toUpperCase() + filter.slice(1)}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex items-center space-x-4">
          {/* Re-ranking Toggle */}
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={reRankMode}
              onChange={(e) => setReRankMode(e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span>Re-ranking</span>
            <RotateCcw className="w-4 h-4 text-gray-400" />
          </label>
          
          {/* Import Button */}
          <button
            onClick={() => setShowImportModal(true)}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium flex items-center space-x-2"
          >
            <Upload className="w-4 h-4" />
            <span>Import</span>
          </button>
        </div>
      </div>

        {isLoading && <SkeletonLines rows={6} />}
        {error && <ErrorBanner>{error.message || String(error)}</ErrorBanner>}

        {filteredEntries.length > 0 && (
          <div className="overflow-x-auto rounded-lg shadow-sm">
            <table className="min-w-full divide-y divide-gray-200 bg-white hidden sm:table">
              <caption className="sr-only">Knowledge entries</caption>
              <thead className="bg-gray-50">
                <tr>
                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Title
                  </th>
                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Source
                  </th>
                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Score
                  </th>
                  <th scope="col" className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Actions
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredEntries.map((e) => (
                  <tr
                    key={e.id || e.entry_id}
                    className="hover:bg-gray-50 transition-colors"
                  >
                    <td className="px-4 py-2 text-sm text-gray-900">
                      <div className="font-medium">{e.title || e.path || '—'}</div>
                      {e.content && (
                        <div className="text-xs text-gray-500 mt-1 line-clamp-2">
                          {e.content.slice(0, 100)}...
                        </div>
                      )}
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                      <Badge variant={e.source?.includes('code:') ? 'blue' : e.source?.includes('git') ? 'green' : 'gray'}>
                        {e.source || e.repo || '—'}
                      </Badge>
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap text-sm text-gray-500">
                      {e.score ? (
                        <span className={`font-medium ${
                          e.score > 0.8 ? 'text-green-600' : e.score > 0.6 ? 'text-yellow-600' : 'text-red-600'
                        }`}>
                          {e.score.toFixed(2)}
                        </span>
                      ) : '—'}
                    </td>
                    <td className="px-4 py-2 whitespace-nowrap text-sm">
                      <div className="flex items-center space-x-2">
                        {/* Open Source */}
                        <button
                          onClick={() => handleOpenSource(e)}
                          className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
                          title="Open Source"
                        >
                          <ExternalLink className="w-4 h-4" />
                        </button>
                        
                        {/* Send to Chat */}
                        <button
                          onClick={() => handleSendToChat(e)}
                          className="p-1 text-gray-400 hover:text-green-600 transition-colors"
                          title="Send to Chat"
                        >
                          <MessageSquare className="w-4 h-4" />
                        </button>
                        
                        {/* Copy Citation */}
                        <button
                          onClick={() => handleCopyCitation(e)}
                          className="p-1 text-gray-400 hover:text-purple-600 transition-colors"
                          title="Copy Citation"
                        >
                          <Copy className="w-4 h-4" />
                        </button>
                        
                        {/* Add to Basket */}
                        <button
                          onClick={() => handleAddToBasket(e)}
                          className="p-1 text-gray-400 hover:text-orange-600 transition-colors"
                          title="Add to Context Basket"
                        >
                          <Plus className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* Mobile cards */}
        {filteredEntries.length > 0 && (
          <div className="sm:hidden space-y-3">
            {filteredEntries.map((e) => (
              <div
                key={e.id || e.entry_id}
                className="card card-hover p-4"
              >
                <div className="flex items-start justify-between mb-2">
                  <h3 className="font-semibold text-gray-900 dark:text-gray-100 flex-1">
                    {e.title || e.path || '—'}
                  </h3>
                  {e.score && (
                    <span className={`text-sm font-medium ml-2 ${
                      e.score > 0.8 ? 'text-green-600' : e.score > 0.6 ? 'text-yellow-600' : 'text-red-600'
                    }`}>
                      {e.score.toFixed(2)}
                    </span>
                  )}
                </div>
                
                <div className="flex items-center justify-between">
                  <Badge variant={e.source?.includes('code:') ? 'blue' : e.source?.includes('git') ? 'green' : 'gray'}>
                    {e.source || e.repo || '—'}
                  </Badge>
                  
                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => handleOpenSource(e)}
                      className="p-1 text-gray-400 hover:text-blue-600 transition-colors"
                      title="Open Source"
                    >
                      <ExternalLink className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={() => handleSendToChat(e)}
                      className="p-1 text-gray-400 hover:text-green-600 transition-colors"
                      title="Send to Chat"
                    >
                      <MessageSquare className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={() => handleCopyCitation(e)}
                      className="p-1 text-gray-400 hover:text-purple-600 transition-colors"
                      title="Copy Citation"
                    >
                      <Copy className="w-4 h-4" />
                    </button>
                    
                    <button
                      onClick={() => handleAddToBasket(e)}
                      className="p-1 text-gray-400 hover:text-orange-600 transition-colors"
                      title="Add to Basket"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                
                {e.content && (
                  <p className="text-sm text-gray-600 mt-2 line-clamp-2">
                    {e.content.slice(0, 150)}...
                  </p>
                )}
              </div>
            ))}
          </div>
        )}

        {!isLoading && filteredEntries.length === 0 && !error && (
          <div className="card card-hover p-8 text-center">
            <div className="max-w-md mx-auto">
              <FileText className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No knowledge entries found</h3>
              <p className="text-gray-500 mb-6">
                {searchQuery 
                  ? 'Try adjusting your search terms or filters'
                  : 'Get started by importing documents, code, or PDFs to build your knowledge base.'
                }
              </p>
              
              {!searchQuery && (
                <div className="flex flex-col sm:flex-row gap-3 justify-center">
                  <button 
                    onClick={() => setShowImportModal(true)}
                    className="flex items-center justify-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    <GitBranch className="w-4 h-4 mr-2" />
                    Import Git Repo
                  </button>
                  <button 
                    onClick={() => setShowImportModal(true)}
                    className="flex items-center justify-center px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
                  >
                    <Upload className="w-4 h-4 mr-2" />
                    Upload Files
                  </button>
                  <button 
                    onClick={() => setShowImportModal(true)}
                    className="flex items-center justify-center px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Upload PDFs
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Context Basket Drawer */}
        {showBasket && (
          <div className="fixed inset-0 z-50 overflow-hidden">
            <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setShowBasket(false)} />
            <div className="fixed right-0 top-0 h-full w-96 bg-white shadow-xl">
              <div className="flex items-center justify-between p-4 border-b">
                <h3 className="text-lg font-semibold">Context Basket</h3>
                <button
                  onClick={() => setShowBasket(false)}
                  className="p-1 text-gray-400 hover:text-gray-600"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-4">
                {contextBasket.length === 0 ? (
                  <div className="text-center text-gray-500 mt-8">
                    <Plus className="w-12 h-12 text-gray-300 mx-auto mb-4" />
                    <p>No items in basket</p>
                    <p className="text-sm mt-1">Add knowledge entries to build context</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {contextBasket.map((item) => (
                      <div key={item.id} className="bg-gray-50 p-3 rounded-lg">
                        <div className="flex items-start justify-between">
                          <div className="flex-1">
                            <h4 className="font-medium text-sm">{item.title || 'Untitled'}</h4>
                            <p className="text-xs text-gray-500 mt-1">{item.source}</p>
                            {item.score && (
                              <span className="text-xs text-blue-600 font-medium">
                                Score: {item.score.toFixed(2)}
                              </span>
                            )}
                          </div>
                          <button
                            onClick={() => handleRemoveFromBasket(item.id)}
                            className="p-1 text-gray-400 hover:text-red-600 ml-2"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
              
              {contextBasket.length > 0 && (
                <div className="p-4 border-t">
                  <button
                    onClick={handleInjectContext}
                    className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
                  >
                    Inject {contextBasket.length} item{contextBasket.length > 1 ? 's' : ''} to Chat
                  </button>
                </div>
              )}
            </div>
          </div>
        )}
        
        {/* Import Modal */}
        {showImportModal && (
          <div className="fixed inset-0 z-50 overflow-hidden">
            <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setShowImportModal(false)} />
            <div className="fixed inset-0 flex items-center justify-center p-4">
              <div className="bg-white rounded-lg shadow-xl max-w-md w-full">
                <div className="flex items-center justify-between p-6 border-b">
                  <h3 className="text-lg font-semibold">Import to Knowledge Base</h3>
                  <button
                    onClick={() => setShowImportModal(false)}
                    className="p-1 text-gray-400 hover:text-gray-600"
                  >
                    <X className="w-5 h-5" />
                  </button>
                </div>
                
                <div className="p-6 space-y-4">
                  <button className="w-full flex items-center justify-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-blue-400 hover:bg-blue-50 transition-colors">
                    <GitBranch className="w-6 h-6 text-gray-400 mr-3" />
                    <div>
                      <div className="font-medium text-gray-900">Import Git Repository</div>
                      <div className="text-sm text-gray-500">Clone and analyze code repository</div>
                    </div>
                  </button>
                  
                  <button className="w-full flex items-center justify-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-green-400 hover:bg-green-50 transition-colors">
                    <Upload className="w-6 h-6 text-gray-400 mr-3" />
                    <div>
                      <div className="font-medium text-gray-900">Upload Files</div>
                      <div className="text-sm text-gray-500">Upload code files, documents, or text</div>
                    </div>
                  </button>
                  
                  <button className="w-full flex items-center justify-center p-4 border-2 border-dashed border-gray-300 rounded-lg hover:border-purple-400 hover:bg-purple-50 transition-colors">
                    <FileText className="w-6 h-6 text-gray-400 mr-3" />
                    <div>
                      <div className="font-medium text-gray-900">Upload PDFs</div>
                      <div className="text-sm text-gray-500">Extract text from PDF documents</div>
                    </div>
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>
  );
}
