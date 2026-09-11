import re
from typing import Dict, Any, List, Optional


def analyze_sender_alignment(
    header_from: List[tuple], 
    return_path: Optional[str], 
    reply_to: Optional[str]
) -> Dict[str, Any]:
    """
    Analyzes alignment between various sender-related headers.
    header_from is expected to be a list of (name, email) tuples from mailparser.
    """
    if not header_from:
        return {
            "header_from": "Unknown",
            "envelope_from": return_path,
            "reply_to": reply_to,
            "is_display_name_spoofed": False,
            "spoofed_entity_detected": None
        }

    display_name, from_email = header_from[0]
    if not display_name:
        display_name = ""
    if not from_email:
        from_email = "Unknown"
    
    is_display_name_spoofed = False
    spoofed_entity_detected = None
    
    # Check 1: Display name contains an email that doesn't match from_email
    email_in_name = re.search(r'[\w\.-]+@[\w\.-]+', display_name)
    if email_in_name and email_in_name.group(0).lower() != from_email.lower():
        is_display_name_spoofed = True
        spoofed_entity_detected = display_name
    
    # Check 2: Display name contains high-value executive keywords
    high_value_keywords = ["CEO", "CFO", "CTO", "Executive", "Billing", "Admin", "IT Support", "Director", "President", "Manager"]
    if not is_display_name_spoofed and display_name:
        if any(keyword.lower() in display_name.lower() for keyword in high_value_keywords):
            # Extract from_email domain and envelope domain to check mismatch
            from_domain = from_email.split("@")[-1].lower() if "@" in from_email else ""
            envelope_domain = ""
            if return_path:
                envelope_match = re.search(r'[\w\.-]+@([\w\.-]+)', return_path)
                if envelope_match:
                    envelope_domain = envelope_match.group(1).lower()
            
            # If domains mismatch, it's likely spoofing
            if envelope_domain and from_domain and envelope_domain != from_domain:
                is_display_name_spoofed = True
                spoofed_entity_detected = display_name
            elif display_name and from_email:
                # High-value keyword with a from_email that looks suspicious
                is_display_name_spoofed = True
                spoofed_entity_detected = display_name
    
    # Check 3: Envelope/header domain mismatch (Return-Path domain != From domain)
    if not is_display_name_spoofed and return_path and "@" in from_email:
        from_domain = from_email.split("@")[-1].lower()
        envelope_match = re.search(r'[\w\.-]+@([\w\.-]+)', return_path)
        if envelope_match:
            envelope_domain = envelope_match.group(1).lower()
            if envelope_domain != from_domain:
                is_display_name_spoofed = True
                spoofed_entity_detected = f"Envelope mismatch: {return_path} vs {from_email}"

    return {
        "header_from": from_email,
        "envelope_from": return_path,
        "reply_to": reply_to,
        "is_display_name_spoofed": is_display_name_spoofed,
        "spoofed_entity_detected": spoofed_entity_detected if is_display_name_spoofed else None
    }
