"""
data_processor.py
------------------
Step 2: Take data/raw_data.json (produced by scraper.py) and turn it into a clean,
structured JSON knowledge base that the chatbot can search over.

Run:
    python data_processor.py

Input:
    data/raw_data.json
Output:
    data/structured_data.json
"""

import json
import os
import re

RAW_PATH = os.path.join(os.path.dirname(__file__), "data", "raw_data.json")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "data", "structured_data.json")

# Map URL keywords -> a friendly category name
CATEGORY_RULES = [
    (r"about-us", "About"),
    (r"bsc-csit", "Courses - BSc CSIT"),
    (r"bca-course|/bca/", "Courses - BCA"),
    (r"bim-course|/bim/", "Courses - BIM"),
    (r"/bhm/", "Courses - BHM"),
    (r"courses", "Courses - Overview"),
    (r"bod", "Team - Board of Directors"),
    (r"teaching-faculty", "Team - Teaching Faculty"),
    (r"visiting-faculty", "Team - Visiting Faculty"),
    (r"non-teaching-faculty", "Team - Non Teaching Staff"),
    (r"our-team", "Team - Overview"),
    (r"syllabus", "Syllabus"),
    (r"gallery", "Gallery"),
    (r"info-notice|notice", "Notices"),
    (r"events", "Events"),
    (r"ndtss", "NDTSS"),
    (r"qaa", "QAA"),
    (r"contact", "Contact"),
]


def categorize(url: str) -> str:
    for pattern, label in CATEGORY_RULES:
        if re.search(pattern, url, re.IGNORECASE):
            return label
    if url.rstrip("/").endswith("lict.edu.np"):
        return "Home"
    return "General"


def chunk_text(text: str, max_words: int = 120):
    """Split long text into smaller retrieval-friendly chunks (roughly by paragraph)."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks = []
    current = []
    word_count = 0
    for para in paragraphs:
        words = para.split()
        if word_count + len(words) > max_words and current:
            chunks.append(" ".join(current))
            current = []
            word_count = 0
        current.append(para)
        word_count += len(words)
    if current:
        chunks.append(" ".join(current))
    return chunks


def extract_contact_info(all_text: str) -> dict:
    email_match = re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", all_text)
    phone_matches = re.findall(r"0\d{1,3}[-\s]?\d{5,7}", all_text)
    return {
        "email": email_match.group(0) if email_match else None,
        "phones": list(dict.fromkeys(phone_matches))[:5],
    }


def main():
    if not os.path.exists(RAW_PATH):
        print(f"Raw data not found at {RAW_PATH}. Run scraper.py first.")
        return

    with open(RAW_PATH, "r", encoding="utf-8") as f:
        raw_items = json.load(f)

    structured = {
        "site": "Lumbini ICT Campus",
        "base_url": "https://lict.edu.np",
        "categories": {},
        "chunks": [],  # flat list used for chatbot retrieval
    }

    combined_text = ""

    for item in raw_items:
        url = item.get("url", "")
        title = item.get("title", "")
        text = item.get("raw_text", "")
        if not text:
            continue
        combined_text += "\n" + text

        category = categorize(url)
        entry = {
            "url": url,
            "title": title,
            "text": text,
        }
        structured["categories"].setdefault(category, []).append(entry)

        for chunk in chunk_text(text):
            structured["chunks"].append(
                {
                    "category": category,
                    "url": url,
                    "title": title,
                    "content": chunk,
                }
            )

    structured["contact_info"] = extract_contact_info(combined_text)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(structured, f, ensure_ascii=False, indent=2)

    print(f"Structured {len(structured['chunks'])} chunks across "
          f"{len(structured['categories'])} categories.")
    print(f"Saved to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
