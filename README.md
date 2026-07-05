# LICT Campus Chatbot

A Streamlit chatbot that scrapes **https://lict.edu.np/**, builds a structured knowledge
base, and answers questions about the campus behind an admin login (ChatGPT-style UI,
with saved conversation history).

## Project structure
```
lict_chatbot/
├── scraper.py          # Step 1: scrape lict.edu.np (BeautifulSoup + Selenium fallback + WP REST API)
├── data_processor.py   # Step 2: turn raw_data.json into structured_data.json
├── database.py         # Step 3: SQLite - admin table (auth) + conversations table (history)
├── chatbot_engine.py   # Chatbot brain: greetings + TF-IDF retrieval over structured data
├── app.py              # Step 4 & 5: Streamlit app (login + ChatGPT-like chat UI + history)
├── requirements.txt
└── data/                # created automatically: raw_data.json, structured_data.json, app.db
```

## Setup

```bash
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

If you want the Selenium fallback to work, you also need Google Chrome installed
(webdriver-manager will download the matching driver automatically).

## Run it (in order)

```bash
# 1. Scrape the website
python scraper.py

# 2. Structure the scraped data into a clean JSON knowledge base
python data_processor.py

# 3. (Optional) initialize the DB and see the seeded demo admin
python database.py

# 4. Launch the chatbot app
streamlit run app.py
```

## Login

Only accounts that exist in the SQLite `admin` table can log in — there's a
**Register** tab on the login screen to add yourself, or use the seeded demo account
created automatically the first time the app runs:

- Email: `admin@lict.edu.np`
- Password: `admin123`

Email addresses are validated with the regex:
```
^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$
```

## How the chatbot answers

`chatbot_engine.py` handles greetings/small talk directly (hi, hello, namaste, thanks,
bye), and otherwise runs TF-IDF similarity search over the scraped content chunks to
find the most relevant section of the website to answer from. No external API key is
required. If you'd like smarter, more conversational answers, there's a commented
example at the bottom of `chatbot_engine.py` showing how to route the matched context
through the Anthropic Claude API instead.

## Notes

- Re-run `scraper.py` + `data_processor.py` any time you want to refresh the knowledge
  base with the latest site content (e.g. new notices).
- Conversation history is stored per-admin in the `conversations` table in
  `data/app.db`, and reloads automatically the next time that admin logs in.
- Use the "Clear conversation" button in the sidebar to wipe your own chat history.
