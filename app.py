# app.py
import os
import re
import json
import requests
import streamlit as st
from dotenv import load_dotenv

# --- CrewAI / Tools ---
from crewai import Agent, Crew, Process, Task, LLM
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource

# --- Solana Pay helpers (same interface as your demo) ---
# Expecting: create_payment(amount_usdc) -> { qr_png_bytes, pay_url, reference }
#            verify_payment_by_memo(reference) -> {"ok": bool, ...}
from solana_pay import create_payment, verify_payment_by_memo

# -------------------- ENV --------------------
load_dotenv(".env")

AIML_API_KEY       = os.getenv("AIML_API_KEY")
SERPER_API_KEY     = os.getenv("SERPER_API_KEY")

MERCHANT_WALLET    = os.getenv("MERCHANT_WALLET")                     # your treasury wallet (required for real QR)
PLATFORM_FEE_USDC  = float(os.getenv("PLATFORM_FEE_USDC", "0.5"))     # flat fee added on top
DEMO_VERIFY_ALWAYS_OK = os.getenv("DEMO_VERIFY_ALWAYS_OK", "1") == "1"

# Optional vendor wallets by source (use if you wire real split payouts later)
VENDOR_WALLET_CARREFOUR = os.getenv("VENDOR_WALLET_CARREFOUR", "")
VENDOR_WALLET_METRO     = os.getenv("VENDOR_WALLET_METRO", "")
VENDOR_WALLET_IMTIAZ    = os.getenv("VENDOR_WALLET_IMTIAZ", "")

# -------------------- AIML LLM --------------------
aiml_llm = LLM(
    model="gpt-4o",
    base_url="https://api.aimlapi.com/v1",
    api_key=AIML_API_KEY,
    temperature=0,
    max_tokens=1000
)

# AIML API Details (STT)
API_KEY  = AIML_API_KEY
BASE_URL = "https://api.aimlapi.com/v1/stt"

# -------------------- Utils --------------------
def parse_price_to_float(value) -> float:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value)
    m = re.search(r"(\d{1,3}(?:,\d{3})*|\d+)(?:\.(\d+))?", s)
    if not m:
        return None
    number = m.group(0).replace(",", "")
    try:
        return float(number)
    except:
        return None

# -------------------- Transcription --------------------
def transcribe_audio_with_aiml(audio_data):
    # 5 MB limit
    if audio_data.size > 5 * 1024 * 1024:
        st.warning("⚠️ Please upload a smaller audio file (less than 5MB) for better performance.")
        return None

    url = BASE_URL
    headers = {"Authorization": f"Bearer {API_KEY}"}
    files = {"audio": ("audio.wav", audio_data, "audio/wav")}
    data = {"model": "#g1_whisper-large"}

    try:
        response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
        response.raise_for_status()
        response_data = response.json()
        transcript = response_data["results"]["channels"][0]["alternatives"][0]["transcript"]
        return transcript

    except requests.exceptions.Timeout:
        st.warning("⏳ AIML API took too long to respond. Please try again.")
        return None

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 524:
            st.warning("⚠️ AIML API timed out (524). Please try again later.")
        else:
            st.warning(f"⚠️ AIML API error: {http_err}")
        return None

    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ Network issue: {e}")
        return None

    except KeyError:
        st.warning("⚠️ Unexpected transcription response. Please try again later.")
        return None

# -------------------- Agents --------------------
input_collector = Agent(
    role="Grocery Input Collector",
    goal=(
        "Collect and clarify user requirements specifically for grocery shopping in Pakistan. "
        "If the user provides irrelevant prompts, politely redirect them back to groceries. "
        "Focus on helping users find the cheapest grocery options."
    ),
    backstory=(
        "Smart and friendly grocery assistant specialized in collecting grocery-related requirements. "
        "Gently guide users back to groceries if they go off-topic."
    ),
    llm=aiml_llm,
    verbose=True
)

# Tools / scrapers
search_tool     = SerperDevTool(api_key=SERPER_API_KEY)
scrape_google   = ScrapeWebsiteTool(website_url='https://google.com/')
scrape_carrefour= ScrapeWebsiteTool(website_url='https://www.carrefour.pk/')
scrape_metro    = ScrapeWebsiteTool(website_url='https://www.metro-online.pk/')

web_searcher = Agent(
    role="Web Search Specialist",
    goal=(
        "Find product listings across Google, Carrefour, and Metro Cash & Carry. "
        "Return JSON list of dicts with: 'name', 'price', 'rating', 'url', 'image_url', 'source', 'delivery_time'."
    ),
    backstory="Skilled product search expert extracting listings and formatting them properly.",
    tools=[search_tool, scrape_google, scrape_carrefour, scrape_metro],
    llm=aiml_llm,
    allow_delegation=False,
    verbose=True
)

