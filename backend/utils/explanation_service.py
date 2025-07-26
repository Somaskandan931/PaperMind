import openai
import logging
from typing import Optional

logger = logging.getLogger( __name__ )


class ExplanationService :
    """Service for generating relevance explanations"""

    def __init__ ( self, api_key: str, model: str = "gpt-3.5-turbo" ) :
        openai.api_key = api_key
        self.model = model

    def explain_relevance ( self, query: str, paper: dict, max_retries: int = 2 ) -> Optional[str] :
        """Generate explanation for why a paper is relevant to the query"""

        prompt = self._build_explanation_prompt( query, paper )

        for attempt in range( max_retries ) :
            try :
                response = openai.ChatCompletion.create(
                    model=self.model,
                    messages=[
                        {
                            "role" : "system",
                            "content" : "You are an expert research assistant. Provide clear, concise explanations of paper relevance."
                        },
                        {"role" : "user", "content" : prompt}
                    ],
                    temperature=0.3,
                    max_tokens=120
                )

                explanation = response.choices[0].message['content'].strip()
                return explanation

            except Exception as e :
                logger.warning( f"Explanation attempt {attempt + 1} failed: {e}" )
                if attempt == max_retries - 1 :
                    return self._fallback_explanation( query, paper )

    def _build_explanation_prompt ( self, query: str, paper: dict ) -> str :
        """Build the explanation prompt"""
        return f"""
Query: "{query}"

Paper Details:
Title: "{paper['title']}"
Abstract: "{paper['abstract'][:400]}..."
Authors: {', '.join( paper.get( 'authors', [] )[:3] )}
Source: {paper.get( 'source', 'Unknown' )}

Task: Explain in exactly 2 sentences why this paper is relevant to the user's query. Focus on specific connections between the query and the paper's content.
        """

    def _fallback_explanation ( self, query: str, paper: dict ) -> str :
        """Provide a fallback explanation when API fails"""
        return f"This paper appears relevant to '{query}' based on semantic similarity analysis. The research focuses on {paper['title'].lower()} which aligns with your search interests."

    def batch_explain ( self, query: str, papers: list, max_papers: int = 5 ) -> dict :
        """Generate explanations for multiple papers"""
        explanations = {}

        for i, paper in enumerate( papers[:max_papers] ) :
            paper_id = paper.get( 'id', f'paper_{i}' )
            try :
                explanation = self.explain_relevance( query, paper )
                explanations[paper_id] = explanation
            except Exception as e :
                logger.error( f"Failed to explain paper {paper_id}: {e}" )
                explanations[paper_id] = self._fallback_explanation( query, paper )

        return explanations
