from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Dict
from enum import Enum
from datetime import datetime

class StatusEnum(str, Enum):
    SUCCESS = "SUCCESS"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"

class Hashes(BaseModel):
    sha256: str
    md5: str

class AttachmentHash(BaseModel):
    name: str
    sha256: str

class SpfResult(BaseModel):
    status: str
    domain: Optional[str] = None
    ip: Optional[str] = None

class DkimResult(BaseModel):
    status: str
    selector: Optional[str] = None
    domain: Optional[str] = None

class DmarcResult(BaseModel):
    status: str
    policy: Optional[str] = None
    alignment: Optional[bool] = None

class SenderAlignment(BaseModel):
    header_from: str
    envelope_from: Optional[str] = None
    reply_to: Optional[str] = None
    is_display_name_spoofed: bool
    spoofed_entity_detected: Optional[str] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    recoverable: bool

class Module3Result(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    case_id: str
    status: StatusEnum
    subject: Optional[str] = None
    timestamp: Optional[datetime] = None
    hashes: Optional[Hashes] = None
    attachment_hashes: List[AttachmentHash] = Field(default_factory=list)
    header_anomaly_score: float = 0.0
    spf: Optional[SpfResult] = None
    dkim: Optional[DkimResult] = None
    dmarc: Optional[DmarcResult] = None
    sender_alignment: Optional[SenderAlignment] = None
    raw_hop_chain: List[str] = Field(default_factory=list)
    raw_headers: Optional[str] = None
    error: Optional[ErrorDetail] = None
