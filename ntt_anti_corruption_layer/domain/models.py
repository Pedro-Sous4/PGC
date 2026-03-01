from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum


class DataFormat(Enum):
    JSON = "JSON"
    XML = "XML"
    CSV = "CSV"


class TransferStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass
class DataRecord:
    """Internal domain model for data records"""
    id: str
    content: dict
    timestamp: datetime
    format: DataFormat
    source_system: str
    metadata: Optional[dict] = None


@dataclass
class TransferRequest:
    """Internal domain model for transfer requests"""
    request_id: str
    source_endpoint: str
    target_endpoint: str
    data_records: List[DataRecord]
    priority: int
    created_at: datetime
    scheduled_for: Optional[datetime] = None


@dataclass
class TransferResponse:
    """Internal domain model for transfer responses"""
    request_id: str
    status: TransferStatus
    message: str
    processed_records: int
    failed_records: int
    timestamp: datetime
    error_details: Optional[List[str]] = None


@dataclass
class SystemEndpoint:
    """Internal domain model for system endpoints"""
    endpoint_id: str
    name: str
    url: str
    authentication_type: str
    is_active: bool
    supported_formats: List[DataFormat]