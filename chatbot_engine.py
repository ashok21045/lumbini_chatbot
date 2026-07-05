"""
chatbot_engine.py
------------------
The "brain" of the chatbot.

- Loads data/structured_data.json (produced by data_processor.py)
- Handles greetings / small talk directly
- Otherwise answers questions using TF-IDF similarity search over the
  scraped LICT content chunks (no external LLM API key required)

You can swap `answer_with_tfidf` for a call to a real LLM (e.g. Anthropic's
Claude API) later if you want smarter answers - see the commented example
at the bottom of this file.
"""

import json
import os
import random
import re

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA_PATH = os.path.join(os.path.dirname(__file__), "data", "structured_data.json")

GREETING_PATTERNS = re.compile(
    r"^\s*(hi|hello|hey|namaste|namaskar|good\s?morning|good\s?afternoon|good\s?evening|"
    r"hii+|helo+)\b", re.IGNORECASE,
)

THANKS_PATTERNS = re.compile(r"\b(thank you|thanks|thankyou|dhanyabad)\b", re.IGNORECASE)

BYE_PATTERNS = re.compile(r"^\s*(bye|goodbye|see you|k thanks bye|exit|quit)\s*$", re.IGNORECASE)

GREETING_RESPONSES = [
    "Hello! 👋 I'm the Lumbini ICT Campus assistant. Ask me about courses, faculty, admissions, notices or events.",
    "Hi there! How can I help you with information about Lumbini ICT Campus today?",
    "Namaste! 🙏 Ask me anything about LICT Campus - courses, syllabus, faculty, or notices.",
]

THANKS_RESPONSES = [
    "You're welcome! Let me know if you have any other questions about LICT Campus.",
    "Happy to help! 😊",
]

BYE_RESPONSES = [
    "Goodbye! Feel free to come back if you have more questions about LICT Campus.",
    "Take care! 👋",
]

FALLBACK_RESPONSES = [
    "I couldn't find specific information about that on the LICT Campus website. "
    "Could you rephrase, or ask about courses, faculty, admissions, notices or contact details?",
]


class ChatbotEngine:
    def __init__(self, data_path: str = DATA_PATH):
        self.chunks = []
        self.vectorizer = None
        self.tfidf_matrix = None
        self._load_data(data_path)

    def _load_data(self, data_path: str):
        if not os.path.exists(data_path):
            self.chunks = []
            return

        with open(data_path, "r", encoding="utf-8") as f:
            structured = json.load(f)

        self.site_name = structured.get("site", "the campus")
        self.contact_info = structured.get("contact_info", {})
        self.chunks = structured.get("chunks", [])

        if self.chunks:
            corpus = [c["content"] for c in self.chunks]
            self.vectorizer = TfidfVectorizer(stop_words="english")
            self.tfidf_matrix = self.vectorizer.fit_transform(corpus)

    def is_ready(self) -> bool:
        return bool(self.chunks) and self.vectorizer is not None

    def handle_greeting_or_smalltalk(self, message: str):
        if GREETING_PATTERNS.search(message):
            return random.choice(GREETING_RESPONSES)
        if BYE_PATTERNS.search(message):
            return random.choice(BYE_RESPONSES)
        if THANKS_PATTERNS.search(message):
            return random.choice(THANKS_RESPONSES)
        return None

    def answer_with_tfidf(self, message: str, top_k: int = 3, threshold: float = 0.08) -> str:
        if not self.is_ready():
            return (
                "My knowledge base is empty. Please run scraper.py and then "
                "data_processor.py to build data/structured_data.json first."
            )

        query_vec = self.vectorizer.transform([message])
        sims = cosine_similarity(query_vec, self.tfidf_matrix).flatten()
        top_indices = sims.argsort()[::-1][:top_k]

        best_score = sims[top_indices[0]] if len(top_indices) else 0
        if best_score < threshold:
            return random.choice(FALLBACK_RESPONSES)

        seen_titles = set()
        answer_parts = []
        for idx in top_indices:
            if sims[idx] < threshold:
                continue
            chunk = self.chunks[idx]
            key = chunk["title"] or chunk["url"]
            if key in seen_titles:
                continue
            seen_titles.add(key)
            answer_parts.append(f"**{chunk['category']}** — {chunk['content'][:500]}")

        if not answer_parts:
            return random.choice(FALLBACK_RESPONSES)

        return "\n\n".join(answer_parts)

    def get_response(self, message: str) -> str:
        message = message.strip()
        if not message:
            return "Please type a question. 🙂"

        smalltalk = self.handle_greeting_or_smalltalk(message)
        if smalltalk:
            return smalltalk

        return self.answer_with_tfidf(message)


# ---------------------------------------------------------------------------
# OPTIONAL: swap in a real LLM for smarter answers.
#
# from anthropic import Anthropic
# client = Anthropic(api_key="YOUR_API_KEY")
#
# def answer_with_llm(self, message, context_chunks):
#     context = "\n\n".join(c["content"] for c in context_chunks)
#     resp = client.messages.create(
#         model="claude-sonnet-4-6",
#         max_tokens=500,
#         messages=[{
#             "role": "user",
#             "content": f"Context about Lumbini ICT Campus:\n{context}\n\nQuestion: {message}"
#         }]
#     )
#     return resp.content[0].text
# ---------------------------------------------------------------------------


if __name__ == "__main__":
    bot = ChatbotEngine()
    print("LICT Chatbot (type 'quit' to exit)")
    while True:
        msg = input("You: ")
        if msg.lower() == "quit":
            break
        print("Bot:", bot.get_response(msg))
