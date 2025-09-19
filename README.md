

**CheapestBuy.AI: Your AI-Powered Grocery Assistant**

CheapestBuy.AI is a smart grocery shopping assistant that helps users find the best and most affordable grocery deals in Pakistan. It uses a CrewAI framework to mimic a team of experts who work together to collect user input, search the web, compare products, analyze reviews, and provide clear recommendations.

**🚀 Features**

**Intelligent Agent Crew:** A team of specialized AI agents works together to fulfill your request.

**Input Collector:** Gathers and clarifies your grocery needs.

**Web Search Specialist:** Searches for products across major Pakistani grocery stores like Carrefour, Metro, and Imtiaz.

**Product Comparison Expert:** Analyzes and ranks the top 3 product options based on price, delivery time, and ratings.

**Review Analyzer:** Summarizes customer reviews to provide pros and cons.

**Recommendation Specialist:** Presents a final, easy-to-read summary of the top deals.

**Voice and Text Input:** You can ask for groceries by typing or speaking your request.

**Customizable Filters:** Apply optional filters for minimum rating or preferred brand to refine your search.

**Structured Recommendations:** The final output provides a clear, organized view of the top options, including price, rating, and a purchase link.

**⚙️ How It Works**
The application is built on Streamlit for the user interface and CrewAI for the AI workflow. The process is sequential:

**User Input:** The user provides a grocery query via text or voice.

**Input Processing:** The Grocery Input Collector agent refines the query and applies any specified filters.

**Web Search:** The Web Search Specialist agent uses web scraping tools (SerperDevTool, ScrapeWebsiteTool) to find product listings.

**Analysis & Ranking:** The Grocery Product Comparison Expert ranks the fetched results to find the best deals.

**Review Summary:** The Grocery Review Analyzer processes product reviews to highlight pros and cons.

**Final Recommendation:** The Grocery Shopping Recommendation Specialist compiles a final, comprehensive summary for the user.

**🛠️ Setup and Installation**
Prerequisites
Python 3.8+

An API key from AIMLAPI for the LLM and embedding models.

An API key from SerperDevTool for web searching.

**Installation Steps**
Clone the repository:

Bash

git clone https://github.com/SheemaMasood381/CheapestBuy_Internet_of_agents_lablab_september2025/
cd your-repo
Create and activate a virtual environment:

Bash

python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
Install the required libraries:

Bash

pip install -r requirements.txt
(Note: You will need to create a requirements.txt file containing all the libraries used in the code, such as crewai, streamlit, requests, python-dotenv, crewai_tools, etc.)

Set up environment variables:

Create a .env file in the project's root directory.

Add your API keys:

AIML_API_KEY="your_aimlapi_key"
SERPER_API_KEY="your_serper_api_key"
Run the application:

Bash

streamlit run app.py
(Assuming your main script file is named app.py)

**🤝 Contribution**
This project was developed by The **Team Alpha** for a hackathon. We welcome contributions from the community. Feel free to open issues or submit pull requests.
**Team Alpha**
1)Sheema Masood
2)Tayyab Nisar
Github= (https://github.com/Tayyab666-star)
Email= (tnasir536@gmail.com)
3)Muhammad Ali
Github= (https://github.com/alimalik07)
Email= (engr.ali.7@gmail.com)
4) Eeman Asghar
Github= (https://github.com/EemanAsghar)
Email= (eemanasghar2@gmail.com)


