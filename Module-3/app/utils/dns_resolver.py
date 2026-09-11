import dns.resolver
import dns.exception
from typing import List, Optional, Tuple
import functools
import os


class DNSResolver:
    def __init__(self):
        self.timeout = float(os.getenv("DNS_TIMEOUT_SECONDS", "2.0"))
        self.nameservers = os.getenv("DNS_CUSTOM_NAMESERVERS", "1.1.1.1,8.8.8.8").split(",")
        self.resolver = dns.resolver.Resolver()
        self.resolver.timeout = self.timeout
        self.resolver.lifetime = self.timeout
        if self.nameservers:
            self.resolver.nameservers = self.nameservers

    @functools.lru_cache(maxsize=1024)
    def query_txt(self, domain: str) -> List[str]:
        """Queries TXT records for a domain. Returns empty list on any failure."""
        records, _ = self.query_txt_with_status(domain)
        return records

    @functools.lru_cache(maxsize=1024)
    def query_txt_with_status(self, domain: str) -> Tuple[List[str], Optional[str]]:
        """
        Queries TXT records for a domain.
        Returns (records, error_type) where error_type is None on success,
        'TEMPERROR' on timeout, or 'NONE' on NXDOMAIN/NoAnswer.
        """
        try:
            answers = self.resolver.resolve(domain, 'TXT')
            return ([str(rdata).strip('"') for rdata in answers], None)
        except dns.exception.Timeout:
            return ([], 'TEMPERROR')
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return ([], 'NONE')
        except Exception:
            return ([], 'TEMPERROR')

    @functools.lru_cache(maxsize=1024)
    def query_mx(self, domain: str) -> List[str]:
        """Queries MX records for a domain."""
        try:
            answers = self.resolver.resolve(domain, 'MX')
            return [str(rdata.exchange).rstrip('.') for rdata in answers]
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN, dns.exception.Timeout):
            return []
        except Exception:
            return []


# Singleton instance
dns_resolver = DNSResolver()
