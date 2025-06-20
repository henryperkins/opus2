// utils/commands/knowledge-commands.js
import { searchAPI } from '../../api/search';

/**
 * Command context interface for knowledge commands
 * @typedef {Object} CommandContext
 * @property {string} projectId - Project ID
 * @property {string} [selectedText] - Currently selected text
 * @property {string} [currentFile] - Current file path
 * @property {Object} [editorContext] - Editor context
 */

/**
 * Command result interface
 * @typedef {Object} CommandResult
 * @property {boolean} success - Whether command succeeded
 * @property {string} message - Result message
 * @property {boolean} [requiresLLM] - Whether result needs LLM processing
 * @property {string} [prompt] - Prompt for LLM
 * @property {Array} [citations] - Associated citations
 * @property {Object} [data] - Additional data
 */

/**
 * Citation interface
 * @typedef {Object} Citation
 * @property {string} id - Citation ID
 * @property {number} number - Citation number
 * @property {Object} source - Source information
 * @property {string} content - Citation content
 * @property {number} confidence - Confidence score
 */

/**
 * Base class for knowledge commands
 */
export class KnowledgeCommand {
  /**
   * @param {string} name - Command name
   * @param {string} description - Command description
   * @param {string} usage - Usage string
   * @param {Array<string>} aliases - Command aliases
   */
  constructor(name, description, usage, aliases = []) {
    this.name = name;
    this.description = description;
    this.usage = usage;
    this.aliases = aliases;
  }

  /**
   * Execute the command
   * @param {string} args - Command arguments
   * @param {CommandContext} context - Command context
   * @returns {Promise<CommandResult>}
   */
  async execute(args, context) {
    // eslint-disable-next-line no-unused-vars
    const _args = args;
    // eslint-disable-next-line no-unused-vars  
    const _context = context;
    throw new Error('Execute method must be implemented');
  }

  /**
   * Parse command arguments
   * @param {string} args - Argument string
   * @returns {Object} Parsed arguments
   */
  parseArgs(args) {
    const flags = {};
    const positional = [];

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

/**
 * Command to find similar content
 */
export class FindSimilarCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/find-similar',
      'Find content similar to the provided text or current selection',
      '/find-similar [text] [--type=all|code|docs] [--limit=10] [--threshold=0.7]',
      ['/similar', '/fs']
    );
  }

  async execute(args, context) {
    const { flags, positional } = this.parseArgs(args);
    const content = positional.join(' ') || context.selectedText;
    const type = flags.type || 'all';
    const limit = parseInt(flags.limit) || 10;
    const threshold = parseFloat(flags.threshold) || 0.7;

    if (!content) {
      return {
        success: false,
        message: 'Please provide text or select text to find similar content.'
      };
    }

    try {
      const results = await searchAPI.findSimilar(context.projectId, {
        content,
        type,
        limit,
        threshold
      });

      if (results.items.length === 0) {
        return {
          success: true,
          message: 'No similar content found with the specified criteria.'
        };
      }

      const citations = this.createCitationsFromResults(results.items);

      return {
        success: true,
        message: `Found ${results.items.length} similar items. See citations for details.`,
        citations,
        data: { similarItems: results.items }
      };
    } catch (error) {
      return {
        success: false,
        message: `Error finding similar content: ${error.message}`
      };
    }
  }

  createCitationsFromResults(results) {
    return results.map((item, index) => ({
      id: item.id,
      number: index + 1,
      source: {
        id: item.id,
        title: item.title || 'Code snippet',
        path: item.path || item.file_path || 'unknown',
        type: item.type || 'document'
      },
      content: item.content.slice(0, 200),
      confidence: item.score || 0.8
    }));
  }
}

/**
 * Command to create citations from search results
 */
