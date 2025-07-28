from transformers import pipeline

# Use a small model for offline summarization
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

def summarize(text, max_tokens=100):
    if not text.strip():
        return {"refined_text": ""}
    
    # Limit to max tokens allowed by the model
    max_input_len = 1024
    input_text = text if len(text.split()) < max_input_len else " ".join(text.split()[:max_input_len])

    summary = summarizer(input_text, max_length=max_tokens, min_length=20, do_sample=False)
    return {
        "refined_text": summary[0]["summary_text"]
    }
