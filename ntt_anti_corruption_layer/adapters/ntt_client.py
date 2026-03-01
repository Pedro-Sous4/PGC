import json
import aiohttp
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from .ntt_models import (
    NTTAuthRequest, NTTAuthResponse, NTTTransferenciaRequest, 
    NTTTransferenciaResponse, NTTTransferStatus, NTTErrorResponse
)


class NTTAPIClient:
    """Client for interacting with NTT Data Exchange API"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url.rstrip('/')
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
        self._auth_credentials: Optional[Dict[str, str]] = None
    
    async def authenticate(self, auth_request: NTTAuthRequest) -> NTTAuthResponse:
        """Authenticate with NTT API"""
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{self.base_url}/auth/token"
            payload = {
                "username": auth_request.username,
                "password": auth_request.password,
                "client_id": auth_request.client_id,
                "client_secret": auth_request.client_secret
            }
            
            async with session.post(url, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self._access_token = data['access_token']
                    self._token_expires_at = datetime.now() + timedelta(seconds=data['expires_in'])
                    self._auth_credentials = {
                        "username": auth_request.username,
                        "password": auth_request.password,
                        "client_id": auth_request.client_id,
                        "client_secret": auth_request.client_secret
                    }
                    
                    return NTTAuthResponse(
                        access_token=data['access_token'],
                        token_type=data['token_type'],
                        expires_in=data['expires_in'],
                        refresh_token=data.get('refresh_token')
                    )
                else:
                    error_data = await response.json()
                    raise Exception(f"Authentication failed: {error_data.get('mensagem_erro', 'Unknown error')}")
    
    async def _ensure_authenticated(self) -> str:
        """Ensure we have a valid access token"""
        if (self._access_token is None or 
            self._token_expires_at is None or 
            datetime.now() >= self._token_expires_at - timedelta(minutes=5)):
            
            if self._auth_credentials is None:
                raise Exception("No authentication credentials available")
            
            await self.authenticate(NTTAuthRequest(**self._auth_credentials))
        
        return self._access_token
    
    async def submit_transfer(self, transfer_request: NTTTransferenciaRequest) -> NTTTransferenciaResponse:
        """Submit a transfer request to NTT API"""
        access_token = await self._ensure_authenticated()
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{self.base_url}/transferencia/enviar"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "id_solicitacao": transfer_request.id_solicitacao,
                "endpoint_origem": transfer_request.endpoint_origem,
                "endpoint_destino": transfer_request.endpoint_destino,
                "dados": [
                    {
                        "id_dado": item.id_dado,
                        "conteudo": item.conteudo,
                        "data_hora": item.data_hora,
                        "formato": item.formato.value,
                        "sistema_origem": item.sistema_origem,
                        "metadados": item.metadados
                    }
                    for item in transfer_request.dados
                ],
                "prioridade": transfer_request.prioridade,
                "data_criacao": transfer_request.data_criacao
            }
            
            if transfer_request.agendamento:
                payload["agendamento"] = transfer_request.agendamento
            
            async with session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return NTTTransferenciaResponse(
                        id_solicitacao=data['id_solicitacao'],
                        status=NTTTransferStatus(data['status']),
                        mensagem=data['mensagem'],
                        registros_processados=data['registros_processados'],
                        registros_falhados=data['registros_falhados'],
                        data_hora_resposta=data['data_hora_resposta'],
                        detalhes_erro=data.get('detalhes_erro')
                    )
                else:
                    error_data = await response.json()
                    raise Exception(f"Transfer submission failed: {error_data.get('mensagem_erro', 'Unknown error')}")
    
    async def get_transfer_status(self, request_id: str) -> NTTTransferenciaResponse:
        """Get status of a transfer request from NTT API"""
        access_token = await self._ensure_authenticated()
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{self.base_url}/transferencia/status/{request_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return NTTTransferenciaResponse(
                        id_solicitacao=data['id_solicitacao'],
                        status=NTTTransferStatus(data['status']),
                        mensagem=data['mensagem'],
                        registros_processados=data['registros_processados'],
                        registros_falhados=data['registros_falhados'],
                        data_hora_resposta=data['data_hora_resposta'],
                        detalhes_erro=data.get('detalhes_erro')
                    )
                else:
                    error_data = await response.json()
                    raise Exception(f"Status check failed: {error_data.get('mensagem_erro', 'Unknown error')}")
    
    async def cancel_transfer(self, request_id: str) -> NTTTransferenciaResponse:
        """Cancel a transfer request in NTT API"""
        access_token = await self._ensure_authenticated()
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            url = f"{self.base_url}/transferencia/cancelar/{request_id}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            async with session.post(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    return NTTTransferenciaResponse(
                        id_solicitacao=data['id_solicitacao'],
                        status=NTTTransferStatus(data['status']),
                        mensagem=data['mensagem'],
                        registros_processados=data['registros_processados'],
                        registros_falhados=data['registros_falhados'],
                        data_hora_resposta=data['data_hora_resposta'],
                        detalhes_erro=data.get('detalhes_erro')
                    )
                else:
                    error_data = await response.json()
                    raise Exception(f"Cancel operation failed: {error_data.get('mensagem_erro', 'Unknown error')}")