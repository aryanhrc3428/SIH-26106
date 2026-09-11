import os
import logging
from datetime import datetime
from typing import Dict, Any

from app.core.celery_app import celery_app
from app.schemas.output_schema import (
    Module3Result, StatusEnum, Hashes, AttachmentHash,
    ErrorDetail, SpfResult, DkimResult, DmarcResult, SenderAlignment
)
from app.utils.hashing import calculate_hashes
from app.parsers.eml_parser import parse_eml
from app.parsers.msg_parser import parse_msg
from app.forensics.hop_extractor import extract_hops
from app.forensics.spf_verifier import verify_spf
from app.forensics.dkim_verifier import verify_dkim
from app.forensics.dmarc_verifier import verify_dmarc
from app.forensics.sender_alignment import analyze_sender_alignment

logger = logging.getLogger(__name__)


def calculate_anomaly_score(
    spf_status: str,
    dkim_status: str,
    dmarc_status: str,
    is_display_name_spoofed: bool,
    has_message_id: bool
) -> float:
    """
    Calculates header_anomaly_score based on CLAUDE.md contract.
    SPF FAIL/PERMERROR: 25
    DKIM FAIL: 25
    DMARC FAIL: 20
    Display name spoofing: 20
    Forged or missing Message-ID: 10
    """
    score = 0.0
    if spf_status in ["FAIL", "PERMERROR"]:
        score += 25.0
    if dkim_status == "FAIL":
        score += 25.0
    if dmarc_status == "FAIL":
        score += 20.0
    if is_display_name_spoofed:
        score += 20.0
    if not has_message_id:
        score += 10.0
        
    return min(score, 100.0)


@celery_app.task(name="tasks.module3_header_analysis", queue="queue_header_forensics")
def module3_header_analysis(case_id: str, file_path: str) -> Dict[str, Any]:
    try:
        if not os.path.exists(file_path):
            return Module3Result(
                case_id=case_id,
                status=StatusEnum.FAILED,
                error=ErrorDetail(
                    code="UNREADABLE_EVIDENCE",
                    message=f"Evidence file not found: {file_path}",
                    recoverable=False
                )
            ).model_dump(mode='json', exclude_none=True)

        # 1. Hashing
        try:
            sha256, md5 = calculate_hashes(file_path)
            hashes = Hashes(sha256=sha256, md5=md5)
        except Exception as e:
            return Module3Result(
                case_id=case_id,
                status=StatusEnum.FAILED,
                error=ErrorDetail(
                    code="UNREADABLE_EVIDENCE",
                    message=f"Could not calculate hashes: {str(e)}",
                    recoverable=False
                )
            ).model_dump(mode='json', exclude_none=True)

        # 2. Parsing
        is_msg = file_path.lower().endswith(".msg")
        try:
            if is_msg:
                parsed_data = parse_msg(file_path)
            else:
                parsed_data = parse_eml(file_path)
        except Exception as e:
            return Module3Result(
                case_id=case_id,
                status=StatusEnum.FAILED,
                hashes=hashes,
                error=ErrorDetail(
                    code="UNREADABLE_EVIDENCE",
                    message=f"Parsing failed: {str(e)}",
                    recoverable=False
                )
            ).model_dump(mode='json', exclude_none=True)

        # Track whether we need DEGRADED status
        is_degraded = False

        # 3. Forensics
        # Hop Extraction
        raw_hop_chain = extract_hops(parsed_data.get("received", []))
        
        # Sender Alignment
        sender_align_data = analyze_sender_alignment(
            parsed_data.get("from", []),
            parsed_data.get("return_path"),
            parsed_data.get("reply_to")
        )
        sender_alignment = SenderAlignment(**sender_align_data)
        
        # Protocol Verification
        header_from_email = sender_align_data.get("header_from") or ""
        header_from_domain = None
        if header_from_email and "@" in str(header_from_email):
            header_from_domain = str(header_from_email).split("@")[-1]
        
        origin_ip = raw_hop_chain[0] if raw_hop_chain else None
        
        # SPF
        spf_res = verify_spf(header_from_domain, origin_ip)
        if spf_res.get("status") == "TEMPERROR":
            is_degraded = True
        spf = SpfResult(**spf_res)
        
        # DKIM - only for .eml files (DKIM applies to raw RFC 822 streams)
        if not is_msg:
            with open(file_path, "rb") as f:
                raw_content = f.read()
            dkim_res = verify_dkim(raw_content)
        else:
            dkim_res = {"status": "NONE", "selector": None, "domain": None}
        dkim = DkimResult(**dkim_res)
        
        # DMARC
        dmarc_res = verify_dmarc(header_from_domain, spf_res, dkim_res)
        if dmarc_res.get("status") == "TEMPERROR":
            is_degraded = True
        dmarc = DmarcResult(**dmarc_res)
        
        # Check timestamp
        timestamp = parsed_data.get("timestamp")
        if timestamp is None:
            is_degraded = True
        
        # 4. Scoring
        score = calculate_anomaly_score(
            spf.status,
            dkim.status,
            dmarc.status,
            sender_alignment.is_display_name_spoofed,
            bool(parsed_data.get("message_id"))
        )
        
        # 5. Build Result
        status = StatusEnum.DEGRADED if is_degraded else StatusEnum.SUCCESS
        
        result = Module3Result(
            case_id=case_id,
            status=status,
            subject=parsed_data.get("subject"),
            timestamp=timestamp,
            hashes=hashes,
            attachment_hashes=[AttachmentHash(**a) for a in parsed_data.get("attachments", [])],
            header_anomaly_score=score,
            spf=spf,
            dkim=dkim,
            dmarc=dmarc,
            sender_alignment=sender_alignment,
            raw_hop_chain=raw_hop_chain,
            raw_headers=parsed_data.get("raw_headers")
        )
        
        return result.model_dump(mode='json', exclude_none=True)

    except Exception as e:
        logger.exception(f"Unexpected error in module3_header_analysis: {str(e)}")
        return Module3Result(
            case_id=case_id,
            status=StatusEnum.FAILED,
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message=f"An unexpected error occurred: {str(e)}",
                recoverable=True
            )
        ).model_dump(mode='json', exclude_none=True)
