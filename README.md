# PaperMind – Semantic Academic Paper Recommender

## Project Summary

**PaperMind** is a full-stack AI-powered academic paper recommender system. It uses LLM-based embeddings and vector similarity search to help researchers discover semantically relevant academic papers from real-time sources like Semantic Scholar and arXiv.  

This project adapts the core logic of a book recommendation system to suit academic workflows, with a custom React frontend and Python API backend.

---

## Features

- Retrieves real academic papers using the Semantic Scholar API.
- Converts paper abstracts into vector embeddings using OpenAI.
- Uses FAISS or ChromaDB for fast vector similarity search.
- Ranks and returns semantically relevant papers.
- (Optional) Provides GPT-based explanations for relevance.
- Responsive frontend built with React.

---

## Tech Stack

| Layer            | Tools and Libraries                            |
| ---------------- | ---------------------------------------------- |
| Frontend (UI)    | React, Tailwind CSS, Axios, React Query        |
| Backend (API)    | Python, FastAPI (or Flask)                     |
| Embeddings       | OpenAI `text-embedding-ada-002` or HuggingFace |
| Vector Search    | FAISS or ChromaDB                              |
| LLM Explanations | OpenAI GPT-3.5 or GPT-4 (via API)              |
| Data Sources     | Semantic Scholar API, arXiv API                |

---

## Project Structure

```
papermind/
├── backend/
│ ├── app.py # FastAPI or Flask API server
│ ├── embedding_utils.py # Embedding + vector index logic
│ ├── explain_utils.py # GPT-based explanation generator
│ ├── fetch_arxiv.py # Paper fetching from APIs
│ └── data/
│ └── papers.json # Cached or preprocessed paper metadata
│
├── frontend/
│ ├── public/
│ ├── src/
│ │ ├── components/ # UI components (PaperCard, Loader)
│ │ ├── pages/ # SearchPage, DetailsPage, etc.
│ │ ├── services/ # API layer (query, explain, upload)
│ │ ├── App.jsx
│ │ └── main.jsx
│ └── tailwind.config.js
│
├── requirements.txt # Backend dependencies
├── README.md # Project documentation
└── package.json # Frontend dependencies
```
---

## Architecture Overview

### Frontend (React)

- Accepts user query or document upload
- Sends request to backend (`/recommend`, `/explain`)
- Renders top-k recommended papers with titles, abstracts, and relevance explanations

### Backend (FastAPI or Flask)

- Routes:
  - `/recommend`: semantic vector-based search
  - `/explain`: GPT-based justification for matches
  - `/classify`: research area prediction (optional)
  - `/upload`: PDF parsing and similarity matching (optional)
- Uses OpenAI embeddings + FAISS for similarity computation

---

## API Endpoints (Planned)

| Method | Endpoint     | Description                                 |
|--------|--------------|---------------------------------------------|
| POST   | `/recommend` | Returns top-k relevant papers for a query   |
| POST   | `/explain`   | Generates short GPT-based explanation       |
| POST   | `/classify`  | Classifies a paper’s research domain        |
| POST   | `/upload`    | Accepts PDF and finds semantically similar papers |

---

## Prompt Template (LLM Explanation)

```
Given the user query: {query}
And the paper: {title} – {abstract}

Explain in 2 concise sentences why this paper is relevant to the query.
```

---

## Example User Flow

1. **User enters:** *"LLM hallucinations in multilingual settings"*
2. **Backend:**
   - Embeds query
   - Searches vector database for top matches
   - Optionally classifies the field (e.g., NLP, Evaluation)
   - Uses GPT to explain relevance
3. **Frontend:**
   - Displays recommended papers
   - Shows abstract, title, and LLM-generated explanation

---

## Setup Guide

### Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app:app --reload
```
---

### Make sure to set your OpenAI key in .env or as an environment variable:
```
OPENAI_API_KEY=your_key_here
```
Frontend (React)
```
cd frontend
npm install
npm run dev
```
## Future Enhancements
- PDF upload support with automatic parsing 
- Paper filtering: topic, year, author, citation count 
- Personalized library / save-to-read-later 
- AI-powered chat assistant to explore citations 
- Integration with Zotero/Mendeley or BibTeX export


