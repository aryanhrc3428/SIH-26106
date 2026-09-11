import mailparser
import email
from typing import Dict, Any, List
from datetime import datetime
from app.utils.hashing import calculate_bytes_sha256


def parse_eml(file_path: str) -> Dict[str, Any]:
    """Parses an .eml file and returns a dictionary of forensic data."""
    mail = mailparser.parse_from_file(file_path)
    
    # Use stdlib email to preserve raw headers (mailparser dict drops duplicate keys)
    with open(file_path, 'rb') as f:
        raw_bytes = f.read()
    
    msg = email.message_from_bytes(raw_bytes)
    
    # Extract raw header block (everything before the body)
    raw_header_end = raw_bytes.find(b'\r\n\r\n')
    if raw_header_end == -1:
        raw_header_end = raw_bytes.find(b'\n\n')
    if raw_header_end != -1:
        raw_headers = raw_bytes[:raw_header_end].decode('utf-8', errors='replace')
    else:
        raw_headers = raw_bytes.decode('utf-8', errors='replace')
    
    # Extract all Received headers in order (preserving duplicates)
    received_headers = msg.get_all('Received', [])
    
    # Extract attachments
    attachments = []
    for attachment in mail.attachments:
        payload = attachment.get("payload", b"")
        if isinstance(payload, str):
            payload = payload.encode('utf-8', errors='replace')
        binary_payload = attachment.get("binary", False)
        raw_data = attachment.get("payload", b"")
        if isinstance(raw_data, str):
            import base64
            try:
                raw_data = base64.b64decode(raw_data)
            except Exception:
                raw_data = raw_data.encode('utf-8', errors='replace')
        attachments.append({
            "name": attachment.get("filename", "unknown"),
            "sha256": calculate_bytes_sha256(raw_data if isinstance(raw_data, bytes) else b"")
        })
        
    return {
        "subject": mail.subject,
        "timestamp": mail.date,
        "from": mail.from_,
        "to": mail.to,
        "message_id": mail.message_id,
        "headers": mail.headers,
        "raw_headers": raw_headers,
        "attachments": attachments,
        "return_path": msg.get("Return-Path", ""),
        "reply_to": msg.get("Reply-To", ""),
        "received": received_headers
    }
