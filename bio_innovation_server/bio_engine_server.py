from typing import Any, Dict, List, Optional
import httpx
from mcp.server.fastmcp import FastMCP
from dotenv import load_dotenv
import os 
import yake
import psycopg2
import psycopg2.extras
import json

mcp = FastMCP("bio_engine_server")
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
SEARCH_ENGINE_ID = os.getenv("SEARCH_ENGINE_ID") #  CX ID
SEARCH_API_BASE = "https://www.googleapis.com/customsearch/v1"
USER_AGENT = "bio-innovation-engine/0.3"

# PostgreSQL connections details
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")     



# --- helper functions ---
async def perform_search(query:str, api_key:Optional[str], cx_id:Optional[str], num_results:int=3)-> Optional[Dict[str,Any]]:
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
def extract_keywords(text:str , max_ngram_size: int=3, num_keywords: int=10)-> List[str]:
    """gets the keywords from given text with YAKE"""
    kw_extractor = yake.KeywordExtractor(lan="en", n=max_ngram_size, dedupLim=0.9,top=num_keywords)
    keywords= kw_extractor.extract_keywords(text)
    return [kw[0] for kw in keywords]

def format_result(problem_text: str, search_response: Optional[Dict[str,Any]]) -> Dict[str,Any]:
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

# ----- DB helpers ----- 
def get_connection():
    """ Makes connection to database

    Returns:
        connection cursor
    """
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            host=DB_HOST,
            port=DB_PORT
        )
        print(f"Server log | DB - Connection established")
        return conn
    except psycopg2.Error as e:
        print(f"Server log DB | error: unable to connect: {e}")
        return None
    
# --- Tool Implementation --- 
@mcp.tool()
async def tool_research_user_problem(problem_description: str) ->Dict[str,Any]:
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
async def tool_find_initial_bio_concepts(problem_keywords: List[str], problem_summary: Optional[str]=None) -> Dict[str,Any]:
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
async def tool_get_bio_concept_overview(bio_concept: str)-> str:
    """
    Performs a targeted web search for a specific biological concept/system
    and returns a Markdown formatted overview.

    Args:
        bio_concept: The name of the biological concept (often a title from previous tool).
    """
    print(f"Server Log - tool_get_bio_concept_overview | researching concept {bio_concept}")
    #targeted simple query
    query=f"what is {bio_concept} in biology OR {bio_concept} biology overview"
    search_res_json = await perform_search(query,GOOGLE_API_KEY,SEARCH_ENGINE_ID, num_results=1)
    
    if search_res_json and search_res_json.get("items") and len(search_res_json["items"])>0:
        top_result = search_res_json["items"][0]
        title = top_result.get("title", bio_concept)
        snippet= top_result.get("snippet", "nothing found").strip().replace("\n"," ")
        link = top_result.get("link","")
        
        #markdown output
        markdown_output = f"""
        # Biological Concept Overview: {bio_concept}

        **Source Title:** {title}
        **Link:** {link}

        ## Overview:
        {snippet}
        """
        return markdown_output
    else:
        return f" ## NO overview found for suitable information"
    

@mcp.tool()
def tool_store_finding(finding_key: str, finding_data: Dict[str, Any])-> Dict[str, Any]:
    """ After research, the client should store their findings in a key-pair match style where it stores the
        topic as the key and the value is the findings stored as a JSONB. If key
    exists, it updates the value. 
    
    

    Args:
        finding_key (str): Unique key for finding 
        finding_data (Dict[str, Any]): the data to store as python dictionary
    """
    print(f"Server log DB_store |  attempting to store key value pair {finding_key} and {finding_data}")
    # connect to db
    conn= get_connection()
    if not conn:
        return {"status": "error", "message":"Database connection failed"}
    
    try:
        with conn.cursor() as cur:
            # insert new mapping into table 
            # if theres a conflict... just add to mappings
            cur.execute(
                """
                INSERT INTO biomap (finding_topic, finding_content)
                VALUES (%s,%s)
                ON CONFLICT (finding_topic) DO UPDATE SET
                    finding_content = EXCLUDED.finding_content;
                """, (finding_key, psycopg2.extras.Json(finding_data)) 
            )
            conn.commit()
            print(f"server log - store findings | success")
            return  {"status": "success", "key": finding_key,  "message":"store complete"}
    except psycopg2.Error as e:
        #rollback changes if any error 
        conn.rollback()
        print(f"server log - store findings | error storing details {e}")
        return {"status": "error", "key": finding_key, "message": f"Database error: {e}"}
    finally:
        #always close
        if conn:
            conn.close()
