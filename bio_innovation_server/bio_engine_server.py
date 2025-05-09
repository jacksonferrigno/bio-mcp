from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os 
import yake

mcp = FastMCP("bio_engine_server")
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID") #  CX ID
SEARCH_API_BASE = "https://www.googleapis.com/customsearch/v1"
USER_AGENT = "bio-innovation-engine/0.1"

# --- helper functions ---
async def perform_search(query, api_key, cx_id, num_results):
    """Performs good search and returns raw JSON response"""
    params={
        "key":api_key,
        "cx":cx_id,
        "q": query,
        "num":num_results
    }
    async with httpx.AsyncClient() as client:
        try:
            print(f"Server log perform_search | searching for {query}")
            response = await client.get(SEARCH_API_BASE, params=params, timeout=10.0)
            response.raise_for_status() # exeception for bad status codes
            return response.json()
        except httpx.RequestError as e:
            print(f"Server Log - perform_search | HTTP Request Error: {e}")
            return None
        except httpx.HTTPStatusError as e:
            print(f"Server Log perform_search | HTTP status error: {e} ")
            return None
        except Exception as e:
            print(f"Server Log perform_search | unexpected error: {e}")
            return None
def extract_keywords(text, max_ngram_size=3, num_keywords=10):
    """gets the keywords from given text with YAKE"""
    kw_extractor = yake.KeywordExtractor(lan="en", n=max_ngram_size, dedupLim=0.9,top=num_keywords)
    keywords= kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords]

def format_result(problem_text, search_response):
    """formats google search results into structured dictionary"""
    if not search_response or "items" not in search_response:
        return{
            "original_problem": problem_text,
            "summary": "No search results found",
            "key_concepts": [],
            "relevant_links":[]
        }
    snippets=[]
    links=[]
    titles=[]
    
    #iterate thru the responses 
    for item in search_response.get("items",[]):
        titles.append(item.get("title","")) # article title
        snippets.append(item.get("snippet", "")) # snippet
        links.append(item.get("link","")) # link 
    
    combined_text = problem_text + " "+ " ".join(titles) + " " + " ".join(snippets)
    extracted_keywords= extract_keywords(combined_text)
    
    #basic summary from combining snippets
    summary= " ".join(snippets).replace("\n", " ").strip()
    return{
        "original_problem": problem_text,
        "summary": summary,
        "extracted_keywords": extracted_keywords,
        "relevant_links" : links
    }
    
    
# --- Tool Implementation --- 
@mcp.tool()
async def tool_research_user_problem(problem_description):
    """Researches the users problem description using web search to gather 
        initial context, extract keywords, and provide relevant links 
        Args: 
        problem_description: user description of the problem or area of interest
    """
    print(f"server log - async def tool_research_user_problem(problem_description)| received problem {problem_description}")
    # perform the search 
    search_data_json = await perform_search(problem_description,GOOGLE_API_KEY, SEARCH_ENGINE_ID)
    
    #format it and put it together
    formatted_results= format_result(problem_description,search_data_json) 
    print(f"[Server Log - tool_research_user_problem] Returning structured research results.")
    return formatted_results
    
@mcp.tool()
async def tool_find_initial_bio_concepts(problem_keywords, problem_summary):
    """
    Generates diverse biological search queries based on problem keywords and an optional summary,
    then performs web searches to find distinct, initial related biological concepts/themes.

    Args:
        problem_keywords: A list of keywords derived from the user's problem description.
        problem_summary: (Optional) A brief summary of the problem domain.
    """
    print(f"server log - tool_find_initial_bio_concepts | received keywords {problem_keywords}")
    bio_searches= List[str]=[]
    
    #strat 1: primary keywords for direct searches
    if problem_keywords:
        #2 primary keywords for focused searches
        for kw in problem_keywords[:2]:
            bio_searches.append(f"biological principles for {kw}")
            bio_searches.append(f"nature's solution for {kw}")
            bio_searches.append(f"how {kw} is solved in nature")
            
    # strat 2: combination of keywords
    if len(problem_keywords) >=2:
        # combine first few keywords-> broader search 
        combined_kw = "and ".join(problem_keywords[:3])
        bio_searches.append(f"bio-inspired systems for {combined_kw}")
    elif problem_keywords:
        bio_searches.append(f"bio-inspired systems for {problem_keywords[0]}")
    
    #remove dups queries and limit searches
    unique_queries =list(set(filter(None, bio_searches)))
    queries_to_run = unique_queries[:min(len(unique_queries),4)] # 4 max
    
    if not queries_to_run:
        return {"bio_concepts_found": [], "message": "Could not generate sufficient biological search queries from input."}
    
    found_bio_concepts_dict: Dict[str, Dict[str, str]] = {} 
    
    for query in queries_to_run:
        print(f"[Server Log - tool_find_initial_bio_concepts] Searching for bio concepts with query: '{query}'")
        search_results= await perform_search(query,GOOGLE_API_KEY, SEARCH_ENGINE_ID)
        
        # search gave us information
        if search_results and search_results.get("items"):
            #extract the article information
            for item in search_results["items"]:
                title = item.get("title", "").strip()
                link = item.get("link","")
                snippet=item.get("snippet","").strip().replace("\n", " ")
                #did we get title
                if title and link:
                    normalized_title =title.lower()
                    # de duplicate check for results 
                    if normalized_title not in found_bio_concepts_dict:
                        found_bio_concepts_dict[normalized_title]={
                            "concept_name": title, 
                            "retrieved_link": link,
                            "retrieved_snippet": snippet,
                            "derived_from_query": query                            
                        }
    if not found_bio_concepts_dict:
        return {"bio_concepts_found":[], "message": "No distinct bio concepts found"}
        
    return  {"bio_concepts_found": list(found_bio_concepts_dict.values())}

@mcp.tool()
async def tool_get_bio_concept_overview(bio_concept):
    """
    Performs a targeted web search for a specific biological concept/system
    and returns a Markdown formatted overview.

    Args:
        bio_concept_name: The name of the biological concept (often a title from previous tool).
    """
    # TODO: this function for spec biological concepts 
    
    

                
                
                
        
        
    
        
    
    

            