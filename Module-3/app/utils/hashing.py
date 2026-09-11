import hashlib
from typing import Tuple

def calculate_hashes(file_path: str) -> Tuple[str, str]:
    """Calculates SHA-256 and MD5 hashes of a file."""
    sha256_hash = hashlib.sha256()
    md5_hash = hashlib.md5()
    
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
            md5_hash.update(byte_block)
            
    return sha256_hash.hexdigest(), md5_hash.hexdigest()

def calculate_bytes_sha256(data: bytes) -> str:
    """Calculates SHA-256 hash of raw bytes."""
    return hashlib.sha256(data).hexdigest()