@mcp.tool()
def tool_fetch_finding(finding_key: str)->Optional[Dict[str,Any]]:
    """  This tool should be ran prior to any specific research on 
        Biological topic matches and query our table to see if the topic
        has already been reserach

    Args:
        finding_key (str): what were looking for

    Returns:
        Optional[Dict[str,Any]]: ouput of the dictionary
    """
    print(f"Server log DB_fetch |  attempting to store key value pair {finding_key}")
    conn= get_connection()
    if not conn:
        return {"status": "error", "message":"Database connection failed"}
    
    try:
        # establish cursor with python dictonary extraction capabaliies 
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * from biomap WHERE finding_topic =%s;", (finding_key,))
            #fetch the results 
            result = cur.fetchall()
            if result:
                #found something so we can reutrn what we got 
                print(f"Server log DB_fetch | successfully found data")
                return result
            else:
                # got nothing (this is valid not error)
                print(f"Server log DB_fetch | no data to be found")
                return None               
    except psycopg2.Error as e:
        print(f"server log - store findings | error fetching ")
        return {"error": f"db fetch error {e}"}
    finally:
        if conn:
            conn.close()
            
@mcp.tool()
def tool_fetch_all()->Optional[Dict[str,Any]]:
    """This tool should be used by the client to fetch all of our research and query our knowledge base in our Postgres Table
        the object of this is to output and display all of our findings throughout using this server.  

    Returns:
        Optional[Dict[str,Any]]: results of our table
    """
    print("Server log- tool_fetch_all | querying and return our knowledge base")
    # get the connection
    conn =get_connection()
    if not conn:
        return {"status": "error", "message":"Database connection failed"}
    try:
        # establish connection
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT * FROM biomap;")
            #fetch all the results 
            results =cur.fetchall()
            if results:
                # if we got something 
                print("server log - tool_fetch_all | successfully acquired data")
                return results
            else:
                # didnt get any - not an error
                print("server log - tool_fetch_all | did not receive any data")
                return None
    except psycopg2.Error as e:
        print(f"server log - tool_fetch_all | error fetching {e}")
        return {"error": f"db fetch error {e}"}
    finally:
        if conn:
            conn.close()
        
    
    

                
#Running server
if __name__ == "__main__":
        if not all([GOOGLE_API_KEY, SEARCH_ENGINE_ID, DB_NAME, DB_HOST,DB_PORT,DB_USER]):
            print("ERROR: Missing environment variables.")
            print("Please set them before running the server.")      
        else:
            print(f"Starting BioInnovationServer (MCP) ({USER_AGENT})...")
            print(f"Google Search API Key: {'*' * (len(GOOGLE_API_KEY) - 4) + GOOGLE_API_KEY[-4:] if GOOGLE_API_KEY else 'Not Set'}")
            print(f"Search Engine ID: {'*' * (len(SEARCH_ENGINE_ID) - 4) + SEARCH_ENGINE_ID[-4:] if SEARCH_ENGINE_ID else 'Not Set'}")
            # quick test to see if we can connect
            conn_test=get_connection()
            if conn_test:
                conn_test.close()
                # if we got one we can close we're good
                print(f"connection to {DB_NAME} complete and success")
                mcp.run(transport='stdio')
                print("BioInnovationServer (MCP) stopped.")
            else:
                print("connection failed")
                
                

            

        
        
    
        
    
    

            