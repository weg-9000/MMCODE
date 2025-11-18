import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateSession } from '@/hooks/useSession'
import { Loader2 } from 'lucide-react'

export default function HomePage() {
  const [requirements, setRequirements] = useState('')
  const navigate = useNavigate()
  const createSessionMutation = useCreateSession()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    if (!requirements.trim()) {
      return
    }

    try {
      const session = await createSessionMutation.mutateAsync(requirements)
      navigate(`/session/${session.id}`)
    } catch (error) {
      console.error('Failed to create session:', error)
    }
  }

  return (
    <div className="container mx-auto px-4 py-8 max-w-4xl">
      <div className="text-center mb-8">
        <h1 className="text-4xl font-bold tracking-tight mb-4">
          DevStrategist AI
        </h1>
        <p className="text-xl text-muted-foreground mb-8">
          AI-powered development strategy automation platform
        </p>
      </div>

      <Card className="mb-8">
        <CardHeader>
          <CardTitle>Describe Your Project Requirements</CardTitle>
          <CardDescription>
            Tell us about your project needs, and our AI agents will analyze and generate 
            a comprehensive development strategy, tech stack recommendations, and documentation.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <Textarea
              placeholder="Example: Build a real-time chat application with user authentication, file sharing, and mobile support. The system should handle 10,000 concurrent users and integrate with existing OAuth providers..."
              value={requirements}
              onChange={(e) => setRequirements(e.target.value)}
              rows={6}
              className="min-h-[150px]"
            />
            <Button 
              type="submit" 
              disabled={!requirements.trim() || createSessionMutation.isPending}
              className="w-full"
            >
              {createSessionMutation.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating Session...
                </>
              ) : (
                'Start Analysis'
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      <div className="grid md:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">🔍 Requirement Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              AI agents extract entities, use cases, and technical constraints from your requirements.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">🏗️ Architecture Design</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Generate system architecture diagrams and component relationships.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">📚 Documentation</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Create OpenAPI specs, ERD diagrams, and comprehensive project documentation.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}