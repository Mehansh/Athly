from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

embeddings = OllamaEmbeddings(
    model="mxbai-embed-large"
)

vectordb = Chroma(
    collection_name="events_storage",
    embedding_function=embeddings,
    persist_directory=os.path.join(BASE_DIR, "chroma_db_events")
)

def addEvents(text, metadata):
    doc = Document(
        page_content=text,
        metadata=metadata
    )

    vectordb.add_documents([doc])

def retrieveEvents(query, k=3):
    return vectordb.similarity_search(query, k)
