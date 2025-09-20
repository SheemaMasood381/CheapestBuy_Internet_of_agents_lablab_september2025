<p align="center">
  <img src="logo.png" alt="Team Alpha Logo" width="240"/>
</p>

# 🥦 CheapestBuy.AI

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/Streamlit-%E2%9C%94%EF%B8%8F-brightgreen.svg)](https://streamlit.io/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)
[![AIML API](https://img.shields.io/badge/AIML%20API-GPT--4o-important.svg)](https://aimlapi.com/)
[![Deployment: Windows](https://img.shields.io/badge/Windows-supported-blue.svg)](https://docs.microsoft.com/en-us/windows/)
[![Solana Pay](https://img.shields.io/badge/Solana%20Pay-Devnet%20Demo-9945FF?logo=solana&logoColor=white)](https://solanapay.com/)

---

## Project Overview

**CheapestBuy.AI** is an intelligent, multi-agent grocery shopping assistant built with Streamlit and CrewAI.  
It searches, compares, and recommends the most affordable groceries in Pakistan, supporting both text and voice-based searches.

---
## Features

- 🪸 **Registered with Coral Protocol** (Agent registry for secure multi-agent operations)
- 🔎 Affordable grocery product search (Carrefour, Metro, Imtiaz)
- 📊 Product comparison: price, delivery options, reviews
- 🤖 Multi-agent pipeline (input, search, analysis, review, recommendation)
- 🔉 Voice search (AIML GPT-4o Whisper integration)
- 💬 User review and sentiment analysis (Daraz, Amazon, AliExpress)
- 🥇 Top 3 detailed recommendations (with images, links, pros, cons, delivery info)
- 🏷️ Simple, beginner-friendly Streamlit UI with filters & history
- 💳 **Solana Pay checkout** (Devnet USDC, QR code payments with escrow math)

---
---
<table>
<tr>
<td width="50%" valign="top">

<h2>Tech Stack</h2>

| Component    | Details                      |
|--------------|------------------------------|
| Python       | 3.10+                        |
| Streamlit    | UI, chat interface           |
| CrewAI       | Multi-agent workflow         |
| AIML API     | GPT-4o + Whisper for LLM/STT |
| Serper.dev   | Web search (Google results)  |
| Custom Tools | Grocery website scrapers     |

</td>
<td width="50%" align="center">

<img src="UI.png" alt="App UI Preview" width="500">

</td>
</tr>
</table>

----
## 🪸 Coral Protocol Integration

Our agent is now registered on [Coral Protocol](https://coralprotocol.com/)!  
Coral enables secure agent registry and agent interactions across decentralized environments.

<table>
<tr>
<td align="center" width="50%">

<b>Agent registry proof</b><br>
<img src="proof_or_agent_registry_in_coral.png" alt="Agent Registry in Coral" width="400"/>

</td>
<td align="center" width="50%">

<b>application.yaml for Coral Registration</b><br>
<img src="application_yaml_to_register_agent_in_coral.png" alt="application.yaml for Coral Registration" width="400"/>

</td>
</tr>
</table>

-----
## 💳 Solana Pay Integration (Demo)

This project includes a **demo integration** of Solana Pay using **Devnet USDC**.  
It is meant for hackathon/demo purposes only — not for production payments.

- Generates **QR codes** for Phantom wallet payments (Devnet USDC).  
- Displays escrow-style fee math (platform fee + vendor share).  
- Two modes:
  - **Demo mode**: always confirms payment (no blockchain check).  
  - **Real mode**: verifies on-chain transaction by reference using Solana Devnet RPC.  
- Works only with **Devnet USDC** (`USDC Mint: 4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU`).  

### Example flow:
1. User selects **Buy with Solana Pay**.  
2. Phantom wallet opens with a **demo Devnet USDC payment request**.  
3. After sending, user clicks **Verify Payment**.  
4. App confirms amount + fee split (escrow-style).  
<img width="634" height="458" alt="image" src="https://github.com/user-attachments/assets/fb60660f-5584-4324-9100-3f0e45aef528" />

## Quick Start

### 1. Clone or Download

```bash
git clone https://github.com/teamalpha/cheapestbuy-ai.git
cd cheapestbuy-ai
```

### 2. Set Up Python Environment

```bash
python -m venv .venv
# Mac/Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Add API Keys to .env

Create a `.env` file in the project root folder:
```bash
AIML_API_KEY=your_aiml_api_key
SERPER_API_KEY=your_serperdev_api_key
# Solana Pay 
MERCHANT_WALLET=your_devnet_phantom_wallet
PRICE_PER_CREDIT_USDC=0.5
SOLANA_CLUSTER=https://api.devnet.solana.com
USDC_MINT=4zMMC9srt5Ri5X14GAgXhaHii3GnPAEERYPJgZJDncDU

# Demo toggle (1 = always confirm, 0 = real Devnet verify)
DEMO_VERIFY_ALWAYS_OK=1

```

### 5. Run the App

```bash
streamlit run app.py
```

---

## Usage

- Select text or voice input
- Enter your grocery query ("cheapest rice", "best milk", etc.)
- Apply filters (brand, minimum rating)
- View results — top 3 deals with images, links, and detailed reviews

---

## Workflow

1. **Input**  
   The grocery-related query is confirmed and refined.

2. **Web Search**  
   Retrieves product results from Google, Carrefour, Metro.

3. **Comparison**  
   Selects the top 3 cheapest and fastest-delivery options.

4. **Reviews**  
   Extracts customer reviews, pros, cons, and sentiment for each product.

5. **Recommendation**  
   Displays a concise summary for each option and highlights the best deal.
   
6. **Checkout (Demo)**  
   Generates a Solana Pay QR → user pays in Phantom (Devnet USDC) → demo/verify flow confirms.

---

## Voice Search Info

- Format: `.wav` (max 5MB)
- AIML API Whisper-Large (GPT-4o)
- Clear warnings are provided in case of network timeout or error

---

## Team & Contributors

This project is the result of the hard work and collaboration of the following contributors:

- [SheemaMasood381](https://github.com/SheemaMasood381)
- [Tayyab666-star](https://github.com/Tayyab666-star)
- [EemanAsghar](https://github.com/EemanAsghar)
- [Muhammad Ali](https://github.com/alimalik07)
  
---

## Contributing

- Fork the repository and submit a pull request
- Report bugs or issues (via GitHub Issues)

---

## License

MIT

---

**Developed by Team Alpha | Powered by Streamlit & CrewAI**
