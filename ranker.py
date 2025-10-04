from pymongo import MongoClient
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

client = MongoClient("mongodb://localhost:27017/")
db = client["search_engine"]
collection = db["pages"]

def cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

def rank_pages(query, top_k=10):
    query_vec = model.encode(query)

    results = []
    for page in collection.find():
        if "vector" in page and page["vector"]:
            page_vec = np.array(page["vector"], dtype=np.float32)

            if page_vec.size == 384:
                score = cosine_similarity(query_vec, page_vec)
                results.append((page["url"], score))

    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]

if __name__ == "__main__":
    query = "Japanese virtual singer"
    ranked = rank_pages(query, top_k=5)
    print(f'Top 5 results for your query "{query}" are given below:')
    for url, score in ranked:
        print(f"{url} (score: {score:.4f})")
