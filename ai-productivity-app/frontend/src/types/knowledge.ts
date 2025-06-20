// types/knowledge.ts
export interface KnowledgeSource {
  id: string;
  projectId: string;
  type: 'document' | 'code' | 'comment' | 'external';
  title: string;
  path: string;
  content: string;
  metadata: {
    author?: string;
    lastModified?: string;
    language?: string;
    tags?: string[];
    version?: string;
  };
  embedding?: number[];
  createdAt: string;
  updatedAt: string;
}

export interface CodeDocument {
  id: string;
  projectId: string;
  file_path: string;
  language: string;
  content: string;
  chunks: CodeChunk[];
  dependencies?: string[];
  exports?: string[];
  lastAnalyzed: string;
}

export interface CodeChunk {
  id: string;
  documentId: string;
  content: string;
  start_line: number;
  end_line: number;
  type: 'function' | 'class' | 'import' | 'export' | 'other';
  name?: string;
  embedding?: number[];
  score?: number;
}

export interface DocumentMatch {
  id: string;
  title: string;
  path: string;
  content: string;
  type: 'document' | 'code' | 'comment';
  score: number;
  highlights: string[];
  metadata?: Record<string, any>;
}

export interface SearchOptions {
  query: string;
  type?: 'all' | 'code' | 'docs' | 'comments';
  language?: string;
  limit?: number;
  threshold?: number;
  dateRange?: {
    start: Date;
    end: Date;
  };
}

export interface SearchResults {
  results: DocumentMatch[];
  total: number;
  searchTime: number;
  facets?: {
    types: Record<string, number>;
    languages: Record<string, number>;
    authors: Record<string, number>;
  };
}

export interface KnowledgeContext {
  relevantDocs: DocumentMatch[];
  codeSnippets: CodeChunk[];
  totalMatches: number;
  searchTime: number;
  confidence: number;
}

export interface Citation {
  id: string;
  number: number;
  source: {
    title: string;
    path: string;
    type: 'code' | 'document' | 'external';
    author?: string;
    lastModified?: string;
  };
  content: string;
  confidence: number;
  context?: {
    before: string;
    after: string;
  };
}
