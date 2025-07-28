from sklearn.metrics.pairwise import cosine_similarity
from transformers import AutoTokenizer, AutoModel
import torch

# Load a small model to stay within 1GB
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
model = AutoModel.from_pretrained(MODEL_NAME)

def get_embedding(text):
    inputs = tokenizer(text, return_tensors='pt', truncation=True, max_length=512)
    with torch.no_grad():
        output = model(**inputs)
    embeddings = output.last_hidden_state.mean(dim=1)
    return embeddings

def rank_sections(sections, persona, job_to_be_done, top_k=5):
    query = f"{persona}. {job_to_be_done}"
    query_vec = get_embedding(query)

    for section in sections:
        section_vec = get_embedding(section["text"])
        similarity = cosine_similarity(query_vec, section_vec)[0][0]
        section["score"] = similarity

    # Sort by similarity
    ranked = sorted(sections, key=lambda x: x["score"], reverse=True)
    return ranked[:top_k]