analyst = Agent(
    role="Grocery Product Comparison Expert",
    goal=(
        "Evaluate fetched grocery listings and select the top 3 recommendations. "
        "Rank by: (1) lowest price, (2) fastest delivery, (3) positive reviews/ratings. "
        "Return JSON list (3 items): 'name','price','rating','delivery_time','image_url','url','source'."
    ),
    backstory="Compares products for best value: affordable, fast delivery, trusted by buyers.",
    llm=aiml_llm,
    verbose=True
)

review_tool = WebsiteSearchTool(
    config={
        "llm": {
            "provider": "openai",
            "config": {
                "model": "gpt-4o",
                "api_key": AIML_API_KEY,
                "base_url": "https://api.aimlapi.com/v1",
                "temperature": 0.5,
                "max_tokens": 1000
            }
        },
        "embedder": {
            "provider": "openai",
            "config": {
                "model": "text-embedding-3-large",
                "api_key": AIML_API_KEY
            }
        }
    }
)

review_agent = Agent(
    role="Grocery Review Analyzer",
    goal=(
        "Analyze user reviews for the top grocery product (Daraz/Amazon/AliExpress if needed). "
        "Summarize pros, cons, and overall sentiment (quality, delivery, value for money)."
    ),
    backstory="Summarizes customer feedback into useful insights for buyers.",
    tools=[review_tool],
    llm=aiml_llm,
    verbose=True
)

recommender = Agent(
    role="Grocery Shopping Recommendation Specialist",
    goal=(
        "Present top 3 grocery recommendations focusing on cheapest price and fastest delivery. "
        "Each item includes: name, price, rating, delivery_time, image_url, and purchase link. "
        "Format clearly for user-friendly display."
    ),
    backstory="Presents comparison results to help users quickly pick the best option.",
    llm=aiml_llm,
    verbose=True
)

# -------------------- Tasks --------------------
if "filters" not in st.session_state:
    st.session_state["filters"] = {"min_rating": 3.5, "brand": ""}

brand = st.session_state["filters"]["brand"].strip() or None
min_rating = st.session_state["filters"]["min_rating"]

description = (
    f"Process the user input for grocery shopping: '{{user_input}}'\n"
    f"Apply filters if applicable:\n"
    f"- Minimum Rating: {min_rating}\n"
)
if brand:
    description += f"- Preferred Brand: {brand}\n"
description += "Generate a refined grocery search query (cheapest + fast delivery)."

input_task = Task(
    description=description,
    expected_output=(
        "A refined grocery product search query based on the user's input and filters. "
        "Stay focused on grocery items and highlight cheapest options."
    ),
    agent=input_collector
)

search_task = Task(
    description="""
        Search online for the best matching grocery products using the refined search query.
        Look for listings across Carrefour Pakistan, Metro Cash & Carry, and Imtiaz.
        Return a JSON list of the **top 3 grocery products** with fields:
        - name, price, rating, url, image_url, source, delivery_time
    """,
    expected_output="""
        A JSON-formatted list of 3 grocery products (Carrefour/Metro/Imtiaz).
        Each item: name, price, rating, url, image_url, source, delivery_time.
    """,
    agent=web_searcher,
    context=[input_task]
)

analysis_task = Task(
    description=(
        "Analyze structured grocery listings (JSON). Compare price, rating, and delivery time. "
        "Rank the top 3 (cheapest + fast delivery preferred). "
        "For each: name, price, rating, source, delivery_time, reason for ranking."
    ),
    expected_output="""
        A ranked list (1..3) of top grocery recommendations.
        Each entry: name, price, rating, source, delivery_time, reason.
    """,
    agent=analyst,
    context=[search_task]
)

review_task = Task(
    description=(
        "For the #1 grocery product/vendor, summarize customer reviews (pros, cons, sentiment). "
        "If direct reviews not available, infer from pricing/popularity/delivery."
    ),
    expected_output="Pros, cons, and user sentiment for the selected grocery item.",
    agent=review_agent,
    context=[analysis_task]
)

recommendation_task = Task(
    description=(
        "Provide final recommendation summary for the top 3 products with image URLs. "
        "Summarize features, pros/cons, delivery, sentiment. "
        "Highlight the best deal and why."
    ),
    expected_output="""
        Summary of top 3 recommended groceries.
        For each: name, price, rating, image_url, delivery_time, pros/cons, sentiment, final verdict.
    """,
    agent=recommender,
    context=[analysis_task, review_task]
)

