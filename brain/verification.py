"""
Chain of Verification (Chunk 3.1)
Reduces hallucinations by verifying model responses before returning them.

Process:
1. Generate initial response
2. Create verification questions about the response
3. Answer verification questions independently
4. Revise response based on verification results
"""

import httpx
from typing import List, Dict, Optional
from config import config


class ChainOfVerification:
    """
    Implements Chain of Verification pattern for reducing hallucinations.

    This module helps ensure factual accuracy by:
    - Generating verification questions about model responses
    - Independently answering those questions
    - Detecting inconsistencies
    - Revising responses when needed
    """

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None):
        """
        Initialize verification chain.

        Args:
            http_client: Optional existing httpx client (for connection reuse)
        """
        self.http_client = http_client
        self.own_client = http_client is None

    async def __aenter__(self):
        """Async context manager entry"""
        if self.own_client:
            self.http_client = httpx.AsyncClient(timeout=30.0)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.own_client and self.http_client:
            await self.http_client.aclose()

    async def generate_response(self, prompt: str) -> str:
        """
        Generate initial response from Vorpal.

        Args:
            prompt: User's question/prompt

        Returns:
            Initial response text
        """
        payload = {
            "model": config.VORPAL_MODEL,
            "prompt": prompt,
            "max_tokens": 256,
            "temperature": 0.7
        }

        response = await self.http_client.post(
            f"{config.VORPAL_URL}/v1/completions",
            json=payload
        )
        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["text"].strip()

    async def generate_verification_questions(
        self,
        original_prompt: str,
        response: str
    ) -> List[str]:
        """
        Generate verification questions about the response.

        These questions help identify potential hallucinations or errors
        in the initial response.

        Args:
            original_prompt: The user's original question
            response: The model's initial response

        Returns:
            List of verification questions (2-4 questions)
        """
        verification_prompt = f"""Given this question and answer, generate 2-3 specific verification questions to check if the answer is factually correct.

Question: {original_prompt}
Answer: {response}

Generate verification questions that:
1. Check specific factual claims
2. Can be answered with yes/no or brief facts
3. Would reveal errors if the original answer was wrong

        Format: One question per line, numbered.
        Verification questions:"""

        payload = {
            "model": config.VORPAL_MODEL,
            "prompt": verification_prompt,
            "max_tokens": 150,
            "temperature": 0.3  # Lower temp for more focused questions
        }

        response_obj = await self.http_client.post(
            f"{config.VORPAL_URL}/v1/completions",
            json=payload
        )
        response_obj.raise_for_status()
        result = response_obj.json()

        questions_text = result["choices"][0]["text"].strip()

        # Parse questions (simple line-based parsing)
        questions = []
        for line in questions_text.split('\n'):
            line = line.strip()
            # Remove numbering like "1.", "2)", etc.
            if line and (line[0].isdigit() or line.startswith('-')):
                # Strip leading number and punctuation
                clean_line = line.lstrip('0123456789.-) ').strip()
                if clean_line:
                    questions.append(clean_line)

        return questions[:3]  # Limit to 3 questions

    async def answer_verification_question(self, question: str) -> str:
        """
        Answer a verification question independently (without seeing original response).

        Args:
            question: Verification question to answer

        Returns:
            Answer to the verification question
        """
        payload = {
            "model": config.VORPAL_MODEL,
            "prompt": question,
            "max_tokens": 100,
            "temperature": 0.3
        }

        response = await self.http_client.post(
            f"{config.VORPAL_URL}/v1/completions",
            json=payload
        )
        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["text"].strip()

    async def verify_and_revise(
        self,
        original_prompt: str,
        response: str,
        verification_qa: List[Dict[str, str]]
    ) -> str:
        """
        Given verification Q&A, determine if response needs revision.

        Args:
            original_prompt: Original user question
            response: Initial response
            verification_qa: List of {question, answer} verification pairs

        Returns:
            Revised response (or original if no issues found)
        """
        # Build verification context
        verification_text = "\n".join([
            f"Q: {qa['question']}\nA: {qa['answer']}"
            for qa in verification_qa
        ])

        revision_prompt = f"""Review this answer in light of verification results. If the verification reveals any errors or inconsistencies, provide a corrected answer. If the answer is correct, return it as-is.

Original Question: {original_prompt}
Original Answer: {response}

Verification Results:
{verification_text}

Provide the final answer (corrected if needed):"""

        payload = {
            "model": config.VORPAL_MODEL,
            "prompt": revision_prompt,
            "max_tokens": 300,
            "temperature": 0.5
        }

        response_obj = await self.http_client.post(
            f"{config.VORPAL_URL}/v1/completions",
            json=payload
        )
        response_obj.raise_for_status()
        result = response_obj.json()

        return result["choices"][0]["text"].strip()

    async def verify(
        self,
        prompt: str,
        initial_response: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Complete verification chain for a prompt.

        Args:
            prompt: User's question
            initial_response: Optional pre-generated response (if None, will generate)

        Returns:
            Dict with:
                - initial_response: Original response
                - verification_questions: List of verification questions
                - verification_answers: List of answers to verification questions
                - final_response: Revised response after verification
                - revised: Boolean indicating if response was revised
        """
        # Step 1: Generate initial response (if not provided)
        if initial_response is None:
            initial_response = await self.generate_response(prompt)

        # Step 2: Generate verification questions
        questions = await self.generate_verification_questions(
            prompt,
            initial_response
        )

        # Step 3: Answer verification questions independently
        verification_qa = []
        for question in questions:
            answer = await self.answer_verification_question(question)
            verification_qa.append({
                "question": question,
                "answer": answer
            })

        # Step 4: Revise based on verification
        final_response = await self.verify_and_revise(
            prompt,
            initial_response,
            verification_qa
        )

        # Determine if response was revised
        revised = final_response.strip() != initial_response.strip()

        return {
            "initial_response": initial_response,
            "verification_questions": questions,
            "verification_qa": verification_qa,
            "final_response": final_response,
            "revised": revised
        }


# Convenience function for one-off verifications
async def verify_response(prompt: str, response: Optional[str] = None) -> Dict:
    """
    Convenience function for running verification chain.

    Args:
        prompt: User's question
        response: Optional pre-generated response

    Returns:
        Verification results dict
    """
    async with ChainOfVerification() as cov:
        return await cov.verify(prompt, response)
