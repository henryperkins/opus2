/* Utility constants for model presets and model information
 *
 * Moving these large static objects out of component files
 * keeps React components slim and makes the data reusable
 * across the application (e.g. other settings pages, tests).
 */
import { Brain, Zap, Settings, DollarSign } from 'lucide-react';

/* ------------------------------------------------------------------
 * Quick-select parameter presets for chat models
 * ---------------------------------------------------------------- */
export const modelPresets = [
  {
    id: 'balanced',
    name: 'Balanced',
    description: 'Good balance of quality and speed',
    config: {
      temperature: 0.7,
      maxTokens: 2048,
      topP: 0.95,
      frequencyPenalty: 0,
      presencePenalty: 0
    },
    icon: Brain
  },
  {
    id: 'creative',
    name: 'Creative',
    description: 'More creative and varied responses',
    config: {
      temperature: 1.2,
      maxTokens: 3000,
      topP: 0.95,
      frequencyPenalty: 0.2,
      presencePenalty: 0.2
    },
    icon: Zap
  },
  {
    id: 'precise',
    name: 'Precise',
    description: 'Focused and deterministic responses',
    config: {
      temperature: 0.3,
      maxTokens: 2048,
      topP: 0.9,
      frequencyPenalty: 0,
      presencePenalty: 0
    },
    icon: Settings
  },
  {
    id: 'cost-efficient',
    name: 'Cost Efficient',
    description: 'Optimized for token usage',
    config: {
      temperature: 0.5,
      maxTokens: 1024,
      topP: 0.9,
      frequencyPenalty: 0,
      presencePenalty: 0
    },
    icon: DollarSign
  }
];

/* ------------------------------------------------------------------
 * Metadata for supported LLMs (context size, pricing, etc.)
 * ---------------------------------------------------------------- */
export const modelInfo = {
  'gpt-4o': {
    id: 'gpt-4o',
    name: 'GPT-4 Omni',
    contextLength: 128000,
    costPer1kTokens: { input: 0.005, output: 0.015 },
    capabilities: ['multimodal', 'function-calling', 'json-mode'],
    recommended: true
  },
  'gpt-4o-mini': {
    id: 'gpt-4o-mini',
    name: 'GPT-4 Omni Mini',
    contextLength: 128000,
    costPer1kTokens: { input: 0.00015, output: 0.0006 },
    capabilities: ['function-calling', 'json-mode'],
    recommended: true
  },
  'gpt-4-turbo': {
    id: 'gpt-4-turbo',
    name: 'GPT-4 Turbo',
    contextLength: 128000,
    costPer1kTokens: { input: 0.01, output: 0.03 },
    capabilities: ['function-calling', 'json-mode']
  },
  'gpt-3.5-turbo': {
    id: 'gpt-3.5-turbo',
    name: 'GPT-3.5 Turbo',
    contextLength: 16385,
    costPer1kTokens: { input: 0.0005, output: 0.0015 },
    capabilities: ['function-calling']
  }
};
