"""
Research Assistant Agent (Chunk 5.4)
Specialized agent for research tasks using library + memory search.

Capabilities:
- Search ingested library documents
- Search conversation memories
- Combine multiple sources
- Provide cited, researched answers
"""

import httpx
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from config import config


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

        # Call library search API
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "http://localhost:8080/library/search",
                json={"query": query, "top_k": min(top_k, 10)}
            )

            if response.status_code != 200:
                return f"Error: Library search failed (HTTP {response.status_code})"

            data = response.json()

        chunks = data.get("chunks", [])

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
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{config.BRAIN_URL}/library/search",
                        json={"query": question, "top_k": top_k}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        chunks = data.get("chunks", [])
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
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(
                        f"{config.BRAIN_URL}/memory/search",
                        params={"query": question, "top_k": top_k}
                    )

                    if response.status_code == 200:
                        data = response.json()
                        memory_results = data.get("memories", [])
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

        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config.VORPAL_URL}/v1/chat/completions",
                json={
                    "model": config.VORPAL_MODEL,
                    "messages": [
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
                    ],
                    "max_tokens": 500,
                    "temperature": 0.3  # Lower temperature for factual responses
                }
            )

            if response.status_code != 200:
                return ResearchResult(
                    answer="",
                    sources=sources,
                    memories_consulted=memories,
                    library_chunks_consulted=library_chunks,
                    total_sources=len(sources),
                    success=False,
                    error=f"LLM request failed (HTTP {response.status_code})"
                )

            llm_response = response.json()
            answer = llm_response["choices"][0]["message"]["content"].strip()

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
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{config.VORPAL_URL}/v1/chat/completions",
                json={
                    "model": config.VORPAL_MODEL,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a research synthesizer. Combine the findings into a coherent summary."
                        },
                        {
                            "role": "user",
                            "content": synthesis_prompt
                        }
                    ],
                    "max_tokens": 800,
                    "temperature": 0.4
                }
            )

            if response.status_code == 200:
                llm_response = response.json()
                synthesis = llm_response["choices"][0]["message"]["content"].strip()
            else:
                synthesis = "(Synthesis failed)"

    except Exception:
        synthesis = "(Synthesis error)"

    return {
        "questions": len(questions),
        "results": results,
        "synthesis": synthesis,
        "total_sources": len(all_sources)
    }
