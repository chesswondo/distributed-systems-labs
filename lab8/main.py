import math
import hashlib
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")

class BloomFilter:
    def __init__(self, expected_items: int, bit_array_size: int):
        self.n = expected_items
        self.m = bit_array_size
        
        # Calculate optimal 'k' based on the formula: min k = (m / n) * ln(2)
        # We use max(1, ...) because we need at least 1 hash function
        optimal_k = (self.m / self.n) * math.log(2)
        self.k = max(1, int(round(optimal_k)))
        
        # Initialize bit array with 0s
        self.bit_array = [0] * self.m
        self.logger = logging.getLogger("BloomFilter")
        
        self.logger.info(
            f"Initialized Filter -> Array size (m): {self.m}, "
            f"Expected items (n): {self.n}, Optimal hashes (k): {self.k}"
        )

    def _get_hashes(self, item: str) -> list[int]:
        """
        Uses Double Hashing technique to simulate 'k' hash functions
        efficiently without calculating 'k' cryptographic hashes.
        """
        encoded_item = item.encode('utf-8')
        
        # Get two base hashes (using standard libraries for demonstration)
        hash1 = int(hashlib.md5(encoded_item).hexdigest(), 16)
        hash2 = int(hashlib.sha1(encoded_item).hexdigest(), 16)
        
        # Generate k hashes: (hash1 + i * hash2) % m
        return [(hash1 + i * hash2) % self.m for i in range(self.k)]

    def add(self, item: str) -> None:
        """Adds an item to the Bloom filter."""
        hashes = self._get_hashes(item)
        for h in hashes:
            self.bit_array[h] = 1
        self.logger.debug(f"Item '{item}' added at positions: {hashes}")

    def check(self, item: str) -> bool:
        """
        Checks if an item is in the set.
        Returns False -> 'definitely not in S'
        Returns True -> 'probably in S'
        """
        hashes = self._get_hashes(item)
        for h in hashes:
            # If any corresponding bit is 0, the item was never added
            if self.bit_array[h] == 0:
                return False
        return True


# Simulation
if __name__ == "__main__":
    # Example: We expect to store 10 items, and we allocate 100 bits of memory.
    bf = BloomFilter(expected_items=10, bit_array_size=100)
    
    # Add some data
    words_to_add = ["apple", "banana", "cherry"]
    for word in words_to_add:
        bf.add(word)
        
    print("\nTesting Queries...")
    
    # Test items we know are in the filter (should be True)
    for word in words_to_add:
        result = bf.check(word)
        print(f"Query '{word}': {result} (Expected: True -> probably in S)")
        
    # Test items we did not add (should be False, but True is a false positive)
    words_not_added = ["grape", "orange", "pineapple"]
    for word in words_not_added:
        result = bf.check(word)
        print(f"Query '{word}': {result} (Expected: False -> definitely not in S)")