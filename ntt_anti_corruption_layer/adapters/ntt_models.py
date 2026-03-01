from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum


class NTTDataFormat(Enum):
    JSON = "JSON"
    XML = "XML"
    CSV = "CSV"


class NTTTransferStatus(Enum):
    PENDING = "PENDENTE"
    IN_PROGRESS = "PROCESSANDO"
    COMPLETED = "CONCLUIDO"
    FAILED = "FALHOU"
    CANCELLED = "CANCELADO"


@dataclass
class NTTAuthRequest:
    """NTT API authentication request"""
    username: str
    password: str
    client_id: str
    client_secret: str


@dataclass
class NTTAuthResponse:
    """NTT API authentication response"""
    access_token: str
    token_type: str
    expires_in: int
    refresh_token: Optional[str] = None


@dataclass
class NTTDataItem:
    """NTT API data item structure"""
    id_dado: str
    conteudo: Dict[str, Any]
    data_hora: str
    formato: NTTDataFormat
    sistema_origem: str
    metadados: Optional[Dict[str, Any]] = None


@dataclass
class NTTTransferenciaRequest:
    """NTT API transfer request structure"""
    id_solicitacao: str
    endpoint_origem: str
    endpoint_destino: str
    dados: List[NTTDataItem]
    prioridade: int
    data_criacao: str
    agendamento: Optional[str] = None


@dataclass
class NTTTransferenciaResponse:
    """NTT API transfer response structure"""
    id_solicitacao: str
    status: NTTTransferStatus
    mensagem: str
    registros_processados: int
    registros_falhados: int
    data_hora_resposta: str
    detalhes_erro: Optional[List[str]] = None


@dataclass
class NTTConfiguracaoEndpoint:
    """NTT API endpoint configuration"""
    id_endpoint: str
    nome: str
    url: str
    tipo_autenticacao: str
    ativo: bool
    formatos_suportados: List[NTTDataFormat]


@dataclass
class NTTErrorResponse:
    """NTT API error response structure"""
    codigo_erro: str
    mensagem_erro: str
    timestamp: str
    detalhes: Optional[Dict[str, Any]] = None