# --- Knowledge Source (optional) ---
product_knowledge = StringKnowledgeSource(
    content=(
        "Information about current grocery products and trends in Pakistan, including packaged "
        "foods, dairy, grains, oils, snacks, and household essentials. Focus only on groceries."
    )
)

# --- Crew Setup ---
shopping_crew = Crew(
    agents=[input_collector, web_searcher, analyst, review_agent, recommender],
    tasks=[input_task, search_task, analysis_task, review_task, recommendation_task],
    verbose=True,
    process=Process.sequential,
    embedder={"provider": "aimlapi", "config": {"model": "text-embedding-3-large", "api_key": AIML_API_KEY}}
)

# -------------------- Streamlit UI --------------------
st.set_page_config(page_title="CheapestBuy.AI", page_icon="🥦")

# Title + Logo
col1, col2 = st.columns([5, 2])
with col1:
    st.markdown(
        "<h1 style='margin-bottom: 0;'>🥦 CheapestBuy.AI</h1>"
        "<p style='margin-top: 0; font-size: 30px;'>Buy Groceries Smarter - Save More</p>",
        unsafe_allow_html=True
    )
with col2:
    st.image("tlogo.png", use_container_width=True)

# Sidebar
with st.sidebar:
    st.header("🛠️ Controls")

    # Handle reset from URL
    query_params = st.query_params
    if "reset" in query_params and query_params["reset"] == "1":
        st.session_state.clear()
        st.query_params.clear()
        st.rerun()

    if st.button("🧹 Start New Search"):
        st.query_params["reset"] = "1"
        st.rerun()

    if st.button("🔄 Reset Session"):
        st.session_state.clear()
        st.rerun()

    st.subheader("🔍 Grocery Filters (Optional)")
    filters = {
        "min_rating": st.slider("Minimum Rating", min_value=1.0, max_value=5.0, value=3.5),
        "brand": st.text_input("Preferred Grocery Brand", value="")
    }
    st.session_state["filters"] = filters
    st.write("Filters will be applied to grocery product search.")

# --- Session State ---
if "messages" not in st.session_state:
    st.session_state.messages = []
if "input_mode" not in st.session_state:
    st.session_state.input_mode = "Text"
if "user_input" not in st.session_state:
    st.session_state.user_input = ""
if "checkout" not in st.session_state:
    st.session_state.checkout = {}  # key: idx -> {ref,total,vendor_share,source}

# Chat history display
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input mode
input_mode = st.radio("Choose input type:", ("Text", "Voice"))
st.session_state.input_mode = input_mode

if st.session_state.input_mode == "Text":
    user_input = st.chat_input("Type your grocery query here (e.g., cheapest milk, rice, sugar)...")
    if user_input:
        st.session_state.user_input = user_input
else:
    audio_data = st.audio_input("Speak your grocery query")
    if audio_data:
        st.info("Processing audio...")
        transcribed_text = transcribe_audio_with_aiml(audio_data)
        if transcribed_text:
            st.session_state.user_input = transcribed_text

