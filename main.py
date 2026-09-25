import os, json, asyncio, websockets
from fastapi import FastAPI, Request
import uvicorn

app = FastAPI()
DERIV_TOKEN = os.getenv("DERIV_API_TOKEN", "")
DERIV_WS = "wss://ws.derivws.com/websockets/v3?app_id=1089"

async def place_deriv_trade(signal):
    symbol = signal.get("symbol","").upper()
    if "XAU" not in symbol and "GOLD" not in symbol:
        return {"skipped": "not XAU"}
    try:
        async with websockets.connect(DERIV_WS) as ws:
            await ws.send(json.dumps({"authorize": DERIV_TOKEN}))
            auth = json.loads(await ws.recv())
            if auth.get("error"):
                return auth
            if auth.get("authorize",{}).get("is_virtual") != 1:
                return {"error": "REAL blocked - use DEMO"}
            ctype = "CALL" if signal.get("action","").upper()=="BUY" else "PUT"
            proposal = {"proposal":1,"amount":10,"basis":"stake","contract_type":ctype,"currency":"USD","duration":5,"duration_unit":"t","symbol":"frxXAUUSD"}
            await ws.send(json.dumps(proposal))
            pres = json.loads(await ws.recv())
            if "proposal" in pres:
                await ws.send(json.dumps({"buy": pres["proposal"]["id"], "price": 10}))
                return json.loads(await ws.recv())
            return pres
    except Exception as e:
        return {"error": str(e)}

@app.post("/webhook")
async def webhook(req: Request):
    try:
        raw = await req.body()
        text = raw.decode('utf-8', errors='ignore').replace('\x00','').strip()
        s = text.find('{')
        e = text.rfind('}')+1
        if s>=0 and e>0:
            text = text[s:e]
        data = json.loads(text)
        print(f"OK webhook: {data}")
        result = await place_deriv_trade(data)
        return result
    except Exception as ex:
        print(f"BAD JSON: {ex}")
        return {"ok": False, "error": str(ex), "fixed": True}
@app.get("/")
def home():
    return {"status": "ok - Render fixed 520"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=10000)