# backend/fetch_arxiv.py

import requests
import xml.etree.ElementTree as ET
import json
import time

ARXIV_API_URL = "http://export.arxiv.org/api/query"

def fetch_arxiv_papers(query: str, max_results: int = 50, start_index: int = 0):
    """
    Fetch papers from arXiv API for a given search query.
    Returns a list of dictionaries with paper metadata.
    """

    print(f"Fetching papers for query: '{query}' ...")
    params = {
        "search_query": f"all:{query}",
        "start": start_index,
        "max_results": max_results,
        "sortBy": "relevance",
        "sortOrder": "descending"
    }

    response = requests.get(ARXIV_API_URL, params=params)
    if response.status_code != 200:
        raise Exception(f"Error fetching data: {response.status_code}")

    papers = []
    root = ET.fromstring(response.text)
    namespace = {"arxiv": "http://www.w3.org/2005/Atom"}

    for entry in root.findall("arxiv:entry", namespace):
        paper = {
            "id": entry.find("arxiv:id", namespace).text if entry.find("arxiv:id", namespace) is not None else "",
            "title": entry.find("arxiv:title", namespace).text.strip().replace("\n", " "),
            "abstract": entry.find("arxiv:summary", namespace).text.strip().replace("\n", " "),
            "authors": [author.find("arxiv:name", namespace).text for author in entry.findall("arxiv:author", namespace)],
            "published": entry.find("arxiv:published", namespace).text,
            "link": entry.find("arxiv:link[@type='text/html']", namespace).attrib.get("href", ""),
        }
        papers.append(paper)

    print(f"Fetched {len(papers)} papers.")
    return papers


def save_papers_to_json(papers: list, filepath: str = "backend/data/papers.json"):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(papers, f, indent=4, ensure_ascii=False)
    print(f"Saved {len(papers)} papers to {filepath}")


if __name__ == "__main__":
    search_query = "large language models"
    papers = fetch_arxiv_papers(search_query, max_results=50)
    save_papers_to_json(papers)
