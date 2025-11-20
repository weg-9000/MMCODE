"""
Knowledge base search utility for technology recommendations.
Integrates with pgvector for similarity search.
"""

from typing import List, Dict, Any, Optional
import asyncio
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import openai

from ..config.settings import settings

logger = logging.getLogger(__name__)


class KnowledgeSearcher:
    """Searches knowledge base for relevant technology information"""
    
    def __init__(self):
        self.openai_client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        threshold: float = None
    ) -> List[Dict[str, Any]]:
        """Search knowledge base for relevant information"""
        
        try:
            # Generate query embedding
            query_embedding = await self._create_embedding(query)
            
            if not query_embedding:
                logger.warning(f"Failed to create embedding for query: {query}")
                return []
            
            # Search knowledge base
            search_threshold = threshold or settings.vector_search_threshold
            search_limit = min(limit, settings.vector_search_limit)
            
            # Note: This would require integration with existing database session
            # For now, returning mock results
            return await self._mock_search(query, search_limit)
            
        except Exception as e:
            logger.error(f"Knowledge search failed for query '{query}': {str(e)}")
            return []
    
    async def search_by_technology(
        self,
        technology_name: str,
        context: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for specific technology information"""
        
        query = f"{technology_name}"
        if context:
            query += f" {context}"
        
        return await self.search(query, limit=3)
    
    async def search_by_domain(
        self,
        domain: str,
        scale: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search for domain-specific technology recommendations"""
        
        query = f"{domain} technology stack"
        if scale:
            query += f" {scale} scale"
        
        return await self.search(query, limit=4)
    
    async def search_by_pattern(self, pattern: str) -> List[Dict[str, Any]]:
        """Search for architecture pattern implementations"""
        
        query = f"{pattern} architecture pattern implementation"
        return await self.search(query, limit=3)
    
    async def _create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding for text using OpenAI API"""
        
        try:
            response = await self.openai_client.embeddings.create(
                model=self.embedding_model,
                input=text,
                encoding_format="float"
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to create embedding: {str(e)}")
            return None
    
    async def _vector_search(
        self,
        db: AsyncSession,
        query_embedding: List[float],
        threshold: float,
        limit: int
    ) -> List[Dict[str, Any]]:
        """Perform vector similarity search in knowledge base"""
        
        try:
            # SQL query for pgvector similarity search
            stmt = text("""
                SELECT 
                    id, content, metadata,
                    1 - (embedding <=> :embedding) as similarity
                FROM knowledge_base
                WHERE 1 - (embedding <=> :embedding) > :threshold
                ORDER BY embedding <=> :embedding
                LIMIT :limit
            """).bindparams(
                embedding=query_embedding,
                threshold=threshold,
                limit=limit
            )
            
            result = await db.execute(stmt)
            rows = result.fetchall()
            
            search_results = []
            for row in rows:
                search_results.append({
                    "id": str(row.id),
                    "content": row.content,
                    "metadata": row.metadata or {},
                    "similarity": round(row.similarity, 3)
                })
            
            return search_results
            
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            return []
    
    async def _mock_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Mock search results for development/testing"""
        
        # Mock knowledge base entries
        mock_knowledge = {
            "react": [
                {
                    "id": "react_1",
                    "content": "React is a popular JavaScript library for building user interfaces, particularly web applications. It uses a component-based architecture and virtual DOM for efficient updates.",
                    "metadata": {
                        "url": "https://reactjs.org/docs",
                        "source": "official_docs",
                        "category": "frontend"
                    },
                    "similarity": 0.95
                },
                {
                    "id": "react_2", 
                    "content": "React ecosystem includes tools like Redux for state management, React Router for navigation, and Next.js for server-side rendering.",
                    "metadata": {
                        "url": "https://github.com/facebook/react",
                        "source": "github",
                        "category": "ecosystem"
                    },
                    "similarity": 0.87
                }
            ],
            "fastapi": [
                {
                    "id": "fastapi_1",
                    "content": "FastAPI is a modern Python web framework designed for building APIs quickly with automatic OpenAPI documentation and high performance.",
                    "metadata": {
                        "url": "https://fastapi.tiangolo.com",
                        "source": "official_docs",
                        "category": "backend"
                    },
                    "similarity": 0.93
                },
                {
                    "id": "fastapi_2",
                    "content": "FastAPI supports async/await patterns, automatic request/response validation with Pydantic, and dependency injection for building scalable APIs.",
                    "metadata": {
                        "url": "https://github.com/tiangolo/fastapi",
                        "source": "github", 
                        "category": "features"
                    },
                    "similarity": 0.85
                }
            ],
            "postgresql": [
                {
                    "id": "postgres_1",
                    "content": "PostgreSQL is a powerful open-source relational database with advanced features like JSONB support, full-text search, and extensions.",
                    "metadata": {
                        "url": "https://www.postgresql.org/docs",
                        "source": "official_docs",
                        "category": "database"
                    },
                    "similarity": 0.91
                }
            ],
            "web_application": [
                {
                    "id": "web_stack_1",
                    "content": "Modern web applications typically use a frontend framework (React, Vue, Angular), backend API (FastAPI, Express, Django), and database (PostgreSQL, MongoDB).",
                    "metadata": {
                        "url": "https://developer.mozilla.org/en-US/docs/Learn",
                        "source": "mdn",
                        "category": "architecture"
                    },
                    "similarity": 0.88
                }
            ],
            "microservices": [
                {
                    "id": "microservices_1",
                    "content": "Microservices architecture involves breaking applications into small, independent services that communicate via APIs, often deployed using containers and orchestration.",
                    "metadata": {
                        "url": "https://microservices.io",
                        "source": "microservices_io",
                        "category": "architecture"
                    },
                    "similarity": 0.89
                }
            ]
        }
        
        # Find relevant mock data
        results = []
        query_lower = query.lower()
        
        for key, entries in mock_knowledge.items():
            if key in query_lower or any(word in query_lower for word in key.split("_")):
                results.extend(entries)
        
        # If no specific matches, return some general results
        if not results:
            results = [
                {
                    "id": "general_1",
                    "content": f"Technology information related to {query}. Modern software development involves choosing appropriate frameworks and tools based on requirements.",
                    "metadata": {
                        "url": "https://stackoverflow.com",
                        "source": "community",
                        "category": "general"
                    },
                    "similarity": 0.7
                }
            ]
        
        # Sort by similarity and limit results
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:limit]
    
    async def bulk_search(
        self,
        queries: List[str],
        limit_per_query: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Perform multiple searches concurrently"""
        
        search_tasks = [
            self.search(query, limit=limit_per_query)
            for query in queries
        ]
        
        results = await asyncio.gather(*search_tasks, return_exceptions=True)
        
        search_results = {}
        for i, (query, result) in enumerate(zip(queries, results)):
            if isinstance(result, Exception):
                logger.warning(f"Search failed for query '{query}': {result}")
                search_results[query] = []
            else:
                search_results[query] = result
        
        return search_results
    
    async def get_technology_popularity(self, technology: str) -> float:
        """Get technology popularity/adoption score"""
        
        # Mock popularity scores (in real implementation, could be from GitHub stars, surveys, etc.)
        popularity_scores = {
            "react": 0.95,
            "vue": 0.85,
            "angular": 0.80,
            "fastapi": 0.80,
            "django": 0.85,
            "express": 0.90,
            "postgresql": 0.90,
            "mongodb": 0.80,
            "redis": 0.85,
            "docker": 0.95,
            "kubernetes": 0.85
        }
        
        return popularity_scores.get(technology.lower(), 0.6)
    
    async def get_technology_trends(self, technologies: List[str]) -> Dict[str, Dict[str, float]]:
        """Get trend data for technologies (growth, stability, etc.)"""
        
        # Mock trend data
        trends = {}
        
        for tech in technologies:
            trends[tech] = {
                "growth_rate": 0.1 + (hash(tech) % 20) / 100,  # Mock growth 10-30%
                "stability": 0.7 + (hash(tech + "stability") % 30) / 100,  # Mock stability 70-100%
                "job_market": 0.6 + (hash(tech + "jobs") % 40) / 100  # Mock job market 60-100%
            }
        
        return trends