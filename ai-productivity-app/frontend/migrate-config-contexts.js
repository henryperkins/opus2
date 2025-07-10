#!/usr/bin/env node

/**
 * Migration script to consolidate configuration contexts
 * 
 * This script will:
 * 1. Update all imports from useConfigOptimized to useAIConfig
 * 2. Update all imports from ModelContext to AIConfigContext
 * 3. Update component usage to use the new consolidated API
 * 4. Create a backup of modified files
 */

import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Files to migrate
const MIGRATION_MAP = {
  // Remove these files after migration
  'src/contexts/ModelContext.jsx': 'REMOVE',
  'src/hooks/useConfigOptimized.js': 'REMOVE',
  
  // Update these imports
  'src/components/settings/ModelConfiguration.jsx': 'UPDATE',
  'src/components/settings/ThinkingConfiguration.jsx': 'UPDATE',
  'src/components/settings/UnifiedAISettings.jsx': 'UPDATE',
  'src/components/chat/ModelSwitcher.jsx': 'UPDATE',
  'src/hooks/useModelSelect.js': 'UPDATE',
  'src/pages/UnifiedSettingsPage.jsx': 'UPDATE',
  'src/pages/ProjectChatPage.jsx': 'UPDATE',
  'src/pages/Dashboard.jsx': 'UPDATE',
};

// Import replacements
const IMPORT_REPLACEMENTS = [
  {
    from: /import\s+{\s*useConfigOptimized\s*}\s+from\s+['"][^'"]*useConfigOptimized['"];?/g,
    to: "import { useAIConfig } from '../contexts/AIConfigContext';"
  },
  {
    from: /import\s+{\s*useConfig\s*}\s+from\s+['"][^'"]*useConfigOptimized['"];?/g,
    to: "import { useAIConfig } from '../contexts/AIConfigContext';"
  },
  {
    from: /import\s+{\s*useModelContext\s*}\s+from\s+['"][^'"]*ModelContext['"];?/g,
    to: "import { useAIConfig } from '../contexts/AIConfigContext';"
  },
  {
    from: /import\s+{\s*ModelProvider\s*}\s+from\s+['"][^'"]*ModelContext['"];?/g,
    to: "import { AIConfigProvider } from '../contexts/AIConfigContext';"
  }
];

// Usage replacements
const USAGE_REPLACEMENTS = [
  {
    from: /useConfigOptimized\(\)/g,
    to: 'useAIConfig()'
  },
  {
    from: /useConfig\(\)/g,
    to: 'useAIConfig()'
  },
  {
    from: /useModelContext\(\)/g,
    to: 'useAIConfig()'
  },
  {
    from: /ModelProvider/g,
    to: 'AIConfigProvider'
  },
  {
    from: /config\.current\.chat_model/g,
    to: 'config.model_id'
  },
  {
    from: /config\.current\.model_id/g,
    to: 'config.model_id'
  },
  {
    from: /config\.current\.provider/g,
    to: 'config.provider'
  },
  {
    from: /currentModel/g,
    to: 'config?.model_id'
  },
  {
    from: /currentProvider/g,
    to: 'config?.provider'
  }
];

function createBackup(filePath) {
  const backupPath = filePath + '.backup';
  if (fs.existsSync(filePath)) {
    fs.copyFileSync(filePath, backupPath);
    console.log(`✓ Created backup: ${backupPath}`);
  }
}

function updateFile(filePath) {
  if (!fs.existsSync(filePath)) {
    console.log(`⚠ File not found: ${filePath}`);
    return;
  }

  // Create backup
  createBackup(filePath);

  // Read file content
  let content = fs.readFileSync(filePath, 'utf8');
  let modified = false;

  // Apply import replacements
  IMPORT_REPLACEMENTS.forEach(replacement => {
    if (replacement.from.test(content)) {
      content = content.replace(replacement.from, replacement.to);
      modified = true;
    }
  });

  // Apply usage replacements
  USAGE_REPLACEMENTS.forEach(replacement => {
    if (replacement.from.test(content)) {
      content = content.replace(replacement.from, replacement.to);
      modified = true;
    }
  });

  // Write updated content
  if (modified) {
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`✓ Updated: ${filePath}`);
  } else {
    console.log(`- No changes needed: ${filePath}`);
  }
}

function removeFile(filePath) {
  if (fs.existsSync(filePath)) {
    // Create backup before removing
    createBackup(filePath);
    
    // Comment out the file instead of deleting
    const content = fs.readFileSync(filePath, 'utf8');
    const commentedContent = `// DEPRECATED: This file has been consolidated into AIConfigContext.jsx\n// ${content.split('\n').join('\n// ')}`;
    
    fs.writeFileSync(filePath, commentedContent, 'utf8');
    console.log(`✓ Deprecated: ${filePath}`);
  }
}

function main() {
  console.log('🚀 Starting configuration context migration...\n');

  // Process each file in the migration map
  Object.entries(MIGRATION_MAP).forEach(([filePath, action]) => {
    const fullPath = path.join(__dirname, filePath);
    
    if (action === 'REMOVE') {
      removeFile(fullPath);
    } else if (action === 'UPDATE') {
      updateFile(fullPath);
    }
  });

  console.log('\n✅ Migration completed!');
  console.log('\nNext steps:');
  console.log('1. Review the changes in each file');
  console.log('2. Test the application');
  console.log('3. Remove .backup files once confirmed working');
  console.log('4. Update any remaining references manually');
}

if (import.meta.url === `file://${process.argv[1]}`) {
  main();
}