from src.parser import extract_text_sections
from src.ranker import rank_sections
from src.summarizer import summarize

import os
import json
from datetime import datetime

INPUT_DIR = os.path.join(os.getcwd(), "input")
OUTPUT_DIR = os.path.join(os.getcwd(), "output")


# Load persona and job dynamically from JSON file
with open("persona_task.json", "r") as f:
    task_info = json.load(f)
    persona = task_info["persona"]
    job = task_info["job_to_be_done"]

def main():
    files = [f for f in os.listdir(INPUT_DIR) if f.endswith(".pdf")]
    all_sections = []

    for file in files:
        full_path = os.path.join(INPUT_DIR, file)
        print(f"Processing {file}...")
        sections = extract_text_sections(full_path)
        for section in sections:
            section["document"] = file
        all_sections.extend(sections)

    top_sections = rank_sections(all_sections, persona, job)

    subsection_analysis = []
    for s in top_sections:
        summary = summarize(s["text"])
        summary["document"] = s["document"]
        summary["page_number"] = s["page"]
        subsection_analysis.append(summary)

    output = {
        "metadata": {
            "documents": files,
            "persona": persona,
            "job_to_be_done": job,
            "timestamp": datetime.now().isoformat()
        },
        "extracted_sections": [{
            "document": s["document"],
            "page_number": s["page"],
            "section_title": s["title"],
            "importance_rank": i + 1
        } for i, s in enumerate(top_sections)],
        "subsection_analysis": subsection_analysis
    }

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, "output.json")
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n✅ Output written to {output_path}")

if __name__ == "__main__":
    main()
