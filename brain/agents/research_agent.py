"""
Research Assistant Agent (Chunk 5.4)
Specialized agent for research tasks using library + memory search.
"""

import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import config
from services.llm import llm
from tools.library_search import get_library_search_tool


@dataclass
class ResearchResult:
    """Result from research assistant"""
    answer: str
    sources: List[Dict[str, Any]]
    memories_consulted: int
    library_chunks_consulted: int
    total_sources: int
    success: bool
    error: Optional[str] = None


async def library_search_tool(query: str, top_k: int = 5) -> str:
    """
    Search the ingested library for relevant information.

    Args:
        query: Research query
        top_k: Number of results to return (default: 5)

    Returns:
        Formatted list of library chunks with citations
    """
    try:
        # Validate input
        if not query or not query.strip():
            return "Error: Search query cannot be empty"

        query = query.strip()

        # Limit query length
        if len(query) > 500:
            return f"Error: Query too long ({len(query)} chars). Maximum 500 characters."

        # Use direct tool instead of HTTP loopback
        tool = get_library_search_tool()
        chunks = tool.search(query, top_k=min(top_k, 10))

        if not chunks:
            return "No relevant library documents found."

        # Format results with citations
        output = f"Found {len(chunks)} relevant library sources:\n\n"
        for i, chunk in enumerate(chunks, 1):
            filename = chunk.get("filename", "unknown")
            chunk_idx = chunk.get("chunk_index", 0)
            total_chunks = chunk.get("total_chunks", 1)
            text = chunk.get("text", "")[:200]  # Truncate for display
            similarity_pct = chunk.get("similarity_pct", 0)

            output += f"{i}. [{similarity_pct:.1f}% match] {filename} (chunk {chunk_idx}/{total_chunks})\n"
            output += f"   {text}...\n\n"

        return output.strip()

    except Exception as e:
        return f"Error searching library: {str(e)}"


async def research_query(
    question: str,
    use_library: bool = True,
    use_memory: bool = True,
    top_k: int = 5
) -> ResearchResult:
    """
    Research a question using multiple sources.

    Args:
        question: Research question
        use_library: Whether to search library documents
        use_memory: Whether to search conversation memories
        top_k: Number of results per source

    Returns:
        ResearchResult with synthesized answer and sources
    """
    try:
        sources = []
        library_chunks = 0
        memories = 0

        # Search library if enabled
        if use_library:
            try:
                tool = get_library_search_tool()
                chunks = tool.search(question, top_k=top_k)
                library_chunks = len(chunks)

                for chunk in chunks:
                    sources.append({
                        "type": "library",
                        "filename": chunk.get("filename"),
                        "text": chunk.get("text"),
                        "similarity": chunk.get("similarity_pct", 0)
                    })
            except Exception as e:
                # Library search failed, continue without it
                pass

        # Search memories if enabled
        if use_memory:
            try:
                # Use internal memory search if available or keep HTTP for now if memory logic is complex
                # For consistency with library search optimization, we should use vector_store directly
                # assuming it's initialized
                from memory.vector_store import vector_store
                
                # Ensure connected
                if not vector_store.client:
                    vector_store.connect()
                    
                memory_results = vector_store.search_similar(question, top_k=top_k)
                memories = len(memory_results)

                for mem in memory_results:
                    sources.append({
                        "type": "memory",
                        "message": mem.get("message"),
                        "timestamp": mem.get("timestamp"),
                        "similarity": (1.0 - mem.get("similarity_score", 1.0)) * 100
                    })
            except Exception as e:
                # Memory search failed, continue without it
                pass

        # Generate answer using Vorpal with context from sources
        context = _format_sources_for_llm(sources)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a research assistant. Answer the question using ONLY the provided sources. "
                    "Cite sources using [Source N] notation. If sources don't contain relevant information, "
                    "say so clearly. Be concise and factual."
                )
            },
            {
                "role": "user",
                "content": f"Question: {question}\n\nSources:\n{context}\n\nProvide a researched answer with citations:"
            }
        ]

        result = await llm.chat(
            messages=messages,
            max_tokens=500,
            temperature=0.3
        )
        
        answer = result["content"]

        return ResearchResult(
            answer=answer,
            sources=sources,
            memories_consulted=memories,
            library_chunks_consulted=library_chunks,
            total_sources=len(sources),
            success=True
        )

    except Exception as e:
        return ResearchResult(
            answer="",
            sources=[],
            memories_consulted=0,
            library_chunks_consulted=0,
            total_sources=0,
            success=False,
            error=str(e)
        )


def _format_sources_for_llm(sources: List[Dict[str, Any]]) -> str:
    """Format sources for LLM context"""
    if not sources:
        return "(No sources available)"

    formatted = []
    for i, source in enumerate(sources, 1):
        if source["type"] == "library":
            formatted.append(
                f"[Source {i}] {source['filename']}: {source['text'][:300]}"
            )
        elif source["type"] == "memory":
            formatted.append(
                f"[Source {i}] Memory: {source['message'][:200]}"
            )

    return "\n\n".join(formatted)


async def multi_query_research(
    questions: List[str],
    synthesize: bool = True
) -> Dict[str, Any]:
    """
    Research multiple related questions and optionally synthesize.

    Args:
        questions: List of research questions
        synthesize: Whether to combine answers into single response

    Returns:
        Dictionary with individual results and optional synthesis
    """
    results = []

    for question in questions:
        result = await research_query(question)
        results.append({
            "question": question,
            "result": result
        })

    if not synthesize:
        return {"questions": len(questions), "results": results}

    # Synthesize all findings
    all_sources = []
    for r in results:
        if r["result"].success:
            all_sources.extend(r["result"].sources)

    synthesis_prompt = "Synthesize findings from the following questions:\n"
    for i, r in enumerate(results, 1):
        synthesis_prompt += f"{i}. {r['question']}\n"
        if r["result"].success:
            synthesis_prompt += f"   Finding: {r['result'].answer}\n\n"

    # Generate synthesis
    try:
        messages = [
            {
                "role": "system",
                "content": "You are a research synthesizer. Combine the findings into a coherent summary."
            },
            {
                "role": "user",
                "content": synthesis_prompt
            }
        ]
        
        result = await llm.chat(
            messages=messages,
            max_tokens=800,
            temperature=0.4
        )
        synthesis = result["content"]

    except Exception:
        synthesis = "(Synthesis error)"

    return {
        "questions": len(questions),
        "results": results,
        "synthesis": synthesis,
        "total_sources": len(all_sources)
    }