export class CitationCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/cite',
      'Create citations from search results or specific documents',
      '/cite <query> [--format=apa|mla|chicago] [--max-items=5]',
      ['/citation', '/ref']
    );
  }

  async execute(args, context) {
    const { flags, positional } = this.parseArgs(args);
    const query = positional.join(' ');
    const format = flags.format || 'apa';
    const maxItems = parseInt(flags['max-items']) || 5;

    if (!query) {
      return {
        success: false,
        message: 'Please provide a search query to create citations.'
      };
    }

    try {
      const results = await searchAPI.hybridSearch(context.projectId, {
        query,
        limit: maxItems
      });

      if (results.results.length === 0) {
        return {
          success: true,
          message: 'No relevant content found for citation.'
        };
      }

      const citations = this.formatCitations(results.results, format);

      return {
        success: true,
        message: `Created ${citations.length} citations in ${format.toUpperCase()} format.`,
        citations,
        data: { formattedCitations: citations.map(c => c.formatted) }
      };
    } catch (error) {
      return {
        success: false,
        message: `Error creating citations: ${error.message}`
      };
    }
  }

  formatCitations(results, format) {
    return results.map((item, index) => {
      const citation = {
        id: item.id,
        number: index + 1,
        source: {
          id: item.id,
          title: item.title || 'Code snippet',
          path: item.path || item.file_path || 'unknown',
          type: item.type || 'document'
        },
        content: item.content.slice(0, 200),
        confidence: item.score || 0.8
      };

      // Add formatted citation based on style
      switch (format.toLowerCase()) {
        case 'apa':
          citation.formatted = `${citation.source.title}. Retrieved from ${citation.source.path}`;
          break;
        case 'mla':
          citation.formatted = `"${citation.source.title}." ${citation.source.path}.`;
          break;
        case 'chicago':
          citation.formatted = `${citation.source.title}, ${citation.source.path}.`;
          break;
        default:
          citation.formatted = `${citation.source.title} (${citation.source.path})`;
      }

      return citation;
    });
  }
}

/**
 * Command to find cross-references in the codebase
 */
export class CrossReferenceCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/xref',
      'Find cross-references and connections between code and documentation',
      '/xref <term> [--include-docs] [--include-code] [--depth=2]',
      ['/cross-ref', '/connections']
    );
  }

  async execute(args, context) {
    const { flags, positional } = this.parseArgs(args);
    const term = positional.join(' ') || context.selectedText;
    const includeDocs = flags['include-docs'] || true;
    const includeCode = flags['include-code'] || true;
    // const depth = parseInt(flags.depth) || 2; // TODO: Implement depth-based search

    if (!term) {
      return {
        success: false,
        message: 'Please provide a term or select text to find cross-references.'
      };
    }

    try {
      const searches = [];

      if (includeDocs) {
        searches.push(
          searchAPI.searchDocuments(context.projectId, {
            query: term,
            limit: 15
          })
        );
      }

      if (includeCode) {
        searches.push(
          searchAPI.searchCode(context.projectId, {
            query: term,
            limit: 15
          })
        );
      }

      const results = await Promise.all(searches);
      const allItems = results.flatMap(r => r.results || []);

      if (allItems.length === 0) {
        return {
          success: true,
          message: 'No cross-references found.'
        };
      }

      const citations = this.createCitationsFromResults(allItems);
      const connections = this.analyzeConnections(allItems, term);

      return {
        success: true,
        message: `Found ${allItems.length} cross-references with ${connections.length} connections.`,
        citations,
        data: { connections, crossReferences: allItems }
      };
    } catch (error) {
      return {
        success: false,
        message: `Error finding cross-references: ${error.message}`
      };
    }
  }

  analyzeConnections(items, term) {
    // Simple connection analysis - could be enhanced
    const connections = [];
    const termLower = term.toLowerCase();

    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        const item1 = items[i];
        const item2 = items[j];

        // Check for common terms, similar paths, or content overlap
        const content1 = (item1.content || '').toLowerCase();
        const content2 = (item2.content || '').toLowerCase();

        if (content1.includes(termLower) && content2.includes(termLower)) {
          connections.push({
            from: item1.id,
            to: item2.id,
            type: 'term_reference',
            strength: this.calculateConnectionStrength(item1, item2, term)
          });
        }
      }
    }

    return connections.sort((a, b) => b.strength - a.strength).slice(0, 10);
  }

  calculateConnectionStrength(item1, item2, term) {
    // Simple strength calculation
    let strength = 0;

    // Same type bonus
    if (item1.type === item2.type) strength += 0.2;

    // Similar paths bonus
    const path1 = item1.path || item1.file_path || '';
    const path2 = item2.path || item2.file_path || '';
    if (path1 && path2) {
      const commonDirs = this.getCommonDirectories(path1, path2);
      strength += commonDirs * 0.1;
    }

    // Score average
    const avgScore = ((item1.score || 0) + (item2.score || 0)) / 2;
    strength += avgScore * 0.5;

    // TODO: Add term frequency analysis using the term parameter

    return Math.min(strength, 1.0);
  }

  getCommonDirectories(path1, path2) {
    const dirs1 = path1.split('/').slice(0, -1);
    const dirs2 = path2.split('/').slice(0, -1);
    let common = 0;

    for (let i = 0; i < Math.min(dirs1.length, dirs2.length); i++) {
      if (dirs1[i] === dirs2[i]) {
        common++;
      } else {
        break;
      }
    }

    return common;
  }

  createCitationsFromResults(results) {
    return results.map((item, index) => ({
      id: item.id,
      number: index + 1,
      source: {
        id: item.id,
        title: item.title || 'Code snippet',
        path: item.path || item.file_path || 'unknown',
        type: item.type || 'document'
      },
      content: item.content.slice(0, 200),
      confidence: item.score || 0.8
    }));
  }
}

