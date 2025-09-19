# 🥦 CheapestBuy.AI

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-%E2%9C%94%EF%B8%8F-brightgreen.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![AIML API](https://img.shields.io/badge/AIML%20API-GPT--4o-important.svg)](https://aimlapi.com/)
[![Deployment: Windows](https://img.shields.io/badge/Windows-supported-blue.svg)](https://docs.microsoft.com/en-us/windows/)

---

## Project Overview

**CheapestBuy.AI** ek smart, multi-agent grocery shopping assistant hai jo Streamlit aur CrewAI par bana hai.  
Ye Pakistan me sab se sasti groceries dhundta, compare karta aur recommend karta hai, text aur voice search dono support karta hai[web:29].

---

## Features

- 🔎 Sasti grocery products search (Carrefour, Metro, Imtiaz)
- 📊 Product comparison: price, delivery, reviews
- 🤖 Multi-agent pipeline (input, search, analysis, review, recommend)
- 🔉 Voice search (AIML GPT-4o Whisper support)
- 💬 User review/sentiment analysis (Daraz, Amazon, AliExpress)
- 🥇 Top 3 detailed recommendations (image, link, pros, cons, delivery info)
- 🏷️ Simple, beginner-friendly Streamlit UI with filters & history

---

## Tech Stack

| Component      | Details                        |
|----------------|-------------------------------|
| Python         | 3.10+ [web:29]                |
| Streamlit      | UI, chat interface            |
| CrewAI         | Multi-agent workflow          |
| AIML API       | GPT-4o + Whisper for LLM/STT  |
| Serper.dev     | Web search (Google results)   |
| Custom Tools   | Grocery website scrapers      |

---

## Quick Start

### 1. Clone Ya Download Karein

```bash
git clone https://github.com/teamalpha/cheapestbuy-ai.git
cd cheapestbuy-ai
```

### 2. Python Environment Setup Karein

```bash
python -m venv .venv
# Mac/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Dependencies Install Karein

```bash
pip install -r requirements.txt
```

### 4. API Keys .env Mein Dalen

.env file banayein project ke root folder mein:
```bash
AIML_API_KEY=apna_aiml_api_key
SERPER_API_KEY=apna_serperdev_api_key
```

### 5. App Run Karein

```bash
streamlit run app.py
```


---

## Usage

- Text ya voice input select karein
- Grocery ka query type karein ("cheapest rice", "best milk" etc.)
- Filters lagayein (brand, min rating)
- Results dekhein — top 3 deals with images, links & review details

---

## Workflow

1. **Input**  
   Grocery related query confirm aur refine hota hai

2. **Web Search**  
   Google, Carrefour, Metro se product results laata hai

3. **Comparison**  
   Top 3 sab se sasti aur tezi se deliver hone wali cheezen select karta hai

4. **Reviews**  
   Product ki customer reviews, pros, cons, sentiment extract kiye jate hain

5. **Recommendation**  
   Har option ko concise summary mein show karta hai, best deal highlight karta hai

---

## Voice Search Info

- Format: `.wav` (max 5MB)
- AIML API Whisper-Large (GPT-4o)
- Network timeout/error ke case mein clear warnings milti hain

---

## Contributing

- Fork karein, PR bhejein
- Bugs/Issues report karein (GitHub Issues)

---

## License

MIT

---

**Developed by Team Alpha | Powered by Streamlit & CrewAI**[web:29]
