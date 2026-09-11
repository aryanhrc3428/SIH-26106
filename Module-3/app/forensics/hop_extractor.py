import re
from typing import List

def extract_hops(received_headers: List[str]) -> List[str]:
    """
    Extracts IP addresses from Received headers and returns them in chronological order.
    The bottom-most Received header is usually the origin.
    """
    hop_ips = []
    
    ipv4_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
    ipv6_pattern = r'(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,7}:|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F]{1,4}|(?:[0-9a-fA-F]{1,4}:){1,5}(?::[0-9a-fA-F]{1,4}){1,2}|(?:[0-9a-fA-F]{1,4}:){1,4}(?::[0-9a-fA-F]{1,4}){1,3}|(?:[0-9a-fA-F]{1,4}:){1,3}(?::[0-9a-fA-F]{1,4}){1,4}|(?:[0-9a-fA-F]{1,4}:){1,2}(?::[0-9a-fA-F]{1,4}){1,5}|[0-9a-fA-F]{1,4}:(?::[0-9a-fA-F]{1,4}){1,6}|:(?::[0-9a-fA-F]{1,4}){1,7}|::(?:ffff(?::0{1,4})?:)?(?:(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9])\.){3}(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9])|(?:[0-9a-fA-F]{1,4}:){1,4}:(?:(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9])\.){3}(?:25[0-5]|(?:2[0-4]|1?[0-9])?[0-9])'
    
    # Process headers in reverse order (bottom-most first = origin)
    for header in reversed(received_headers):
        if not header:
            continue
            
        # Find IPv4 addresses
        ipv4_matches = re.findall(ipv4_pattern, header)
        # Find IPv6 addresses using finditer to get full match
        ipv6_matches = [m.group(0) for m in re.finditer(ipv6_pattern, header)]
        
        ips = ipv4_matches + ipv6_matches
        
        # Add unique IPs from this hop
        for ip in ips:
            if ip not in hop_ips:
                hop_ips.append(ip)
                
    return hop_ips
