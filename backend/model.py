from langchain_ollama.llms import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate

model = OllamaLLM(model = "mistral")

site_filters = {
    "Relevance" : ["Most Popular", "Newest", "Trending"],
    "Organizer" : ["Red Bull", "Local Clubs", "Indie Orgs", "Verified"],
    "Difficulty" : ["Beginner", "Intermediate", "Pro / Elite"],
    "Distance" : ["< 5 Miles", "< 20 Miles", "< 50 Miles", "Anywhere"],
    "Location" : ["Maharashtra", "Punjab", "Gujrat", "Goa"]
}

template = """
You are an assistant for a website called "Athly", which helps users find a sports event.
You will be given a query and a list of possible filters, your job is to appropriately provide the appropriate filters from the list of filters.

Here are the possible filters: {filters}

Here is the user query: {query}


"""

prompt = ChatPromptTemplate.from_template(template)
chain = prompt | model

result = chain.invoke({"filters": site_filters, "query": "All events in mumbai for old people"})
print(result)