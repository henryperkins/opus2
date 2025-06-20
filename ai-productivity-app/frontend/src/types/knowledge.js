// types/knowledge.js

// Knowledge Source interface
export const KnowledgeSourceType = {
  DOCUMENT: 'document',
  CODE: 'code',
  COMMENT: 'comment',
  EXTERNAL: 'external'
};

// Code Chunk types
export const CodeChunkType = {
  FUNCTION: 'function',
  CLASS: 'class',
  IMPORT: 'import',
  EXPORT: 'export',
  OTHER: 'other'
};

// Search types
export const SearchType = {
  ALL: 'all',
  CODE: 'code',
  DOCS: 'docs',
  COMMENTS: 'comments'
};

// Citation source types
export const CitationSourceType = {
  CODE: 'code',
  DOCUMENT: 'document',
  EXTERNAL: 'external'
};

// Helper functions for type validation
export const validateKnowledgeSource = (obj) => {
  return obj && 
    typeof obj.id === 'string' &&
    typeof obj.projectId === 'string' &&
    Object.values(KnowledgeSourceType).includes(obj.type) &&
    typeof obj.title === 'string' &&
    typeof obj.path === 'string' &&
    typeof obj.content === 'string' &&
    typeof obj.metadata === 'object' &&
    typeof obj.createdAt === 'string' &&
    typeof obj.updatedAt === 'string';
};

export const validateCodeDocument = (obj) => {
  return obj &&
    typeof obj.id === 'string' &&
    typeof obj.projectId === 'string' &&
    typeof obj.file_path === 'string' &&
    typeof obj.language === 'string' &&
    typeof obj.content === 'string' &&
    Array.isArray(obj.chunks) &&
    typeof obj.lastAnalyzed === 'string';
};

export const validateCodeChunk = (obj) => {
  return obj &&
    typeof obj.id === 'string' &&
    typeof obj.documentId === 'string' &&
    typeof obj.content === 'string' &&
    typeof obj.start_line === 'number' &&
    typeof obj.end_line === 'number' &&
    Object.values(CodeChunkType).includes(obj.type);
};

export const validateSearchOptions = (obj) => {
  return obj &&
    typeof obj.query === 'string' &&
    (!obj.type || Object.values(SearchType).includes(obj.type)) &&
    (!obj.language || typeof obj.language === 'string') &&
    (!obj.limit || typeof obj.limit === 'number') &&
    (!obj.threshold || typeof obj.threshold === 'number');
};

// Factory functions for creating objects
export const createKnowledgeSource = (data) => ({
  id: data.id || '',
  projectId: data.projectId || '',
  type: data.type || KnowledgeSourceType.DOCUMENT,
  title: data.title || '',
  path: data.path || '',
  content: data.content || '',
  metadata: {
    author: data.metadata?.author,
    lastModified: data.metadata?.lastModified,
    language: data.metadata?.language,
    tags: data.metadata?.tags || [],
    version: data.metadata?.version,
    ...data.metadata
  },
  embedding: data.embedding,
  createdAt: data.createdAt || new Date().toISOString(),
  updatedAt: data.updatedAt || new Date().toISOString()
});

export const createCodeDocument = (data) => ({
  id: data.id || '',
  projectId: data.projectId || '',
  file_path: data.file_path || '',
  language: data.language || '',
  content: data.content || '',
  chunks: data.chunks || [],
  dependencies: data.dependencies,
  exports: data.exports,
  lastAnalyzed: data.lastAnalyzed || new Date().toISOString()
});

export const createCodeChunk = (data) => ({
  id: data.id || '',
  documentId: data.documentId || '',
  content: data.content || '',
  start_line: data.start_line || 0,
  end_line: data.end_line || 0,
  type: data.type || CodeChunkType.OTHER,
  name: data.name,
  embedding: data.embedding,
  score: data.score
});

export const createSearchOptions = (data) => ({
  query: data.query || '',
  type: data.type || SearchType.ALL,
  language: data.language,
  limit: data.limit || 10,
  threshold: data.threshold || 0.5,
  dateRange: data.dateRange
});

export const createCitation = (data) => ({
  id: data.id || '',
  number: data.number || 1,
  source: {
    title: data.source?.title || '',
    path: data.source?.path || '',
    type: data.source?.type || CitationSourceType.DOCUMENT,
    author: data.source?.author,
    lastModified: data.source?.lastModified,
    ...data.source
  },
  content: data.content || '',
  confidence: data.confidence || 0,
  context: data.context
});