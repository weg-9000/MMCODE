import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { 
  createSession, 
  getSession, 
  getSessionArtifacts, 
  runAgentAnalysis 
} from '@/lib/api'
import { useToast } from '@/components/ui/use-toast'

export function useCreateSession() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  
  return useMutation({
    mutationFn: (requirements: string) => createSession(requirements),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
      toast({
        title: "Session created",
        description: "Your analysis session has been created successfully.",
      })
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to create session. Please try again.",
        variant: "destructive",
      })
    }
  })
}

export function useSession(sessionId: string) {
  return useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => getSession(sessionId),
    enabled: !!sessionId,
    refetchInterval: (data) => {
      // Stop polling if completed or failed
      return data?.status === 'completed' || data?.status === 'failed' ? false : 2000
    }
  })
}

export function useSessionArtifacts(sessionId: string) {
  return useQuery({
    queryKey: ['session-artifacts', sessionId],
    queryFn: () => getSessionArtifacts(sessionId),
    enabled: !!sessionId
  })
}

export function useRunAnalysis() {
  const queryClient = useQueryClient()
  const { toast } = useToast()
  
  return useMutation({
    mutationFn: (sessionId: string) => runAgentAnalysis(sessionId),
    onSuccess: (_, sessionId) => {
      queryClient.invalidateQueries({ queryKey: ['session', sessionId] })
      toast({
        title: "Analysis started",
        description: "AI agents are now analyzing your requirements.",
      })
    },
    onError: (error) => {
      toast({
        title: "Error",
        description: "Failed to start analysis. Please try again.",
        variant: "destructive",
      })
    }
  })
}