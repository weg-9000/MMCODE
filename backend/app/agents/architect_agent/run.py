"""
Architect Agent Standalone Runner
=================================

Runs the Architect Agent as a standalone A2A server.

Usage:
    python -m app.agents.architect_agent.run
"""

import os
import sys
import asyncio
import logging
import signal
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Setup path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.agents.architect_agent.core.agent import ArchitectAgent
from app.agents.architect_agent.config.settings import get_settings
from app.agents.shared.models.a2a_models import A2ATask, TaskStatus

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("ArchitectAgentRunner")

# Global agent instance
agent: Optional[ArchitectAgent] = None


class TaskRequest(BaseModel):
    """A2A Task Request"""
    task_type: str
    context: dict
    correlation_id: Optional[str] = None


class TaskResponse(BaseModel):
    """A2A Task Response"""
    task_id: str
    status: str
    result: Optional[dict] = None
    error: Optional[str] = None


def create_app() -> FastAPI:
    """Create FastAPI application for the agent"""
    app = FastAPI(
        title="Architect Agent",
        description="A2A Server for Architecture Design",
        version="1.0.0"
    )

    @app.on_event("startup")
    async def startup():
        global agent
        settings = get_settings()
        config = {
            "own_endpoint": f"http://localhost:{settings.a2a_server_port}",
            "redis_url": settings.redis_url,
            "llm_provider": os.getenv("LLM_PROVIDER", "openai"),
            "llm_model": os.getenv("LLM_MODEL", settings.effective_model),
            "llm_api_key": settings.effective_api_key or os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY"),
            "llm_timeout": settings.llm_timeout,
            "llm_temperature": settings.effective_temperature,
        }
        agent = ArchitectAgent(config)
        logger.info(f"Architect Agent started on port {settings.a2a_server_port}")

    @app.on_event("shutdown")
    async def shutdown():
        logger.info("Architect Agent shutting down")

    @app.get("/health")
    async def health():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "agent_id": "architect-agent",
            "version": "1.0.0"
        }

    @app.get("/capabilities")
    async def capabilities():
        """Get agent capabilities"""
        if agent:
            return agent.agent_card.to_dict()
        return {"error": "Agent not initialized"}

    @app.post("/tasks", response_model=TaskResponse)
    async def create_task(request: TaskRequest):
        """Create and process a task"""
        if not agent:
            raise HTTPException(status_code=503, detail="Agent not initialized")

        try:
            # Create task
            task = A2ATask(
                task_type=request.task_type,
                context=request.context,
                status=TaskStatus.PENDING
            )

            # Process task based on type
            if request.task_type == "architecture_design":
                result = await agent.handle_architecture_design(task)
            elif request.task_type == "pattern_recommendation":
                result = await agent.handle_pattern_recommendation(task)
            else:
                raise HTTPException(status_code=400, detail=f"Unknown task type: {request.task_type}")

            return TaskResponse(
                task_id=task.task_id,
                status="completed",
                result=result.content if result else None
            )

        except Exception as e:
            logger.exception(f"Task processing failed: {e}")
            return TaskResponse(
                task_id=task.task_id if task else "unknown",
                status="failed",
                error=str(e)
            )

    @app.get("/tasks/{task_id}")
    async def get_task(task_id: str):
        """Get task status"""
        # For simplicity, tasks are processed synchronously
        return {"task_id": task_id, "status": "not_found"}

    return app


def main():
    """Main entry point"""
    settings = get_settings()
    port = int(os.getenv("A2A_SERVER_PORT", settings.a2a_server_port))

    logger.info(f"Starting Architect Agent on port {port}")

    app = create_app()

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )


if __name__ == "__main__":
    main()
