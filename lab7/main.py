import hashlib
import hmac
import logging
import secrets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)-10s | %(message)s",
    datefmt="%H:%M:%S"
)

def hash_data(data: bytes) -> bytes:
    """Calculates SHA-256 hash."""
    return hashlib.sha256(data).digest()

class LamportClient:
    def __init__(self, user_id: str, seed_length: int = 32, chain_length: int = 100):
        self.user_id = user_id
        self.chain_length = chain_length
        self.current_index = chain_length
        self.logger = logging.getLogger("Client")
        
        # Generate a cryptographically secure random seed
        self._seed = secrets.token_bytes(seed_length)
        self._hash_chain = self._generate_chain()
        self.logger.info(f"Initialized client '{self.user_id}' with chain length {self.chain_length}.")

    def _generate_chain(self) -> list[bytes]:
        """Generates the full hash chain from P_0 to P_N."""
        chain = [self._seed]
        current = self._seed
        for _ in range(self.chain_length):
            current = hash_data(current)
            chain.append(current)
        return chain

    def get_registration_data(self) -> tuple[str, bytes, int]:
        """Returns data needed for server registration (User ID, P_N, N)."""
        self.logger.info("Exporting registration data (P_N) for secure channel transfer.")
        return self.user_id, self._hash_chain[self.chain_length], self.chain_length

    def generate_login_payload(self) -> bytes | None:
        """Generates the next one-time password (OTP) for login."""
        if self.current_index <= 0:
            self.logger.error("Hash chain exhausted! Re-registration required.")
            return None
        
        self.current_index -= 1
        otp = self._hash_chain[self.current_index]
        self.logger.info(f"Generated OTP for index {self.current_index}.")
        return otp


class LamportServer:
    def __init__(self, lookahead_window: int = 5):
        # In a real app, this would be a database (e.g., PostgreSQL or Redis)
        self.db: dict[str, dict] = {}
        # Allows skipping a few hashes in case of network drops
        self.lookahead_window = lookahead_window
        self.logger = logging.getLogger("Server")

    def register_user(self, user_id: str, root_hash: bytes, chain_length: int) -> None:
        """Registers a user over a presumed secure channel."""
        self.db[user_id] = {
            "current_hash": root_hash,
            "current_index": chain_length
        }
        self.logger.info(f"Successfully registered user '{user_id}'.")

    def authenticate(self, user_id: str, provided_otp: bytes) -> bool:
        """Authenticates a user handling potential network desync."""
        if user_id not in self.db:
            self.logger.warning(f"Authentication failed: User '{user_id}' not found.")
            return False

        user_record = self.db[user_id]
        stored_hash = user_record["current_hash"]
        stored_index = user_record["current_index"]

        if stored_index <= 0:
            self.logger.warning(f"Authentication failed: User '{user_id}' hash chain exhausted.")
            return False

        # Lookahead verification: handle potential skipped indices due to network drops
        current_test_hash = provided_otp
        for offset in range(1, self.lookahead_window + 1):
            current_test_hash = hash_data(current_test_hash)
            
            # Using hmac.compare_digest to prevent timing attacks
            if hmac.compare_digest(current_test_hash, stored_hash):
                # Update state
                new_index = stored_index - offset
                self.db[user_id]["current_hash"] = provided_otp
                self.db[user_id]["current_index"] = new_index
                
                self.logger.info(
                    f"Auth SUCCESS for '{user_id}'. "
                    f"Index advanced from {stored_index} to {new_index} (Offset: {offset})."
                )
                return True

        self.logger.warning(f"Auth FAILED for '{user_id}': Invalid OTP or desync beyond lookahead window.")
        return False


def run_simulation():
    """Runs an end-to-end simulation of the Lamport scheme."""
    print("\nSTARTING LAMPORT AUTHENTICATION SIMULATION\n")
    
    server = LamportServer(lookahead_window=3)
    client = LamportClient(user_id="alice_dev", chain_length=10)

    print("\nPHASE 1: REGISTRATION (SECURE CHANNEL)")
    user_id, p_n, n = client.get_registration_data()
    server.register_user(user_id, p_n, n)

    print("\nPHASE 2: NORMAL LOGIN")
    otp_1 = client.generate_login_payload()
    server.authenticate(user_id, otp_1)

    print("\nPHASE 3: REPLAY ATTACK")
    server.logger.warning("Simulating network sniffer replaying the intercepted OTP...")
    server.authenticate(user_id, otp_1) # Sending the same OTP again

    print("\nPHASE 4: NETWORK DROP & DESYNC (LOOKAHEAD TEST)")
    client.logger.warning("Generating OTP, but simulating network drop (Server never receives it).")
    lost_otp = client.generate_login_payload() 
    
    client.logger.info("Generating the NEXT OTP for a new login attempt.")
    otp_3 = client.generate_login_payload()
    
    server.logger.info("Server receives OTP_3. Expecting OTP_2. Testing lookahead recovery...")
    server.authenticate(user_id, otp_3)

    print("\nSIMULATION COMPLETE\n")

if __name__ == "__main__":
    run_simulation()