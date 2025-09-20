# solana_pay.py
import os, time, uuid, io, qrcode, requests
from urllib.parse import urlencode
from dotenv import load_dotenv

load_dotenv()

ENV = os.getenv("ENV", "devnet")
HELIUS_API_KEY = os.getenv("HELIUS_API_KEY")
MERCHANT = os.getenv("MERCHANT_WALLET")

USDC_MAIN = os.getenv("USDC_MINT_MAINNET", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
USDC_DEV  = os.getenv("USDC_MINT_DEVNET", "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v")
USDC = USDC_MAIN if ENV == "mainnet" else USDC_DEV

def create_payment(amount_usdc: float, label="CheapestBuy", message="Agent credits"):
    ref = uuid.uuid4().hex
    params = {
        "amount": f"{amount_usdc}",
        "spl-token": USDC,
        "reference": ref,
        "label": label,
        "message": message,
        "memo": f"cb-{ref}",
    }
    url = f"solana:{MERCHANT}?{urlencode(params)}"
    img = qrcode.make(url)
    buf = io.BytesIO(); img.save(buf, format="PNG"); buf.seek(0)
    return {"reference": ref, "pay_url": url, "qr_png_bytes": buf.read()}

def verify_payment_by_memo(reference: str, timeout_sec=20):
    base = f"https://api.helius.xyz/v0/addresses/{MERCHANT}/transactions?api-key={HELIUS_API_KEY}&limit=10"
    end = time.time() + timeout_sec
    while time.time() < end:
        r = requests.get(base, timeout=10)
        if r.ok:
            for tx in r.json():
                for m in (tx.get("memos") or []):
                    if (m.get("memo") or "") == f"cb-{reference}":
                        return {"ok": True, "signature": tx.get("signature")}
        time.sleep(2)
    return {"ok": False}
