import extract_msg
from typing import Dict, Any, List
from datetime import datetime
from app.utils.hashing import calculate_bytes_sha256


def parse_msg(file_path: str) -> Dict[str, Any]:
    """Parses a .msg file and returns a dictionary of forensic data."""
    msg = extract_msg.openMsg(file_path)
    
    # Extract headers safely
    headers = {}
    if msg.headerDict:
        for line in msg.headerDict:
            headers[line] = msg.headerDict[line]
    
    # Extract raw headers safely    
    raw_headers = ""
    if msg.header is not None:
        try:
            raw_headers = msg.header.as_string()
        except Exception:
            raw_headers = str(msg.header) if msg.header else ""
    
    # Extract attachments safely
    attachments = []
    for attachment in (msg.attachments or []):
        att_data = getattr(attachment, 'data', None)
        att_name = getattr(attachment, 'longFilename', None) or getattr(attachment, 'shortFilename', None) or 'unknown'
        attachments.append({
            "name": att_name,
            "sha256": calculate_bytes_sha256(att_data) if att_data else calculate_bytes_sha256(b"")
        })
    
    # Extract Received headers
    received_raw = headers.get("Received", [])
    if isinstance(received_raw, str):
        received_raw = [received_raw]
    elif not isinstance(received_raw, list):
        received_raw = []
        
    return {
        "subject": msg.subject or "",
        "timestamp": msg.date,
        "from": [(msg.sender or "", msg.sender or "")] if msg.sender else [],
        "to": [(msg.to or "", msg.to or "")] if msg.to else [],
        "message_id": getattr(msg, 'messageId', None) or headers.get('Message-ID'),
        "headers": headers,
        "raw_headers": raw_headers,
        "attachments": attachments,
        "return_path": headers.get("Return-Path", ""),
        "reply_to": headers.get("Reply-To", ""),
        "received": received_raw
    }
