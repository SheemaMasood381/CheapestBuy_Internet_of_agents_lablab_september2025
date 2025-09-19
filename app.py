import os
from crewai import Agent, Crew, Process, Task, LLM
from dotenv import load_dotenv
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool
from crewai.knowledge.source.string_knowledge_source import StringKnowledgeSource
import requests
import streamlit as st
import json

# Load environment variables
load_dotenv(".env")

AIML_API_KEY = os.getenv("AIML_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Create an AIML LLM instance
aiml_llm =LLM(
    model="gpt-4o",
    base_url="https://api.aimlapi.com/v1",
    api_key=AIML_API_KEY,
    temperature=0,
    max_tokens=1000)

# AIML API Details
API_KEY = AIML_API_KEY  # Add your AIML API Key here
BASE_URL = "https://api.aimlapi.com/v1/stt"


import streamlit as st
import requests

# Function to send audio to AIML API for transcription with error handling
def transcribe_audio_with_aiml(audio_data):
    # Check if the audio file size is under 5MB
    if audio_data.size > 5 * 1024 * 1024:  # 5 MB limit
        st.warning("⚠️ Please upload a smaller audio file (less than 5MB) for better performance.")
        return None


    url = BASE_URL
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    # Prepare the audio file for sending
    files = {"audio": ("audio.wav", audio_data, "audio/wav")}
    data = {"model": "#g1_whisper-large"}  # Model for transcription

    try:
        # Send audio data to AIML API with timeout set to 60 seconds
        response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
        response.raise_for_status()  # Raise an error if the status code is 400 or higher
        
        # Parse the transcription result from the response
        response_data = response.json()
        transcript = response_data["results"]["channels"][0]["alternatives"][0]["transcript"]
        
        return transcript

    except requests.exceptions.Timeout:
        st.warning("⏳ We are using AIML API for transcription as per hackathon guidelines. However, the service is taking too long to respond. Please try again later.")
        return None

    except requests.exceptions.HTTPError as http_err:
        if response.status_code == 524:
            st.warning("⚠️ We are using AIML API for transcription as per hackathon guidelines. Unfortunately, the service is currently unavailable (timeout). Please try again later.")
        else:
            st.warning(f"⚠️ We are using AIML API for transcription as per hackathon guidelines. An unexpected error occurred: {http_err}. Please try again later.")
        return None

    except requests.exceptions.RequestException as e:
        st.warning(f"⚠️ We are using AIML API for transcription as per hackathon guidelines. A network issue occurred: {e}. Please check your connection and try again.")
        return None

    except KeyError as e:
        st.warning("⚠️ We are using AIML API for transcription as per hackathon guidelines. The service returned an unexpected response. Please try again later.")
        return None



# Define Agents
input_collector = Agent(
    role="Grocery Input Collector",
    goal=(
        "Collect and clarify user requirements specifically for grocery shopping in Pakistan. "
        "If the user provides irrelevant prompts or asks about non-grocery topics, politely redirect "
        "them back to groceries. Always ensure the focus is on helping users find the cheapest options "
        "for their grocery needs."
    ),
    backstory=(
        "You are a smart and friendly grocery assistant who understands what users need while shopping. "
        "You specialize in collecting grocery-related requirements (e.g., rice, flour, milk, vegetables). "
        "If someone goes off-topic (like asking about perfumes, electronics, or random questions), you gently "
        "guide them back to groceries and help refine their request to make sure they get the best and cheapest deals."
    ),
    llm=aiml_llm,
    verbose=True
)

# Define  web search Tools
# Tools for specific websites
search_tool = SerperDevTool(api_key=SERPER_API_KEY)

scrape_google = ScrapeWebsiteTool(website_url='https://google.com/')
scrape_carrefour = ScrapeWebsiteTool(website_url='https://www.carrefour.pk/')
scrape_metro = ScrapeWebsiteTool(website_url='https://www.metro-online.pk/')


web_searcher = Agent(
    role="Web Search Specialist",
    goal="Find product listings across Google, Carrefour, and Metro Cash & Carry. "
         "Return the result as a JSON list of dictionaries, where each dictionary contains: "
         "'name', 'price', 'rating', 'url', and 'image_url'.",
    backstory="You are a skilled product search expert who knows how to extract valuable listings "
              "from multiple grocery platforms and format them properly.",
    tools=[search_tool, scrape_google, scrape_carrefour, scrape_metro],
    llm=aiml_llm,
    allow_delegation=False,
    verbose=True
)

# Define the analysis agent
analyst = Agent(
    role="Grocery Product Comparison Expert",
    goal=(
        "Evaluate the fetched grocery product listings and select the top 3 recommendations. "
        "Ranking priority: (1) lowest price, (2) fastest delivery time (if available), and (3) "
        "positive reviews/ratings. Return results as a JSON list of 3 dictionaries, each containing: "
        "'name', 'price', 'rating', 'delivery_time', 'image_url', and 'url'."
    ),
    backstory=(
        "You are a grocery product comparison expert. You always recommend products that are "
        "affordable, delivered quickly, and trusted by other buyers. Your goal is to ensure "
        "users get maximum value in terms of both cost and quality."
    ),
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
        "Analyze user reviews for the top recommended grocery product from platforms like Daraz, "
        "Amazon, or AliExpress. Summarize user sentiment by extracting clear pros, cons, and the "
        "overall impression of the product’s quality, delivery experience, and value for money."
    ),
    backstory=(
        "You are a review analysis specialist focused only on grocery products. "
        "Your job is to summarize customer feedback into useful insights that help buyers "
        "decide whether the product is worth purchasing."
    ),
    tools=[review_tool],
    llm=aiml_llm,
    verbose=True
)


