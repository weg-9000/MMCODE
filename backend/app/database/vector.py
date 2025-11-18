from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from typing import List, Dict, Any
import logging

from ..models.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)

async def search_knowledge(
    db: AsyncSession,
    query_embedding: List[float],
    match_threshold: float = 0.7,
    match_count: int = 5
) -> List[Dict[str, Any]]:
    """Search knowledge base using vector similarity"""
    try:
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
            threshold=match_threshold,
            limit=match_count
        )
        
        result = await db.execute(stmt)
        rows = result.fetchall()
        
        return [
            {
                "id": str(row.id),
                "content": row.content,
                "metadata": row.metadata,
                "similarity": row.similarity
            }
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Vector search failed: {str(e)}")
        return []

async def add_knowledge_entry(
    db: AsyncSession,
    content: str,
    embedding: List[float],
    metadata: Dict[str, Any]
) -> KnowledgeBase:
    """Add new entry to knowledge base"""
    entry = KnowledgeBase(
        content=content,
        embedding=embedding,
        metadata=metadata
    )
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry