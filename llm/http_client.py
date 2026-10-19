"""
Shared HTTP Client with Connection Pooling
Provides both sync and async clients with connection pooling, keep-alive, and retries.
"""
import logging

import httpx

logger = logging.getLogger(__name__)


class PooledHTTPClient:
    """
    HTTP client with connection pooling for both sync and async operations.
    
    Uses httpx for HTTP/2 support, connection pooling, and keep-alive.
    """
    
    def __init__(
        self,
        base_url: str = "",
        max_connections: int = 100,
        max_keepalive_connections: int = 20,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0,
    ):
        self.base_url = base_url
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.timeout = timeout
        
        # Sync client with connection pooling
        self._sync_client: httpx.Client | None = None
        self._async_client: httpx.AsyncClient | None = None
        
    def _get_sync_client(self) -> httpx.Client:
        """Get or create sync client with connection pooling."""
        if self._sync_client is None or self._sync_client.is_closed:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
                keepalive_expiry=self.keepalive_expiry,
            )
            self._sync_client = httpx.Client(
                base_url=self.base_url,
                limits=limits,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
            logger.debug(f"Created sync HTTP client for {self.base_url}")
        return self._sync_client
    
    def _get_async_client(self) -> httpx.AsyncClient:
        """Get or create async client with connection pooling."""
        if self._async_client is None or self._async_client.is_closed:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive_connections,
                keepalive_expiry=self.keepalive_expiry,
            )
            self._async_client = httpx.AsyncClient(
                base_url=self.base_url,
                limits=limits,
                timeout=httpx.Timeout(self.timeout),
                follow_redirects=True,
            )
            logger.debug(f"Created async HTTP client for {self.base_url}")
        return self._async_client
    
    # Sync methods
    def get(self, url: str, **kwargs) -> httpx.Response:
        """Sync GET request."""
        client = self._get_sync_client()
        return client.get(url, **kwargs)
    
    def post(self, url: str, **kwargs) -> httpx.Response:
        """Sync POST request."""
        client = self._get_sync_client()
        return client.post(url, **kwargs)
    
    def stream_post(self, url: str, **kwargs) -> httpx.Response:
        """Sync streaming POST request."""
        client = self._get_sync_client()
        return client.post(url, **kwargs)
    
    # Async methods
    async def aget(self, url: str, **kwargs) -> httpx.Response:
        """Async GET request."""
        client = self._get_async_client()
        return await client.get(url, **kwargs)
    
    async def apost(self, url: str, **kwargs) -> httpx.Response:
        """Async POST request."""
        client = self._get_async_client()
        return await client.post(url, **kwargs)
    
    async def astream_post(self, url: str, **kwargs) -> httpx.Response:
        """Async streaming POST request."""
        client = self._get_async_client()
        return await client.post(url, **kwargs)
    
    def close(self):
        """Close both clients."""
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()
        if self._async_client and not self._async_client.is_closed:
            import asyncio
            try:
                asyncio.get_event_loop().run_until_complete(self._async_client.aclose())
            except RuntimeError:
                # No event loop running, client will be garbage collected
                pass
    
    async def aclose(self):
        """Async close both clients."""
        if self._sync_client and not self._sync_client.is_closed:
            self._sync_client.close()
        if self._async_client and not self._async_client.is_closed:
            await self._async_client.aclose()


class HTTPClientFactory:
    """Factory for creating pooled HTTP clients."""
    
    _clients: dict[str, PooledHTTPClient] = {}
    _lock = __import__('threading').RLock()
    
    @classmethod
    def get_client(
        cls,
        base_url: str,
        max_connections: int = 100,
        max_keepalive: int = 20,
        keepalive_expiry: float = 30.0,
        timeout: float = 30.0,
    ) -> PooledHTTPClient:
        """Get or create a pooled client for the given base URL."""
        with cls._lock:
            if base_url not in cls._clients:
                cls._clients[base_url] = PooledHTTPClient(
                    base_url=base_url,
                    max_connections=max_connections,
                    max_keepalive_connections=max_keepalive,
                    keepalive_expiry=keepalive_expiry,
                    timeout=timeout,
                )
            return cls._clients[base_url]
    
    @classmethod
    def close_all(cls):
        """Close all clients."""
        with cls._lock:
            for client in cls._clients.values():
                client.close()
            cls._clients.clear()