# backend/explain_utils.py

import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")

EXPLAIN_PROMPT_TEMPLATE = """
You are an academic assistant. A user is searching for papers related to the following query:

Query: "{query}"

Below is the abstract of a research paper:

Title: "{title}"
Abstract: "{abstract}"

Explain in two concise sentences why this paper is relevant to the query.
"""

def explain_relevance(query: str, title: str, abstract: str, model: str = "gpt-3.5-turbo") -> str:
    """
    Generate a short explanation of why the paper is relevant to the query.
    """
    prompt = EXPLAIN_PROMPT_TEMPLATE.format(query=query, title=title, abstract=abstract)

    try:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert research assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        explanation = response.choices[0].message['content'].strip()
        return explanation

    except Exception as e:
        print(f"[ERROR] LLM explanation failed: {e}")
        return "Explanation not available due to an API error."
