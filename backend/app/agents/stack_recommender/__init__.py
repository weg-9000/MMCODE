"""
StackRecommender Agent - A2A-enabled technology stack recommendation system.

This module provides intelligent technology stack recommendations based on
architecture analysis using the Agent-to-Agent (A2A) protocol.

Main Components:
- A2A Server: Handles incoming tasks from other agents
- Stack Analysis Engine: Core recommendation logic
- Quality Scorer: Evaluates recommendation quality
- Knowledge Searcher: Searches for relevant technology insights
- Template Matcher: Provides predefined stack templates

Usage:
    from app.agents.stack_recommender import agent_server
    
    # The agent server is automatically configured and ready to handle A2A tasks
    app = agent_server.app
"""

from .core.agent import agent_server, StackRecommenderAgent as A2AStackRecommenderServer
from .capabilities.stack_analysis import StackAnalysisEngine
from .utils.quality_scorer import QualityScorer
from .utils.knowledge_search import KnowledgeSearcher
from .utils.template_matcher import TemplateMatcher
from .config.settings import settings

__version__ = "1.0.0"
__author__ = "DevStrategist AI Team"

# Export main components
__all__ = [
    "agent_server",
    "A2AStackRecommenderServer",
    "StackAnalysisEngine", 
    "QualityScorer",
    "KnowledgeSearcher",
    "TemplateMatcher",
    "settings"
]

# Agent metadata
AGENT_INFO = {
    "name": "stack-recommender",
    "version": __version__,
    "description": "AI agent for technology stack recommendation based on architecture analysis",
    "capabilities": [
        "Technology stack analysis",
        "Architecture pattern matching",
        "Quality assessment",
        "Knowledge-based recommendations",
        "Template-based fallback"
    ],
    "protocols": ["A2A"],
    "dependencies": [
        "fastapi",
        "langchain",
        "openai",
        "pydantic",
        "sqlalchemy"
    ]
}