from langchain_community.embeddings import OllamaEmbeddings
from langchain_community.vectorstores.chroma import Chroma

from config import settings


def get_vector_db():
    embedding = OllamaEmbeddings(
        model=settings.TEXT_EMBEDDING_MODEL, show_progress=True
    )
    return Chroma(
        collection_name=settings.COLLECTION_NAME,
        persist_directory=settings.CHROMA_PATH.as_posix(),
        embedding_function=embedding,
    )
