from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from datamanager import get_db_filters
import json
import re

# model = OllamaLLM(model = "phi3:mini")
model = OllamaLLM(model="mistral")

static_filters = {
    "Relevance": ["Most Popular", "Newest", "Trending"],
    "Difficulty": ["Beginner", "Intermediate", "Pro / Elite"],
    "Distance": ["< 5 Miles", "< 20 Miles", "< 50 Miles", "Anywhere"],
    "Type": ["Marathon", "Triathlon", "Cycling", "Swimming", "Running", "Sports", "Table Tennis", "Tennis", "Chess"]
}

print("Loading AI: Fetching latest locations from Database...")
db_data = get_db_filters()

site_filters = {**static_filters, **db_data}
print(f"AI Loaded with {len(site_filters['Location'])} locations.")

template = """
You are an assistant for a website called "Athly", which helps users find a sports event.
You will be given a query and a list of possible filters. Your job is to select the appropriate filters SOLELY from the provided list.
The filters must be copied EXACTLY as they appear in the list — do not rephrase, shorten, or paraphrase.

CRITICAL DISAMBIGUATION RULES (follow strictly):
- "Table Tennis" and "Tennis" are TWO DIFFERENT sport types. Never confuse them.
  * If the user mentions "table tennis", "ping pong", or "TT", set Type to exactly "Table Tennis".
  * If the user mentions "tennis" (but NOT table tennis or ping pong), set Type to exactly "Tennis".
- "Running" covers jogging, road running, sprinting. "Marathon" is only for marathon-distance races.
- If no filter in the list matches the query, use "None" for that key.

Here are the possible filters: {filters}

Here is the user query: {query}

Reply format:
The reply must be VALID JSON ONLY — no markdown, no extra text, nothing else.
{{
    "filters": {{
        "Relevance" : <value from list or "None">,
        "Organizer" : <value from list or "None">,
        "Difficulty" : <value from list or "None">,
        "Distance" : <value from list or "None">,
        "Location" : <value from list or "None">,
        "Type" : <value from list or "None">
    }},
    "reasoning": "A short, friendly message explaining what filters were applied."
}}
"""

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

def run_model(prompt_query):
    result = chain.invoke({"filters": site_filters, "query": prompt_query})

    text = result
    text = re.sub(r"```json|```", "", text).strip()
    
    try:
        return json.loads(text)
    except:
        return {
            "filters": {}, 
            "reasoning": "I had trouble processing that request. Please try again."
        }