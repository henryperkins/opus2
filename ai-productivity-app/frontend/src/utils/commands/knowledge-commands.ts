// commands/knowledge-commands.ts
import { searchAPI } from '../api/search';
import { CodeDocument, DocumentMatch } from '../types/knowledge';

interface CommandContext {
  projectId: string;
  currentFile?: string;
  selectedText?: string;
  editorContent?: string;
  userId: string;
}

interface CommandResult {
  success: boolean;
  message?: string;
  data?: any;
  citations?: Citation[];
  requiresLLM?: boolean;
  prompt?: string;
}

interface Citation {
  id: string;
  number: number;
  source: {
    title: string;
    path: string;
    type: 'code' | 'document' | 'external';
  };
  content: string;
  confidence: number;
}

export class KnowledgeCommand {
  constructor(
    public name: string,
    public description: string,
    public usage: string,
    public aliases: string[] = []
  ) {}

  async execute(args: string, context: CommandContext): Promise<CommandResult> {
    throw new Error('Execute method must be implemented');
  }

  parseArgs(args: string): Record<string, any> {
    const flags: Record<string, any> = {};
    const positional: string[] = [];

    const parts = args.match(/(?:[^\s"]+|"[^"]*")+/g) || [];

    for (const part of parts) {
      if (part.startsWith('--')) {
        const [key, value] = part.substring(2).split('=');
        flags[key] = value || true;
      } else {
        positional.push(part.replace(/^"|"$/g, ''));
      }
    }

    return { flags, positional };
  }
}

export class FindSimilarCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/find-similar',
      'Find similar code or documents in knowledge base',
      '/find-similar [--type=code|docs] [--limit=5] [--threshold=0.7]',
      ['/similar', '/fs']
    );
  }

  async execute(args: string, context: CommandContext): Promise<CommandResult> {
    const { flags } = this.parseArgs(args);
    const type = flags.type || 'all';
    const limit = parseInt(flags.limit) || 5;
    const threshold = parseFloat(flags.threshold) || 0.7;

    // Use selected text or current file content
    const searchContent = context.selectedText || context.editorContent;

    if (!searchContent) {
      return {
        success: false,
        message: 'No content selected. Please select text or have content in the editor.'
      };
    }

    try {
      const results = await searchAPI.findSimilar(context.projectId, {
        content: searchContent.slice(0, 500), // Limit content size
        type,
        limit,
        threshold
      });

      if (results.items.length === 0) {
        return {
          success: true,
          message: 'No similar content found in the knowledge base.'
        };
      }

      // Format results with citations
      const citations: Citation[] = results.items.map((item, index) => ({
        id: item.id,
        number: index + 1,
        source: {
          title: item.title || item.file_path,
          path: item.file_path,
          type: item.type as 'code' | 'document'
        },
        content: item.content.slice(0, 200),
        confidence: item.score
      }));

      const message = this.formatResults(results.items, citations);

      return {
        success: true,
        message,
        data: results,
        citations
      };
    } catch (error) {
      return {
        success: false,
        message: `Error searching knowledge base: ${error.message}`
      };
    }
  }

  private formatResults(items: any[], citations: Citation[]): string {
    const lines = [`Found ${items.length} similar items:\n`];

    items.forEach((item, index) => {
      lines.push(`[${index + 1}] **${item.title || item.file_path}** (${Math.round(item.score * 100)}% match)`);
      lines.push(`   Path: ${item.file_path}`);
      lines.push(`   Preview: ${item.content.slice(0, 100)}...`);
      lines.push('');
    });

    return lines.join('\n');
  }
}

