const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

interface CreateSessionRequest {
  requirements: string
}

interface Session {
  id: string
  requirements: string
  status: 'draft' | 'analyzing' | 'completed' | 'failed'
  version: number
  created_at: string
  completed_at?: string
  agent_status?: Record<string, string>
}

interface Artifact {
  id: string
  type: string
  content: any
  quality_score?: any
  created_at: string
}

export async function createSession(requirements: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json' 
    },
    body: JSON.stringify({ requirements })
  })
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return response.json()
}

export async function getSession(sessionId: string): Promise<Session> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}`)
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return response.json()
}

export async function getSessionArtifacts(sessionId: string): Promise<Artifact[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sessions/${sessionId}/artifacts`)
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return response.json()
}

export async function runAgentAnalysis(sessionId: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}/api/v1/agents/analyze`, {
    method: 'POST',
    headers: { 
      'Content-Type': 'application/json' 
    },
    body: JSON.stringify({ session_id: sessionId })
  })
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
}

export function streamAgentStatus(
  sessionId: string, 
  onMessage: (data: any) => void,
  onError?: (error: Event) => void
): () => void {
  const eventSource = new EventSource(`${API_BASE_URL}/api/v1/agents/${sessionId}/stream`)
  
  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      onMessage(data)
    } catch (error) {
      console.error('Error parsing SSE data:', error)
    }
  }
  
  if (onError) {
    eventSource.onerror = onError
  }
  
  return () => eventSource.close()
}