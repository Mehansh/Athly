from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

#model = OllamaLLM(model = "phi3:mini")
model = OllamaLLM(model = "mistral")


site_filters = {
    "Relevance" : ["Most Popular", "Newest", "Trending"],
    "Organizer" : ["Red Bull", "Local Clubs", "Indie Orgs", "Verified"],
    "Difficulty" : ["Beginner", "Intermediate", "Pro / Elite"],
    "Distance" : ["< 5 Miles", "< 20 Miles", "< 50 Miles", "Anywhere"],
    "Location" : ["Maharashtra", "Punjab", "Gujrat", "Goa"],
    "Type" : ["Marathon", "Triathlon", "Cycling", "Swimming"]
}

template = """
You are an assistant for a website called "Athly", which helps users find a sports event.
You will be given a query and a list of possible filters, your job is to appropriately provide the appropriate filters solely and only from the list of filters.
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
    "reasoning": "A message to the user addressing the query, and tell the user the changes you've made."
}}
If filters are not applicable, you can reply with "None" for that filter, but the filter key must be present in the json.
Anything more than the json above will be rejected. Do not include any text outside the json. The json should be the only content in your response.

"""

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

import json
import re

def run_model(prompt_query):
    result = chain.invoke({"filters": site_filters, "query": prompt_query})

    text = result

    text = re.sub(r"```json|```", "", text).strip()

    return json.loads(text)