# Define the final recommendation agent
recommender = Agent(
    role="Grocery Shopping Recommendation Specialist",
    goal=(
        "Present the top 3 grocery product recommendations with a focus on the cheapest price "
        "and fastest delivery. Always highlight affordability, delivery speed, and rating. "
        "Each recommendation must include: product name, price, rating, delivery_time, image URL, "
        "and purchase link. Format the summary clearly and concisely for user-friendly display."
    ),
    backstory=(
        "You are a smart grocery shopping assistant. You take the comparison results and present "
        "them in a way that makes it easy for users to quickly pick the cheapest option with "
        "fast delivery and good reviews."
    ),
    llm=aiml_llm,
    verbose=True
)

# Manually format the filters
brand = st.session_state["filters"]["brand"].strip() or None
min_rating = st.session_state["filters"]["min_rating"]

description = f"Process the user input for grocery shopping: '{{user_input}}'\n" \
              f"Apply the following filters if applicable:\n" \
              f"- Minimum Rating: {min_rating}\n"

if brand:
    description += f"- Preferred Brand: {brand}\n"

description += "Generate a refined grocery product search query (cheapest + fast delivery focused) based on these inputs."


# Now, use the formatted description in your Task
input_task = Task(
    description=description,
    expected_output=(
        "A refined grocery product search query based on the user's input "
        "and any applicable filters (e.g., minimum rating, preferred brand). "
        "The query must stay focused on grocery items and highlight cheapest options."
    ),
    agent=input_collector
)


search_task = Task(
    description="""
        Search online for the best matching grocery products using the refined search query.
        Look for product listings across Carrefour Pakistan, Metro Cash & Carry, and Imtiaz.
        Use appropriate tools (e.g., web scraping, APIs if available).

        Return a JSON list of the **top 3 grocery products** with the following fields:
        - name (title)
        - price
        - rating
        - url
        - image_url
        - source (e.g., Carrefour, Metro, Imtiaz)
        - delivery_time (if available)
    """,
    expected_output="""
        A JSON-formatted list of 3 grocery products from Carrefour, Metro, or Imtiaz.
        Each product must include: name, price, rating, url, image_url, source, and delivery_time.
    """,
    agent=web_searcher,
    context=[input_task]
)


analysis_task = Task(
    description=(
        "Analyze the structured grocery product listings (JSON format) from Carrefour, Metro, and Imtiaz. "
        "Compare features, price, rating, and delivery time for each. "
        "Rank the top 3 groceries based on value (cheapest + fast delivery preferred). "
        "For each of the top 3, return: name, price, rating, source, delivery_time, brief reason for ranking."
    ),
    expected_output="""
        A ranked list (1 to 3) of the top grocery product recommendations.
        Each entry should include: name, price, rating, source, delivery_time, and reason for ranking.
    """,
    agent=analyst,
    context=[search_task]
)


review_task = Task(
    description=(
        "Using the top grocery product and vendor (Carrefour, Metro, or Imtiaz), "
        "summarize customer reviews for this grocery item. "
        "Include pros, cons, and overall sentiment. "
        "If reviews are not directly available, infer sentiment from pricing, popularity, and delivery service."
    ),
    expected_output="A summarized list of pros, cons, and user sentiment for the selected grocery item.",
    agent=review_agent,
    context=[analysis_task]
)


recommendation_task = Task(
    description=(
        "Provide a final grocery recommendation summary based on the top 3 ranked products and their customer reviews. "
        "Summarize key features, pros/cons, delivery, and customer sentiment for each. "
        "Highlight which grocery item is the best deal and why, but present all three options with image URLs."
    ),
    expected_output="""
        A summary of top 3 recommended groceries.
        For each: name, price, rating, image_url, delivery_time, pros/cons, sentiment, and final verdict.
    """,
    agent=recommender,
    context=[analysis_task, review_task]
)