export class CitationCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/cite',
      'Add citations from knowledge base to your response',
      '/cite "search query" [--format=inline|footnote] [--limit=3]',
      ['/citation', '/ref']
    );
  }

  async execute(args: string, context: CommandContext): Promise<CommandResult> {
    const { flags, positional } = this.parseArgs(args);
    const query = positional.join(' ');
    const format = flags.format || 'inline';
    const limit = parseInt(flags.limit) || 3;

    if (!query) {
      return {
        success: false,
        message: 'Please provide a search query for citations.'
      };
    }

    try {
      const results = await searchAPI.searchDocuments(context.projectId, {
        query,
        limit,
        threshold: 0.6
      });

      if (results.results.length === 0) {
        return {
          success: true,
          message: 'No relevant citations found for your query.'
        };
      }

      const citations: Citation[] = results.results.map((doc, index) => ({
        id: doc.id,
        number: index + 1,
        source: {
          title: doc.title,
          path: doc.path,
          type: 'document' as const
        },
        content: doc.highlights[0] || doc.content.slice(0, 200),
        confidence: doc.score
      }));

      const formattedCitations = format === 'inline'
        ? this.formatInlineCitations(citations)
        : this.formatFootnoteCitations(citations);

      return {
        success: true,
        message: formattedCitations,
        citations,
        data: { format, results: results.results }
      };
    } catch (error) {
      return {
        success: false,
        message: `Error fetching citations: ${error.message}`
      };
    }
  }

  private formatInlineCitations(citations: Citation[]): string {
    const lines = ['Here are the relevant citations:\n'];

    citations.forEach(cite => {
      lines.push(`• "${cite.content}" [${cite.number}]`);
    });

    lines.push('\n**References:**');
    citations.forEach(cite => {
      lines.push(`[${cite.number}] ${cite.source.title} - ${cite.source.path}`);
    });

    return lines.join('\n');
  }

  private formatFootnoteCitations(citations: Citation[]): string {
    const lines = ['**Citations:**\n'];

    citations.forEach(cite => {
      lines.push(`[${cite.number}] **${cite.source.title}**`);
      lines.push(`    Path: ${cite.source.path}`);
      lines.push(`    Quote: "${cite.content}"`);
      lines.push(`    Confidence: ${Math.round(cite.confidence * 100)}%`);
      lines.push('');
    });

    return lines.join('\n');
  }
}

export class CrossReferenceCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/cross-reference',
      'Find related documentation and code for a topic',
      '/cross-reference <topic> [--depth=2] [--include-deps]',
      ['/xref', '/related']
    );
  }

  async execute(args: string, context: CommandContext): Promise<CommandResult> {
    const { flags, positional } = this.parseArgs(args);
    const topic = positional.join(' ');
    const depth = parseInt(flags.depth) || 2;
    const includeDeps = flags['include-deps'] || false;

    if (!topic) {
      return {
        success: false,
        message: 'Please provide a topic to cross-reference.'
      };
    }

    try {
      // Search for initial matches
      const [docs, code] = await Promise.all([
        searchAPI.searchDocuments(context.projectId, { query: topic, limit: 5 }),
        searchAPI.searchCode(context.projectId, { query: topic, limit: 5 })
      ]);

      // Build relationship graph
      const references = await this.buildReferenceGraph(
        docs.results,
        code.results,
        depth,
        includeDeps,
        context.projectId
      );

      const citations = this.createCitationsFromReferences(references);

      return {
        success: true,
        message: this.formatCrossReferences(references, topic),
        citations,
        data: references
      };
    } catch (error) {
      return {
        success: false,
        message: `Error building cross-references: ${error.message}`
      };
    }
  }

  private async buildReferenceGraph(
    docs: any[],
    code: any[],
    depth: number,
    includeDeps: boolean,
    projectId: string
  ): Promise<any[]> {
    // Simplified reference building - in production, this would be more sophisticated
    const references = [];

    // Add direct matches
    references.push(...docs.map(d => ({ ...d, type: 'document', level: 0 })));
    references.push(...code.map(c => ({ ...c, type: 'code', level: 0 })));

    // Find related items (simplified)
    if (depth > 1) {
      for (const item of [...docs, ...code].slice(0, 3)) {
        const related = await searchAPI.findSimilar(projectId, {
          content: item.content.slice(0, 200),
          limit: 2,
          threshold: 0.6
        });

        references.push(...related.items.map(r => ({ ...r, level: 1, parent: item.id })));
      }
    }

    return references;
  }

  private createCitationsFromReferences(references: any[]): Citation[] {
    return references.slice(0, 10).map((ref, index) => ({
      id: ref.id,
      number: index + 1,
      source: {
        title: ref.title || ref.file_path,
        path: ref.file_path || ref.path,
        type: ref.type
      },
      content: ref.content.slice(0, 200),
      confidence: ref.score || 0.8
    }));
  }

  private formatCrossReferences(references: any[], topic: string): string {
    const lines = [`## Cross-references for "${topic}"\n`];

    const byLevel = references.reduce((acc, ref) => {
      const level = ref.level || 0;
      if (!acc[level]) acc[level] = [];
      acc[level].push(ref);
      return acc;
    }, {});

    Object.entries(byLevel).forEach(([level, refs]: [string, any[]]) => {
      lines.push(`\n### ${level === '0' ? 'Direct matches' : `Related (level ${level})`}`);

      refs.forEach((ref, idx) => {
        lines.push(`${idx + 1}. **${ref.title || ref.file_path}**`);
        lines.push(`   Type: ${ref.type} | Score: ${Math.round((ref.score || 0.8) * 100)}%`);
        lines.push(`   ${ref.content.slice(0, 100)}...`);
      });
    });

    return lines.join('\n');
  }
}

