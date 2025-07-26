import requests
import xml.etree.ElementTree as ET
import logging
from typing import List, Dict, Optional
import time

logger = logging.getLogger( __name__ )


class PaperFetcher :
    """Unified interface for fetching papers from different sources"""

    def __init__ ( self ) :
        self.session = requests.Session()
        self.session.headers.update( {
            'User-Agent' : 'PaperMind/1.0 (research@papermind.ai)'
        } )

    def fetch_semantic_scholar ( self, query: str, limit: int = 20 ) -> List[Dict] :
        """Fetch papers from Semantic Scholar with enhanced error handling"""
        try :
            url = "https://api.semanticscholar.org/graph/v1/paper/search"
            params = {
                "query" : query,
                "limit" : min( limit, 100 ),  # API limit
                "fields" : "title,abstract,authors,year,url,paperId,citationCount,publicationTypes"
            }

            response = self.session.get( url, params=params, timeout=30 )
            response.raise_for_status()

            data = response.json()
            papers = []

            for item in data.get( "data", [] ) :
                # Filter out papers without abstracts or very short abstracts
                abstract = item.get( "abstract", "" )
                if not abstract or len( abstract ) < 100 :
                    continue

                authors = []
                for author in item.get( "authors", [] ) :
                    if author.get( "name" ) :
                        authors.append( author["name"] )

                papers.append( {
                    "id" : item.get( "paperId", "" ),
                    "title" : item["title"].strip(),
                    "abstract" : abstract.strip(),
                    "authors" : authors,
                    "published" : str( item.get( "year", "" ) ),
                    "url" : item.get( "url", "" ),
                    "source" : "semantic_scholar",
                    "citation_count" : item.get( "citationCount", 0 ),
                    "publication_types" : item.get( "publicationTypes", [] )
                } )

            logger.info( f"Fetched {len( papers )} papers from Semantic Scholar" )
            return papers

        except requests.exceptions.RequestException as e :
            logger.error( f"Semantic Scholar API request error: {e}" )
            return []
        except Exception as e :
            logger.error( f"Semantic Scholar processing error: {e}" )
            return []

    def fetch_arxiv ( self, query: str, limit: int = 20 ) -> List[Dict] :
        """Fetch papers from arXiv with improved parsing"""
        try :
            arxiv_url = "http://export.arxiv.org/api/query"
            params = {
                "search_query" : f"all:{query}",
                "start" : 0,
                "max_results" : min( limit, 100 ),
                "sortBy" : "relevance",
                "sortOrder" : "descending"
            }

            response = self.session.get( arxiv_url, params=params, timeout=30 )
            response.raise_for_status()

            papers = []
            root = ET.fromstring( response.text )

            # arXiv uses Atom namespace
            ns = {"atom" : "http://www.w3.org/2005/Atom"}

            for entry in root.findall( "atom:entry", ns ) :
                try :
                    title_elem = entry.find( "atom:title", ns )
                    summary_elem = entry.find( "atom:summary", ns )
                    id_elem = entry.find( "atom:id", ns )
                    published_elem = entry.find( "atom:published", ns )
                    updated_elem = entry.find( "atom:updated", ns )

                    if not all( [title_elem, summary_elem, id_elem] ) :
                        continue

                    # Extract authors
                    authors = []
                    for author in entry.findall( "atom:author", ns ) :
                        name_elem = author.find( "atom:name", ns )
                        if name_elem is not None :
                            authors.append( name_elem.text.strip() )

                    # Extract categories
                    categories = []
                    for category in entry.findall( "atom:category", ns ) :
                        term = category.get( "term" )
                        if term :
                            categories.append( term )

                    # Extract arXiv ID and create URL
                    arxiv_id = id_elem.text.split( '/' )[-1]
                    url = f"https://arxiv.org/abs/{arxiv_id}"
                    pdf_url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                    # Clean title and abstract
                    title = title_elem.text.strip().replace( '\n', ' ' )
                    abstract = summary_elem.text.strip().replace( '\n', ' ' )

                    # Skip if abstract is too short
                    if len( abstract ) < 100 :
                        continue

                    papers.append( {
                        "id" : arxiv_id,
                        "title" : title,
                        "abstract" : abstract,
                        "authors" : authors,
                        "published" : published_elem.text[:10] if published_elem else "",
                        "updated" : updated_elem.text[:10] if updated_elem else "",
                        "url" : url,
                        "pdf_url" : pdf_url,
                        "source" : "arxiv",
                        "categories" : categories
                    } )

                except Exception as e :
                    logger.warning( f"Error processing arXiv entry: {e}" )
                    continue

            logger.info( f"Fetched {len( papers )} papers from arXiv" )
            return papers

        except Exception as e :
            logger.error( f"arXiv API error: {e}" )
            return []

    def fetch_from_sources ( self, query: str, sources: List[str], max_per_source: int = 20 ) -> List[Dict] :
        """Fetch papers from multiple sources and deduplicate"""
        all_papers = []

        for source in sources :
            try :
                if source == "semantic_scholar" :
                    papers = self.fetch_semantic_scholar( query, max_per_source )
                elif source == "arxiv" :
                    papers = self.fetch_arxiv( query, max_per_source )
                else :
                    logger.warning( f"Unknown source: {source}" )
                    continue

                all_papers.extend( papers )
                time.sleep( 0.5 )  # Rate limiting

            except Exception as e :
                logger.error( f"Error fetching from {source}: {e}" )
                continue

        # Deduplicate based on title similarity
        return self._deduplicate_papers( all_papers )

    def _deduplicate_papers ( self, papers: List[Dict] ) -> List[Dict] :
        """Remove duplicate papers based on title similarity"""
        unique_papers = []
        seen_titles = set()

        for paper in papers :
            # Normalize title for comparison
            normalized_title = paper["title"].lower().replace( " ", "" ).replace( "-", "" )[:50]

            if normalized_title not in seen_titles :
                seen_titles.add( normalized_title )
                unique_papers.append( paper )

        logger.info( f"Deduplicated {len( papers )} papers to {len( unique_papers )}" )
        return unique_papers
