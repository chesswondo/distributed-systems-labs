import hashlib
import time
import logging
import sys
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Set up logging to monitor the process
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

app = FastAPI()

# In a real blockchain, the state is distributed and immutable.
# Here, each node maintains its own local ledger.
class State:
    balance: int = 100
    contract_active: bool = False
    hashlock: str = ""
    amount: int = 0
    timeout: float = 0.0
    receiver: str = ""

state = State()
logger = logging.getLogger("Init")


# Data models
class LockRequest(BaseModel):
    hashlock: str
    amount: int
    timeout_seconds: int
    receiver: str

class ClaimRequest(BaseModel):
    secret: str


# Endpoints
@app.get("/")
def get_status():
    """Check node balance and contract status."""
    return {
        "balance": state.balance,
        "contract_active": state.contract_active,
        "hashlock": state.hashlock,
        "expires_in": max(0, state.timeout - time.time()) if state.contract_active else 0
    }

@app.post("/lock")
def lock_funds(req: LockRequest):
    """HTLC Setup Phase: Lock funds with a hash and a timer."""
    if state.contract_active:
        raise HTTPException(status_code=400, detail="Contract already active")
    if state.balance < req.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")

    # Lock the funds
    state.balance -= req.amount
    state.hashlock = req.hashlock
    state.amount = req.amount
    state.timeout = time.time() + req.timeout_seconds
    state.receiver = req.receiver
    state.contract_active = True

    logger.info(f"FUNDS LOCKED! {req.amount} coins reserved for '{req.receiver}'. Hashlock: {req.hashlock}")
    return {"status": "Locked"}

@app.post("/claim")
def claim_funds(req: ClaimRequest):
    """HTLC Claim Phase: Reveal secret to get the funds."""
    if not state.contract_active:
        raise HTTPException(status_code=400, detail="No active contract")
    if time.time() > state.timeout:
        raise HTTPException(status_code=400, detail="Contract expired. Use /refund")

    # Cryptographic verification
    secret_hash = hashlib.sha256(req.secret.encode()).hexdigest()
    if secret_hash != state.hashlock:
        raise HTTPException(status_code=400, detail="Invalid secret. Hash mismatch.")

    # Reveal secret to the network and complete transfer
    logger.info(f"Contract claimed! Secret revealed: '{req.secret}'")
    logger.info(f"{state.amount} coins successfully transferred to {state.receiver}.")
    
    # Reset contract (funds are already deducted from balance during lock)
    state.contract_active = False
    state.hashlock = ""
    return {"status": "Claimed", "secret_revealed": req.secret}

@app.post("/refund")
def refund():
    """Refund funds if the timeout has passed and funds weren't claimed."""
    if not state.contract_active:
        raise HTTPException(status_code=400, detail="No active contract")
    if time.time() < state.timeout:
        raise HTTPException(status_code=400, detail="Contract has not expired yet")

    # Restore balance
    state.balance += state.amount
    logger.info(f"TIMEOUT! Refund successful. {state.amount} coins returned to balance.")
    state.contract_active = False
    return {"status": "Refunded"}

if __name__ == "__main__":
    # Get port from command line arguments
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    name = sys.argv[2] if len(sys.argv) > 2 else f"Node-{port}"
    
    logger.name = name
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="error")