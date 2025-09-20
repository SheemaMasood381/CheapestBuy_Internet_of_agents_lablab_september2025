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
scrape_imtiaz    = ScrapeWebsiteTool(website_url='https://www.imtiaz.com/') 
# (Add more scrapers as needed)

web_searcher = Agent(
    role="Web Search Specialist",
    goal=(
        "Find product listings across Google, Carrefour, Metro Cash & Carry, and Imtiaz Market. "
        "Return JSON list of dicts with: 'name', 'price', 'rating', 'url', 'image_url', 'source', 'delivery_time'."
    ),
    backstory="Skilled product search expert extracting listings and formatting them properly.",
    tools=[search_tool, scrape_google, scrape_carrefour, scrape_metro, scrape_imtiaz],  # added here
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
        "Analyze user reviews for top grocery products from Carrefour, Metro, Imtiaz, "
        "and any other scraped local grocery stores. "
        "Summarize pros, cons, and overall sentiment (quality, delivery, value for money)."
    ),
    backstory="Summarizes customer feedback into useful insights for buyers.",
    tools=[review_tool],  # make sure review_tool is set up to fetch reviews from these scraped sources
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

# background 
import base64

def local_file_to_base64(path):
    with open(path, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

png_base64 = local_file_to_base64("logo.png")  # your PNG file

st.markdown(
    f"""
    <style>
    body {{
        background: url("data:image/png;base64,{png_base64}") no-repeat center center fixed !important;
        background-size: cover !important;
    }}
    .stApp {{
        background-color: rgba(255, 255, 255, 0.6) !important;
        backdrop-filter: blur(7px);
    }}
    .block-container {{
        background: transparent !important;
    }}
    </style>
    """,
    unsafe_allow_html=True
)


# Tabs
tabs = st.tabs([
    "🛒 BestBuy.AI (Groceries)",   # Tab 0: Main grocery search
    "💳 Rent Our Agents Registered with Coral Protocol (MCP)"           # Tab 1: Payment / agent rental
])

tab1, tab2 = tabs

# Track active tab automatically
if "current_tab" not in st.session_state:
    st.session_state.current_tab = 0  # default Tab 0

# --- Tab 1: Groceries Demo ---
# --- Tab 1: Groceries Demo ---
with tabs[0]:
    st.session_state.current_tab = 0
    st.write("Find the **best grocery deals** instantly from multiple options!")

    col1, col2 = st.columns([5, 2])
    with col1:
        st.markdown(
            """
            <div style='line-height: 1.2;'>
                <h1 style='margin-bottom: 5px;'>🛒 BestBuy.AI</h1>
                <p style='margin-top: 0; font-size: 24px; color: gray;'>
                    Buy Groceries Smarter - Save More
                </p>
            </div>
            """,
            unsafe_allow_html=True
        )
    with col2:
        st.image("logo.png", width="content") 
    st.markdown("---")

    # Sidebar
    with st.sidebar:
        st.header("🛠️ Controls")

        # Handle reset from URL
        query_params = st.query_params
        if "reset" in query_params and query_params["reset"] == "1":
            st.session_state.clear()
            st.query_params.clear()
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

                        st.markdown("---")

                    reply_summary = f"Found {len(products)} grocery options. Best choices shown above."

                except Exception:
                    # Fallback to raw assistant text if not JSON
                    st.markdown(reply)
                    reply_summary = reply

            st.session_state.messages.append({"role": "assistant", "content": reply_summary})

        st.session_state.user_input = ""


# --- Tab 2: Rent Our Agent ---
with tabs[1]:
    st.session_state.current_tab = 1
    st.title("💡 Rent BestBuy.AI Agent")
    st.write(
        "Experience the convenience of BestBuy.AI — your personal AI shopping assistant. "
        "Rent now and instantly start saving time and money on online shopping!"
    )
    # --- Custom Button CSS ---
    st.markdown(
        """
        <style>
        div.stButton > button:first-child {
            background: linear-gradient(90deg, #007BFF, #00C6FF);  /* Blue gradient */
            color: white;
            font-size: 80px;
            font-weight: bold;
            padding: 20px 250px;
            border-radius: 15px;
            border: none;
            box-shadow: 0px 4px 10px rgba(0,0,0,0.25);
            transition: 0.3s;
        }
        div.stButton > button:first-child:hover {
            background: linear-gradient(90deg, #6f42c1, #b266ff);  /* Purple gradient on hover */
            box-shadow: 0px 6px 15px rgba(0,0,0,0.35);
            transform: scale(1.05);
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # --- Plan Selection ---
    plan = st.radio(
        "Choose Your Plan",
        options=["Monthly - 1 USDC (Demo)", "Yearly - 10 USDC (Demo)"],
        index=0,
        horizontal=True
    )
    amount_usdc = 1.0 if plan.startswith("Monthly") else 10.0

    # --- Rent Button ---
    if st.button("💳 Rent This Agent"):
        payment = create_payment(amount_usdc=amount_usdc)
        st.session_state["last_payment_reference"] = payment["reference"]
        st.image(payment["qr_png_bytes"], caption="Scan with Phantom Wallet to pay via Solana Pay")
        st.write(f"Payment Link: [{payment['pay_url']}]({payment['pay_url']})")

        if st.session_state.get("demo_mode", True):
            # Auto show demo success
            # Demo success
            st.success("✅ Payment confirmed! (Demo Mode)")
            st.session_state["demo_payment_success"] = True
            st.success(f"✅ Payment Successful for {plan}! Thank you for renting BestBuy.AI (Demo Mode)")
            st.info(
                """
                🎉 **Your BestBuy.AI agent is now ready to use!**

                **Here’s what you can do next:**
                - Access your agent instantly online via your personal dashboard or a secure platform link.
                - Integrate the agent into your website with our embed widget (HTML snippet provided upon request).
                - Need help or want a custom setup? Contact our team:

                **Email:** support@bestbuy.ai  
                **Phone:** +92-300-XXXXXXX  
                **Website:** [www.bestbuy.ai](https://www.bestbuy.ai)

                ⚠️ **No download required** — BestBuy.AI runs securely in the cloud.
                """
            )
            

    # --- Verify Payment Section ---
    ref = st.session_state.get("last_payment_reference")
    if ref:
        st.markdown("### 🔍 Verify Payment (Live Blockchain Check)")
        st.write(
            "Click the button below to confirm the payment on the Solana blockchain. "
            "⚠️ This is **real-time verification** — it will only succeed if the payment was actually made. "
            "Demo payments shown above are for presentation purposes only."
        )

        if st.button("✅ Verify Payment"):
            if st.session_state.get("demo_payment_success", False):
                st.info(
                    "⚠️ Note: The previous success message was in demo mode. "
                    "This verification will check the real blockchain transaction."
                )

            # Call Helius API to verify payment
            result = verify_payment_by_memo(ref, timeout_sec=30)
            if result["ok"]:
                st.success("✅ Payment confirmed on Solana blockchain! Signature: " + result["signature"])
                st.info(
                    "🎉 The agent is now officially active. "
                    "You can access it via your dashboard or integration link."
                )
            else:
                st.warning(
                    "⏳ Payment not yet confirmed on the blockchain. "
                    "Please wait a few moments and try again."
                )



    st.divider()

    # Why Choose BestBuy.AI
    st.subheader("🚀 Why Choose BestBuy.AI?")
    st.write("""
    BestBuy.AI is your **smart online shopping assistant**, saving you time and money by instantly finding the **best deals** from multiple stores and brands.  
    Say goodbye to endless scrolling and comparing — get **personalized, efficient, and reliable shopping recommendations** in seconds.
    """)

    # Our Solution
    st.subheader("✅ How BestBuy.AI Works")
    st.write("""
    - Instantly searches across **top grocery stores** to find the **lowest prices and best deals**.  
    - Summarizes **customer reviews** to highlight pros, cons, and overall satisfaction.  
    - Easy integration for **third-party platforms** to enhance their customer experience.  
    """)

    # Future Growth
    st.subheader("📈 Future Expansion & Innovations")
    st.write("""
    BestBuy.AI will expand beyond groceries to cover multiple categories:

    - 💄 Beauty & Personal Care  
    - 💻 Electronics  
    - 🍲 Food & Beverages  
    - 👗 Fashion & Apparel  
    - 🪑 Home & Furniture  
    - 🧸 Toys & Hobbies  
    - 🔨 DIY & Hardware  
    - 🏋️ Sports & Fitness  
    - ✈️ Travel & Bookings  

    *(...and more innovative agents coming soon!)*  
    """)

    st.info("Rent this agent securely via **Phantom Wallet / Solana Pay** and experience smarter online shopping today!")

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
        <b>🤖 Agent Registered with Coral Protocol</b> | Rent Agent securely via <b>Phantom / Solana Pay</b>
    </div>
""", unsafe_allow_html=True)