# --- Knowledge Source (Grocery Only) ---
product_knowledge = StringKnowledgeSource(
    content=(
        "Information about current grocery products and trends in Pakistan, "
        "including packaged foods, beverages, dairy, grains, oils, snacks, and household essentials. "
        "Focus only on groceries, not electronics or other categories."
    )
)

# --- Grocery Shopping Crew Setup ---
shopping_crew = Crew(
    agents=[input_collector, web_searcher, analyst, review_agent, recommender],
    tasks=[input_task, search_task, analysis_task, review_task, recommendation_task],
    verbose=True,
    process=Process.sequential,
    embedder={
        "provider": "aimlapi",
        "config": {
            "model": "text-embedding-3-large",
            "api_key": AIML_API_KEY,
        }
    }
)

# --- Streamlit App UI ---
st.set_page_config(page_title="CheapestBuy.AI", page_icon="🥦")

# Title and Logo in same row using columns
col1, col2 = st.columns([5, 2])
with col1:
    st.markdown("""
                <h1 style='margin-bottom: 0;'>🥦 CheapestBuy.AI</h1>
                <p style='margin-top: 0; font-size: 40px;'>Buy Groceries Smarter - Save More</p>
                """, unsafe_allow_html=True)
with col2:
    st.image("tlogo.png", use_container_width=True)

# --- Sidebar ---
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

    # Filters Section
    st.subheader("🔍 Grocery Filters (Optional)")

    filters = {
        "min_rating": st.slider("Minimum Rating", min_value=1.0, max_value=5.0, value=3.5),
        "brand": st.text_input("Preferred Grocery Brand", value="")
    }

    st.session_state["filters"] = filters
    st.write("Filters will be applied to grocery product search.")

# --- Main Chat Area ---
st.markdown("<h5>💬 Ask about any grocery item — your AI Grocery Crew will find, compare, and recommend the best deals in Pakistan!</h5>", unsafe_allow_html=True)

# --- Session state setup ---
if "messages" not in st.session_state:
    st.session_state.messages = []

if "input_mode" not in st.session_state:
    st.session_state.input_mode = "Text"

if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# --- Display previous messages ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Input Mode Selector
input_mode = st.radio("Choose input type:", ("Text", "Voice"))
st.session_state.input_mode = input_mode

# Handle Text Input
if st.session_state.input_mode == "Text":
    user_input = st.chat_input("Type your grocery query here (e.g., cheapest milk, rice, sugar)...")
    if user_input:
        st.session_state.user_input = user_input

# Handle Voice Input
elif st.session_state.input_mode == "Voice":
    audio_data = st.audio_input("Speak your grocery query")
    if audio_data:
        st.info("Processing audio...")
        transcribed_text = transcribe_audio_with_aiml(audio_data)
        if transcribed_text:
            st.session_state.user_input = transcribed_text

# --- Process after input is received ---
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
                # Parse structured product response
                products = json.loads(reply)
                if isinstance(products, list):
                    for idx, product in enumerate(products, 1):
                        st.markdown(f"### 🛒 Option {idx}: {product.get('name', 'No Name')}")
                        if product.get("image_url"):
                            st.image(product.get("image_url"), use_column_width=True)

                        st.markdown(f"""
                            💵 **Price:** {product.get('price', 'N/A')}  
                            ⭐ **Rating:** {product.get('rating', 'N/A')}  
                            🚚 **Delivery:** {product.get('delivery_time', 'N/A')}  
                            🔗 [Buy Now]({product.get('url', '#')})  

                            **Pros:** {", ".join(product.get("pros", [])) if product.get("pros") else "N/A"}  
                            **Cons:** {", ".join(product.get("cons", [])) if product.get("cons") else "N/A"}  
                            **Sentiment:** {product.get("sentiment", "N/A")}
                            ---
                        """)
                    reply_summary = f"Found {len(products)} grocery options. Best one is highlighted above."
                else:
                    raise ValueError("Not a list")

            except Exception:
                st.markdown(reply)
                reply_summary = reply

        # Save assistant message
        st.session_state.messages.append({"role": "assistant", "content": reply_summary})

    st.session_state.user_input = ""

# --- Footer ---
st.markdown("""
    <style>
    .custom-footer {
        position: fixed;
        bottom: 0;
        left: 0;
        width: 100%;
        text-align: center;
        padding: 10px 0;
        font-size: 14px;
        color: gray;
        background-color: white;
        z-index: 100;
    }
    .custom-footer hr {
        border: none;
        border-top: 1px solid #ddd;
        margin: 0;
    }
    </style>

    <div class="custom-footer">
        <hr>
        Powered by Streamlit | Developed by The Team Alpha
    </div>
    """, unsafe_allow_html=True)