/**
 * Command to summarize knowledge base content on a topic
 */
export class KnowledgeSummaryCommand extends KnowledgeCommand {
  constructor() {
    super(
      '/knowledge-summary',
      'Summarize relevant knowledge base content',
      '/knowledge-summary <topic> [--max-items=10] [--include-stats]',
      ['/ks', '/summary']
    );
  }

  async execute(args, context) {
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

  buildSummaryPrompt(topic, results, includeStats) {
    let prompt = `Please provide a comprehensive summary of the knowledge available about "${topic}" based on the following sources:\n\n`;

    results.forEach((item, index) => {
      const title = item.title || `${item.type || 'Content'} ${index + 1}`;
      prompt += `**Source ${index + 1}: ${title}**\n`;
      if (item.path || item.file_path) {
        prompt += `Path: ${item.path || item.file_path}\n`;
      }
      prompt += `Content: ${item.content.slice(0, 300)}...\n\n`;
    });

    prompt += `\nPlease create a summary that:\n`;
    prompt += `1. Synthesizes information from all sources\n`;
    prompt += `2. Identifies key concepts and relationships\n`;
    prompt += `3. Highlights any conflicts or inconsistencies\n`;
    prompt += `4. Provides actionable insights\n`;

    if (includeStats) {
      prompt += `5. Includes relevant statistics and metrics\n`;
    }

    prompt += `\nUse the citations [1], [2], etc. to reference specific sources.`;

    return prompt;
  }

  createCitationsFromResults(results) {
    return results.map((item, index) => ({
      id: item.id,
      number: index + 1,
      source: {
        id: item.id,
        title: item.title || 'Knowledge source',
        path: item.path || item.file_path || 'unknown',
        type: item.type || 'document'
      },
      content: item.content.slice(0, 200),
      confidence: item.score || 0.8
    }));
  }
}

/**
 * Registry for knowledge commands
 */
export class KnowledgeCommandRegistry {
  constructor() {
    this.commands = new Map();
    this.registerDefaultCommands();
  }

  registerDefaultCommands() {
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

  register(command) {
    this.commands.set(command.name, command);
    command.aliases.forEach(alias => {
      this.commands.set(alias, command);
    });
  }

  get(commandName) {
    return this.commands.get(commandName);
  }

  getAll() {
    const unique = new Map();
    this.commands.forEach(cmd => {
      unique.set(cmd.name, cmd);
    });
    return Array.from(unique.values());
  }

  async execute(commandLine, context) {
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