# --- Run Crew and Render Results + Solana Pay ---
if st.session_state.user_input:
    user_msg = st.session_state.user_input
    st.session_state.messages.append({"role": "user", "content": user_msg})

    with st.chat_message("user"):
        st.markdown(user_msg)

    with st.chat_message("assistant"):
        with st.spinner("Finding the best grocery deals..."):
            result = shopping_crew.kickoff(inputs={"user_input": user_msg})
            reply = result.raw

            try:
                products = json.loads(reply)
                if not isinstance(products, list):
                    raise ValueError("Not a list")

                for idx, product in enumerate(products, 1):
                    st.markdown(f"### 🛒 Option {idx}: {product.get('name', 'No Name')}")

                    # Image
                    if product.get("image_url"):
                        st.image(product.get("image_url"), use_container_width=True)

                    # Base fields
                    price_raw = product.get("price", "N/A")
                    price_val = parse_price_to_float(price_raw)
                    source    = (product.get("source") or "").strip() or "Unknown"

                    st.markdown(
                        f"💵 **Price (vendor):** {price_raw}  \n"
                        f"⭐ **Rating:** {product.get('rating', 'N/A')}  \n"
                        f"🚚 **Delivery:** {product.get('delivery_time', 'N/A')}  \n"
                        f"🔗 [Product Page]({product.get('url', '#')})  \n\n"
                        f"**Pros:** {', '.join(product.get('pros', [])) if product.get('pros') else 'N/A'}  \n"
                        f"**Cons:** {', '.join(product.get('cons', [])) if product.get('cons') else 'N/A'}  \n"
                        f"**Sentiment:** {product.get('sentiment', 'N/A')}"
                    )

                    # If price not parseable, skip checkout
                    if price_val is None:
                        st.info("Price could not be parsed — cannot checkout this item.")
                        st.markdown("---")
                        continue

                    # Fee math
                    total_due    = round(price_val + PLATFORM_FEE_USDC, 4)
                    vendor_share = round(price_val, 4)

                    st.markdown(
                        f"**Checkout total (USDC):** `{total_due}` "
                        f"(includes platform fee `${PLATFORM_FEE_USDC:.2f}`)"
                    )

                    # (Optional) Map vendors to wallets if you later enable auto-split payouts
                    vendor_pubkey = None
                    src_lower = source.lower()
                    if src_lower.startswith("carrefour") and VENDOR_WALLET_CARREFOUR:
                        vendor_pubkey = VENDOR_WALLET_CARREFOUR
                    elif src_lower.startswith("metro") and VENDOR_WALLET_METRO:
                        vendor_pubkey = VENDOR_WALLET_METRO
                    elif src_lower.startswith("imtiaz") and VENDOR_WALLET_IMTIAZ:
                        vendor_pubkey = VENDOR_WALLET_IMTIAZ

                    col_buy, col_verify = st.columns(2)

                    # Generate QR
                    with col_buy:
                        if st.button("🟣 Buy with Solana Pay", key=f"buy_{idx}"):
                            if not MERCHANT_WALLET:
                                st.error("Set MERCHANT_WALLET in .env to generate a payment QR.")
                            else:
                                try:
                                    # Demo behavior: single-recipient QR to merchant wallet (like your demo app)
                                    pay = create_payment(total_due)
                                except Exception as e:
                                    st.error(f"Failed to create payment: {e}")
                                else:
                                    st.session_state.checkout[idx] = {
                                        "ref": pay["reference"],
                                        "total": total_due,
                                        "vendor_share": vendor_share,
                                        "source": source,
                                    }
                                    st.image(pay["qr_png_bytes"], caption=f"Scan to pay {total_due} USDC (Devnet)")
                                    st.code(pay["pay_url"], language="text")
                                    st.markdown(f"[Open in Phantom]({pay['pay_url']})")

                    # Verify payment
                    with col_verify:
                        if st.button("✅ Verify Payment", key=f"verify_{idx}"):
                            entry = st.session_state.checkout.get(idx)
                            if not entry:
                                st.warning("Generate the QR first for this item.")
                            else:
                                if DEMO_VERIFY_ALWAYS_OK:
                                    ok = True
                                else:
                                    try:
                                        res = verify_payment_by_memo(entry["ref"])
                                        ok = bool(res.get("ok"))
                                    except Exception as e:
                                        ok = False
                                        st.warning(f"Verification error: {e}")

                                if ok:
                                    st.success(
                                        f"✅ Payment confirmed!\n\n"
                                        f"- **Total received:** {entry['total']} USDC  \n"
                                        f"- **Platform fee:** {PLATFORM_FEE_USDC:.2f} USDC  \n"
                                        f"- **Vendor amount (escrow math):** {entry['vendor_share']} USDC  \n"
                                        f"- **Vendor source:** {entry['source']}"
                                    )
                                    st.info(
                                        "Demo-style escrow: funds are received by your merchant wallet. "
                                        "In production, auto-payout vendor share post-confirmation, or switch to a split tx."
                                    )
                                else:
                                    st.info("Not confirmed yet. Try again.")

                    st.markdown("---")

                reply_summary = f"Found {len(products)} grocery options. Best choices shown above."

            except Exception:
                # Fallback to raw assistant text if not JSON
                st.markdown(reply)
                reply_summary = reply

        st.session_state.messages.append({"role": "assistant", "content": reply_summary})

    st.session_state.user_input = ""

# --- Footer ---
st.markdown("""
    <style>
    .custom-footer {
        position: fixed; bottom: 0; left: 0; width: 100%;
        text-align: center; padding: 10px 0; font-size: 14px;
        color: gray; background-color: white; z-index: 100;
    }
    .custom-footer hr {
        border: none; border-top: 1px solid #ddd; margin: 0;
    }
    </style>
    <div class="custom-footer">
        <hr>
        Powered by Streamlit | Developed by The Team Alpha <br>
        <b>🤖 Agent Registered with Coral Protocol</b>
    </div>
""", unsafe_allow_html=True)