export class KnowledgeSummaryCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/knowledge-summary',
      'Summarize relevant knowledge base content',
      '/knowledge-summary <topic> [--max-items=10] [--include-stats]',
      ['/ks', '/summary']
    );
  }

  async execute(args: string, context: CommandContext): Promise<CommandResult> {
    const { flags, positional } = this.parseArgs(args);
    const topic = positional.join(' ') || context.selectedText;
    const maxItems = parseInt(flags['max-items']) || 10;
    const includeStats = flags['include-stats'] || false;

    if (!topic) {
      return {
        success: false,
        message: 'Please provide a topic or select text to summarize knowledge about.'
      };
    }

    try {
      const results = await searchAPI.hybridSearch(context.projectId, {
        query: topic,
        limit: maxItems
      });

      const prompt = this.buildSummaryPrompt(topic, results.results, includeStats);
      const citations = this.createCitationsFromResults(results.results);

      return {
        success: true,
        message: 'Knowledge summary prepared. Processing with AI...',
        requiresLLM: true,
        prompt,
        citations,
        data: { topic, results: results.results }
      };
    } catch (error) {
      return {
        success: false,
        message: `Error creating knowledge summary: ${error.message}`
      };
    }
  }

  private buildSummaryPrompt(topic: string, results: any[], includeStats: boolean): string {
    const lines = [
      `Create a comprehensive summary about "${topic}" based on the following knowledge base content:\n`
    ];

    results.forEach((result, idx) => {
      lines.push(`[${idx + 1}] ${result.title || result.file_path}`);
      lines.push(`Content: ${result.content.slice(0, 300)}...`);
      lines.push('---');
    });

    lines.push('\nPlease provide:');
    lines.push('1. A concise overview of the topic');
    lines.push('2. Key points from the knowledge base');
    lines.push('3. Relationships between different pieces of information');

    if (includeStats) {
      lines.push('4. Statistics about coverage and confidence levels');
    }

    return lines.join('\n');
  }

  private createCitationsFromResults(results: any[]): Citation[] {
    return results.map((result, index) => ({
      id: result.id,
      number: index + 1,
      source: {
        title: result.title || result.file_path,
        path: result.file_path || result.path,
        type: result.type || 'document'
      },
      content: result.content.slice(0, 200),
      confidence: result.score || 0.8
    }));
  }
}

// Command Registry
export class KnowledgeCommandRegistry {
  private commands: Map<string, KnowledgeCommand> = new Map();

  constructor() {
    this.registerDefaultCommands();
  }

  private registerDefaultCommands() {
    const defaultCommands = [
      new FindSimilarCommand(),
      new CitationCommand(),
      new CrossReferenceCommand(),
      new KnowledgeSummaryCommand()
    ];

    defaultCommands.forEach(cmd => {
      this.register(cmd);
    });
  }

  register(command: KnowledgeCommand) {
    this.commands.set(command.name, command);
    command.aliases.forEach(alias => {
      this.commands.set(alias, command);
    });
  }

  get(commandName: string): KnowledgeCommand | undefined {
    return this.commands.get(commandName);
  }

  getAll(): KnowledgeCommand[] {
    const unique = new Map<string, KnowledgeCommand>();
    this.commands.forEach(cmd => {
      unique.set(cmd.name, cmd);
    });
    return Array.from(unique.values());
  }

  async execute(commandLine: string, context: CommandContext): Promise<CommandResult> {
    const [commandName, ...argParts] = commandLine.trim().split(/\s+/);
    const args = argParts.join(' ');

    const command = this.get(commandName);
    if (!command) {
      return {
        success: false,
        message: `Unknown command: ${commandName}. Available commands: ${this.getAll().map(c => c.name).join(', ')}`
      };
    }

    return command.execute(args, context);
  }
}
