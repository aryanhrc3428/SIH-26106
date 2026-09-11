import dkim
from typing import Dict, Any, Optional, Callable


def verify_dkim(raw_eml: bytes, dns_lookup_func: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Verifies DKIM signatures in a raw email message.
    Returns status: PASS, FAIL, or NONE (no signature found).
    """
    try:
        # Quick check: if no DKIM-Signature header exists, return NONE
        # This avoids passing non-RFC822 data (like .msg binary) into dkim
        try:
            header_portion = raw_eml.split(b'\r\n\r\n', 1)[0]
            if b'\n\n' in raw_eml and b'\r\n\r\n' not in raw_eml:
                header_portion = raw_eml.split(b'\n\n', 1)[0]
        except Exception:
            return {"status": "NONE", "selector": None, "domain": None}
        
        if b'dkim-signature' not in header_portion.lower():
            return {"status": "NONE", "selector": None, "domain": None}
        
        d = dkim.DKIM(raw_eml)
        
        # Extract selector and domain from signature before verification
        selector = None
        domain = None
        sig_headers = [h for h in d.headers if h[0].lower() == b'dkim-signature']
        if sig_headers:
            sig_val = sig_headers[0][1].decode('utf-8', errors='replace')
            for part in sig_val.split(';'):
                part = part.strip()
                if part.startswith('d='):
                    domain = part[2:].strip()
                elif part.startswith('s='):
                    selector = part[2:].strip()
        
        # Verify with optional custom DNS lookup
        kwargs = {}
        if dns_lookup_func:
            kwargs['dnsfunc'] = dns_lookup_func
        
        valid = d.verify(**kwargs)
        
        return {
            "status": "PASS" if valid else "FAIL",
            "selector": selector,
            "domain": domain
        }
    except dkim.DKIMException:
        return {"status": "FAIL", "selector": None, "domain": None}
    except Exception:
        return {"status": "NONE", "selector": None, "domain": None}
