// DEPRECATED: This file has been consolidated into AIConfigContext.jsx
// // DEPRECATED: This hook has been consolidated into AIConfigContext.jsx
// // Use useAIConfig() instead of useConfigOptimized()
// //
// // hooks/useConfigOptimized.js
// // Optimized version of useConfig using React Query for better caching and deduplication
// // import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
// import { configAPI } from '../api/config';
// import { toast } from 'react-hot-toast';
// import { useDefaults } from './useDefaults';
//
// export function useConfigOptimized() {
//   const queryClient = useQueryClient();
//   const { data: defaults } = useDefaults();
//
//   // Query for fetching config with optimized caching
//   const {
//     data: config,
//     isLoading: loading,
//     error,
//     refetch
//   } = useQuery({
//     queryKey: ['config'],
//     queryFn: async () => {
//       const data = await configAPI.getConfig();
//       return createConfigData(data, defaults);
//     },
//     enabled: !!defaults, // only run if defaults are loaded
//     staleTime: 30000, // Consider data fresh for 30 seconds
//     cacheTime: 5 * 60 * 1000, // Keep in cache for 5 minutes
//     refetchOnWindowFocus: false, // Prevent excessive refetching
//     retry: (failureCount, error) => {
//       // Don't retry client errors (4xx)
//       if (error?.response?.status >= 400 && error?.response?.status < 500) {
//         return false;
//       }
//       return failureCount < 2;
//     },
//     onError: (err) => {
//       console.error('Failed to fetch config:', err);
//       // Don't show toast for cached data scenarios
//       if (!queryClient.getQueryData(['config'])) {
//         toast.error('Failed to load configuration');
//       }
//     }
//   });
//
//   // Mutation for updating model config with optimistic updates
//   const updateModelConfigMutation = useMutation({
//     mutationFn: async (updates) => {
//       const defaultProvider = defaults?.provider || 'openai';
//       const defaultModel = defaults?.model || 'gpt-4o-mini';
//
//       return await configAPI.updateModelConfig({
//         provider: updates.provider || config?.current.provider || defaultProvider,
//         chat_model: updates.chat_model || config?.current.chat_model || defaultModel,
//         useResponsesApi: updates.useResponsesApi ?? config?.current.useResponsesApi ?? false,
//         temperature: updates.temperature,
//         maxTokens: updates.maxTokens,
//         topP: updates.topP,
//         frequencyPenalty: updates.frequencyPenalty,
//         presencePenalty: updates.presencePenalty,
//         systemPrompt: updates.systemPrompt,
//         reasoning_effort: updates.reasoning_effort,
//       });
//     },
//     onMutate: async (updates) => {
//       // Cancel any outgoing refetches
//       await queryClient.cancelQueries(['config']);
//
//       // Snapshot the previous value
//       const previousConfig = queryClient.getQueryData(['config']);
//
//       // Optimistically update to the new value
//       queryClient.setQueryData(['config'], old => {
//         if (!old) return old;
//         return {
//           ...old,
//           current: {
//             ...old.current,
//             ...updates
//           }
//         };
//       });
//
//       // Return a context object with the snapshotted value
//       return { previousConfig };
//     },
//     onError: (err, updates, context) => {
//       // If the mutation fails, use the context returned from onMutate to roll back
//       queryClient.setQueryData(['config'], context.previousConfig);
//       console.error('Failed to update config:', err);
//       toast.error('Failed to update configuration');
//     },
//     onSuccess: () => {
//       // Invalidate and refetch config to ensure consistency
//       queryClient.invalidateQueries(['config']);
//       toast.success('Configuration updated successfully');
//     },
//     onSettled: () => {
//       // Always refetch after error or success to ensure we have the latest data
//       queryClient.invalidateQueries(['config']);
//     },
//   });
//
//   // Debounced config update function to prevent rapid API calls
//   const updateConfig = async (updates) => {
//     try {
//       await updateModelConfigMutation.mutateAsync(updates);
//     } catch (error) {
//       // Error is already handled in the mutation
//       throw error;
//     }
//   };
//
//   // Prefetch config on mount for better UX
//   const prefetchConfig = () => {
//     queryClient.prefetchQuery({
//       queryKey: ['config'],
//       queryFn: async () => {
//         const data = await configAPI.getConfig();
//         return createConfigData(data, defaults);
//       },
//       staleTime: 30000,
//     });
//   };
//
//   return {
//     config,
//     loading,
//     error,
//     refetch,
//     updateConfig,
//     prefetchConfig,
//     isUpdating: updateModelConfigMutation.isLoading,
//     updateError: updateModelConfigMutation.error,
//   };
// }
//
// // Alternative hook that maintains backward compatibility with existing useConfig
// export function useConfig() {
//   const optimized = useConfigOptimized();
//
//   return {
//     config: optimized.config,
//     loading: optimized.loading,
//     error: optimized.error,
//     refetch: optimized.refetch,
//     updateConfig: optimized.updateConfig,
//   };
// }
//
//
// // Helper function to create a default config structure
// export function createConfigData(data, defaults) {
//   const defaultProvider = defaults?.provider || 'openai';
//   const defaultModel = defaults?.model || 'gpt-4o-mini';
//   const defaultTemperature = defaults?.temperature ?? 0.7;
//
//   return {
//     current: {
//       provider: data?.provider || defaultProvider,
//       chat_model: data?.chat_model || defaultModel,
//       temperature: data?.temperature ?? defaultTemperature,
//       maxTokens: data?.maxTokens ?? 4096,
//       topP: data?.topP ?? 1.0,
//       frequencyPenalty: data?.frequencyPenalty ?? 0.0,
//       presencePenalty: data?.presencePenalty ?? 0.0,
//       systemPrompt: data?.systemPrompt || '',
//       useResponsesApi: data?.useResponsesApi ?? false,
//       reasoning_effort: data?.reasoning_effort || 'auto',
//     },
//     available: {
//       models: data?.available_models || [],
//       providers: data?.available_providers || [],
//     },
//     lastUpdated: new Date().toISOString(),
//   };
// }
