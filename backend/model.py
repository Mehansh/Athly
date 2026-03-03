from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from datamanager import get_db_filters # Import the new function
import json
import re

# model = OllamaLLM(model = "phi3:mini")
model = OllamaLLM(model="mistral")

# 1. DEFINE STATIC FILTERS (Things that rarely change)
static_filters = {
    "Relevance": ["Most Popular", "Newest", "Trending"],
    "Difficulty": ["Beginner", "Intermediate", "Pro / Elite"],
    "Distance": ["< 5 Miles", "< 20 Miles", "< 50 Miles", "Anywhere"],
    "Type": ["Marathon", "Triathlon", "Cycling", "Swimming", "Sports"]
}

# 2. FETCH DYNAMIC FILTERS ON STARTUP
print("Loading AI: Fetching latest locations from Database...")
db_data = get_db_filters()

# 3. MERGE THEM
site_filters = {**static_filters, **db_data}
print(f"AI Loaded with {len(site_filters['Location'])} locations.")

template = """
You are an assistant for a website called "Athly", which helps users find a sports event.
You will be given a query and a list of possible filters. Your job is to select the appropriate filters solely from the provided list.
The filters should be only from the list below.
Here are the possible filters: {filters}

Here is the user query: {query}

Reply format:
The reply should be in a JSON format ONLY. Anything else WILL BE REJECTED.
Here is the json format:
{{
    "filters": {{
        "Relevance" : <filter from the list>,
        "Organizer" : <filter from the list>,
        "Difficulty" : <filter from the list>,
        "Distance" : <filter from the list>,
        "Location" : <filter from the list>,
        "Type" : <filter from the list>
    }},
    "reasoning": "A short message to the user."
}}
If filters are not applicable, reply with "None" for that filter key.
"""

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

def run_model(prompt_query):
    # Pass the DYNAMIC site_filters to the AI
    result = chain.invoke({"filters": site_filters, "query": prompt_query})

    text = result
    text = re.sub(r"```json|```", "", text).strip()
    
    # Simple error handling if JSON fails
    try:
        return json.loads(text)
    except:
        return {
            "filters": {}, 
            "reasoning": "I had trouble processing that request. Please try again."
        }