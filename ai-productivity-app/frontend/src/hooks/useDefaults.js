import { useQuery } from '@tanstack/react-query';
import api from '../utils/api';

export function useDefaults() {
  return useQuery({
    queryKey: ['ai-config', 'defaults'],
    queryFn: () => api.get('/api/v1/ai-config/defaults').then(r => r.data),
    staleTime: 60 * 60 * 1000,       // 1 h
  });
}
