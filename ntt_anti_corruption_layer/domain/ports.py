from abc import ABC, abstractmethod
from typing import List, Optional
from .models import TransferRequest, TransferResponse, DataRecord


class DataTransferPort(ABC):
    """Port interface for data transfer operations"""
    
    @abstractmethod
    async def submit_transfer(self, request: TransferRequest) -> TransferResponse:
        """Submit a transfer request"""
        pass
    
    @abstractmethod
    async def get_transfer_status(self, request_id: str) -> TransferResponse:
        """Get status of a transfer request"""
        pass
    
    @abstractmethod
    async def cancel_transfer(self, request_id: str) -> TransferResponse:
        """Cancel a transfer request"""
        pass


class DataRepositoryPort(ABC):
    """Port interface for data repository operations"""
    
    @abstractmethod
    async def save_data_records(self, records: List[DataRecord]) -> bool:
        """Save data records to repository"""
        pass
    
    @abstractmethod
    async def get_data_records(self, filters: dict) -> List[DataRecord]:
        """Retrieve data records from repository"""
        pass
    
    @abstractmethod
    async def update_data_record(self, record_id: str, updates: dict) -> bool:
        """Update a data record"""
        pass


class NotificationPort(ABC):
    """Port interface for notification operations"""
    
    @abstractmethod
    async def send_notification(self, message: str, recipients: List[str]) -> bool:
        """Send notification to recipients"""
        pass