from typing import Dict, Any
from app.utils.dns_resolver import dns_resolver as default_dns_resolver


def verify_spf(domain: str, ip: str, resolver=None) -> Dict[str, Any]:
    """
    Performs a basic SPF check for a domain and IP.
    Returns a dict with status: PASS, FAIL, NEUTRAL, SOFTFAIL, NONE, TEMPERROR, or PERMERROR.
    """
    _resolver = resolver or default_dns_resolver
    
    if not domain or not ip:
        return {"status": "NONE", "domain": domain, "ip": ip}

    txt_records, error_type = _resolver.query_txt_with_status(domain)
    
    if error_type == 'TEMPERROR':
        return {"status": "TEMPERROR", "domain": domain, "ip": ip}
    
    spf_record = next((rec for rec in txt_records if rec.startswith("v=spf1")), None)

    if not spf_record:
        return {"status": "NONE", "domain": domain, "ip": ip}

    # Check ip4 and ip6 mechanisms
    if f"ip4:{ip}" in spf_record or f"ip6:{ip}" in spf_record:
        return {"status": "PASS", "domain": domain, "ip": ip}
    
    # Check include mechanisms (simplified - check +all, -all, ~all, ?all)
    if "-all" in spf_record:
        return {"status": "FAIL", "domain": domain, "ip": ip}
    if "~all" in spf_record:
        return {"status": "SOFTFAIL", "domain": domain, "ip": ip}
    if "?all" in spf_record or "all" in spf_record:
        return {"status": "NEUTRAL", "domain": domain, "ip": ip}

    return {"status": "NEUTRAL", "domain": domain, "ip": ip}
