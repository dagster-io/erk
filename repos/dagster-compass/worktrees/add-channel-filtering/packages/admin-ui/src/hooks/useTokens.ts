import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchTokens, createToken } from '../api/tokens'
import type { CreateTokenRequest } from '../types/token'

export function useTokens() {
  return useQuery({
    queryKey: ['tokens'],
    queryFn: fetchTokens,
  })
}

export function useCreateToken() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: CreateTokenRequest) => createToken(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tokens'] })
    },
  })
}
