from typing import Dict, Any
from app.utils.dns_resolver import dns_resolver as default_dns_resolver


def verify_dmarc(header_from_domain: str, spf_result: Dict[str, Any], dkim_result: Dict[str, Any], resolver=None) -> Dict[str, Any]:
    """
    Performs a DMARC check based on SPF and DKIM results.
    """
    _resolver = resolver or default_dns_resolver
    
    if not header_from_domain:
        return {"status": "NONE", "policy": None, "alignment": False}

    # Query DMARC record
    dmarc_domain = f"_dmarc.{header_from_domain}"
    txt_records, error_type = _resolver.query_txt_with_status(dmarc_domain)
    
    if error_type == 'TEMPERROR':
        return {"status": "TEMPERROR", "policy": None, "alignment": False}
    
    dmarc_record = next((rec for rec in txt_records if rec.startswith("v=DMARC1")), None)

    if not dmarc_record:
        return {"status": "NONE", "policy": None, "alignment": False}

    # Parse policy
    policy = "none"
    if "p=reject" in dmarc_record:
        policy = "reject"
    elif "p=quarantine" in dmarc_record:
        policy = "quarantine"

    # Check alignment
    spf_aligned = spf_result.get("status") == "PASS" and spf_result.get("domain") == header_from_domain
    dkim_aligned = dkim_result.get("status") == "PASS" and dkim_result.get("domain") == header_from_domain

    alignment = spf_aligned or dkim_aligned
    status = "PASS" if alignment else "FAIL"

    return {
        "status": status,
        "policy": policy,
        "alignment": alignment
    }
