"""JWT-based authentication for the Mai AI API.

Provides token creation, password hashing, and a FastAPI dependency
for protecting routes. Supports both JWT bearer tokens and the legacy
``API_AUTH_TOKEN`` static bearer token. Also supports OIDC/SAML providers
for enterprise single sign-on.
"""

import logging
import os
import hashlib
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List, Set
from urllib.parse import urlencode

import bcrypt
import httpx
from fastapi import HTTPException, Request, Depends, Response, Form, APIRouter
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography import x509
from lxml import etree

logger = logging.getLogger("api.auth")

_JWT_SECRET: str = ""
_JWT_ALGORITHM = "HS256"
_ACCESS_EXPIRE_MINUTES = 15
_REFRESH_EXPIRE_DAYS = 7

# JWT Key Rotation
_JWT_KEYS: Dict[str, Dict[str, Any]] = {}  # kid -> {key, alg, created_at, expires_at}
_JWT_CURRENT_KID: str = "default"
_JWT_KEY_ROTATION_INTERVAL_DAYS = 30

# OIDC/SAML Configuration
_OIDC_PROVIDERS: Dict[str, Dict[str, Any]] = {}
_SAML_PROVIDERS: Dict[str, Dict[str, Any]] = {}

_bearer_scheme = HTTPBearer(auto_error=False)


# ── Config ───────────────────────────────────────────────────────────────
def configure(jwt_secret: str = "", access_expire_minutes: int = 15, refresh_expire_days: int = 7):
    global _JWT_SECRET, _ACCESS_EXPIRE_MINUTES, _REFRESH_EXPIRE_DAYS
    _JWT_SECRET = jwt_secret or _auto_secret()
    _ACCESS_EXPIRE_MINUTES = access_expire_minutes
    _REFRESH_EXPIRE_DAYS = refresh_expire_days
    _init_jwt_keys()


def _auto_secret() -> str:
    """Generate a persistent pseudo-random secret from a machine-local seed."""
    seed = f"{os.name}-{os.environ.get('COMPUTERNAME', '')}-{os.environ.get('USERNAME', '')}-mai-jwt"
    return hashlib.sha256(seed.encode()).hexdigest()


# ── JWT Key Rotation ──────────────────────────────────────────────────────
def _generate_key_pair() -> tuple[str, str]:
    """Generate a new RSA key pair for JWT signing."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode()
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode()
    return private_pem, public_pem


def _generate_kid() -> str:
    """Generate a unique key ID."""
    return secrets.token_urlsafe(16)


def _get_current_key() -> Dict[str, Any]:
    """Get the current active signing key."""
    return _JWT_KEYS.get(_JWT_CURRENT_KID, {})


def _get_key_by_kid(kid: str) -> Optional[Dict[str, Any]]:
    """Get a key by its key ID."""
    return _JWT_KEYS.get(kid)


def _rotate_jwt_keys() -> str:
    """Rotate to a new JWT signing key."""
    global _JWT_CURRENT_KID
    
    # Generate new key pair
    private_pem, public_pem = _generate_key_pair()
    new_kid = _generate_kid()
    
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=_JWT_KEY_ROTATION_INTERVAL_DAYS)
    
    # Add new key
    _JWT_KEYS[new_kid] = {
        "private": private_pem,
        "public": public_pem,
        "alg": "RS256",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": expires_at.isoformat(),
    }
    
    # Mark old key as expired (but keep for verification)
    old_kid = _JWT_CURRENT_KID
    if old_kid in _JWT_KEYS:
        _JWT_KEYS[old_kid]["expires_at"] = datetime.now(timezone.utc).isoformat()
    
    # Set new key as current
    _JWT_CURRENT_KID = new_kid
    
    logger.info(f"Rotated JWT key: {old_kid} -> {new_kid}")
    return new_kid


def _init_jwt_keys() -> None:
    """Initialize JWT keys on startup."""
    global _JWT_KEYS, _JWT_CURRENT_KID
    
    if not _JWT_KEYS:
        # Generate initial key pair
        private_pem, public_pem = _generate_key_pair()
        kid = _generate_kid()
        
        now = datetime.now(timezone.utc)
        expires_at = datetime.now(timezone.utc) + timedelta(days=_JWT_KEY_ROTATION_INTERVAL_DAYS)
        
        _JWT_KEYS[kid] = {
            "private": private_pem,
            "public": public_pem,
            "alg": "RS256",
            "created_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
        }
        _JWT_CURRENT_KID = kid
        logger.info(f"Initialized JWT keys with kid: {kid}")


def _get_signing_key(kid: Optional[str] = None) -> tuple[str, str]:
    """Get the signing key and algorithm for a given kid."""
    if kid is None:
        kid = _JWT_CURRENT_KID
    if not _JWT_KEYS:
        _init_jwt_keys()
        kid = _JWT_CURRENT_KID

    key_info = _JWT_KEYS.get(kid)
    if not key_info:
        raise ValueError(f"No key found for kid: {kid}")
    
    # Check if key is expired
    expires_at = datetime.fromisoformat(key_info["expires_at"].replace('Z', '+00:00'))
    if datetime.now(timezone.utc) > expires_at:
        # Try to rotate
        _rotate_jwt_keys()
        kid = _JWT_CURRENT_KID
        key_info = _JWT_KEYS[kid]
    
    return key_info["private"], key_info["alg"]


def _get_verification_keys() -> Dict[str, Any]:
    """Get all valid verification keys for JWKS endpoint."""
    now = datetime.now(timezone.utc)
    valid_keys = {}
    for kid, info in _JWT_KEYS.items():
        expires_at = datetime.fromisoformat(info["expires_at"].replace('Z', '+00:00'))
        if now < expires_at:
            valid_keys[kid] = {
                "kty": "RSA",
                "kid": kid,
                "use": "sig",
                "alg": info["alg"],
                "n": _get_public_modulus(info["public"]),
                "e": "AQAB",
            }
    return {"keys": list(valid_keys.values())}


def _get_public_modulus(pem: str) -> str:
    """Extract modulus from PEM public key."""
    public_key = serialization.load_pem_public_key(pem.encode())
    numbers = public_key.public_numbers()
    n = numbers.n
    return base64.urlsafe_b64encode(n.to_bytes((n.bit_length() + 7) // 8, 'big')).decode().rstrip('=')


# ── Password helpers (bcrypt directly, no passlib) ───────────────────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


# ── OIDC Provider Configuration ───────────────────────────────────────────
class OIDCProviderConfig:
    """OpenID Connect Provider Configuration."""
    
    def __init__(
        self,
        issuer: str,
        client_id: str,
        client_secret: str,
        redirect_uri: str,
        scopes: List[str] = None,
        issuer_url: str = "",
        jwks_uri: str = "",
        authorization_endpoint: str = "",
        token_endpoint: str = "",
        userinfo_endpoint: str = "",
    ):
        self.issuer = issuer
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.scopes = scopes or ["openid", "email", "profile"]
        self.issuer_url = issuer_url or f"{issuer}/.well-known/openid-configuration"
        self.jwks_uri = jwks_uri or f"{issuer}/.well-known/jwks.json"
        self.authorization_endpoint = authorization_endpoint or f"{issuer}/authorize"
        self.token_endpoint = token_endpoint or f"{issuer}/token"
        self.userinfo_endpoint = userinfo_endpoint or f"{issuer}/userinfo"
        self._jwks_cache: Optional[Dict] = None
        self._jwks_fetched_at: float = 0

    async def fetch_jwks(self) -> Dict[str, Any]:
        """Fetch and cache JWKS from the provider."""
        import time
        if self._jwks_cache and (time.time() - self._jwks_fetched_at) < 3600:
            return self._jwks_cache
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.jwks_uri)
            response.raise_for_status()
            self._jwks_cache = response.json()
            self._jwks_fetched_at = time.time()
            return self._jwks_cache

    def get_signing_key(self, kid: str) -> Optional[rsa.RSAPublicKey]:
        """Get the RSA public key for a given key ID."""
        jwks = self.fetch_jwks()
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return rsa.RSAPublicKey.from_jwk(key)
        return None


def configure_oidc_provider(
    name: str,
    issuer: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: List[str] = None,
    **kwargs,
) -> OIDCProviderConfig:
    """Configure an OIDC provider."""
    provider = OIDCProviderConfig(
        issuer=issuer,
        client_id=client_id,
        client_secret=client_secret,
        redirect_uri=redirect_uri,
        scopes=scopes,
        **kwargs,
    )
    _OIDC_PROVIDERS[name] = provider
    logger.info("Configured OIDC provider: %s", name)
    return provider


def get_oidc_provider(name: str) -> Optional[OIDCProviderConfig]:
    """Get configured OIDC provider by name."""
    return _OIDC_PROVIDERS.get(name)


def list_oidc_providers() -> List[str]:
    """List configured OIDC providers."""
    return list(_OIDC_PROVIDERS.keys())


# ── Token helpers ────────────────────────────────────────────────────────
def create_access_token(subject: str, extra: Optional[dict] = None) -> str:
    from jose import jwt
    private_key, alg = _get_signing_key()
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=_ACCESS_EXPIRE_MINUTES),
        "iat": datetime.now(timezone.utc),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, private_key, algorithm=alg, headers={"kid": _JWT_CURRENT_KID})


def create_refresh_token(subject: str) -> str:
    from jose import jwt
    private_key, alg = _get_signing_key()
    payload = {
        "sub": subject,
        "exp": datetime.now(timezone.utc) + timedelta(days=_REFRESH_EXPIRE_DAYS),
        "iat": datetime.now(timezone.utc),
        "type": "refresh",
    }
    return jwt.encode(payload, private_key, algorithm=alg, headers={"kid": _JWT_CURRENT_KID})


def decode_token(token: str) -> dict:
    from jose import JWTError, jwt
    try:
        # Get the key ID from the token header
        header = jwt.get_unverified_header(token)
        kid = header.get("kid", _JWT_CURRENT_KID)
        
        key_info = _JWT_KEYS.get(kid)
        if not key_info:
            raise JWTError(f"No key found for kid: {kid}")
        
        public_key = serialization.load_pem_public_key(key_info["public"].encode())
        
        return jwt.decode(
            token,
            public_key,
            algorithms=[key_info["alg"]],
            audience=None,  # No audience validation for now
            options={"verify_exp": True}
        )
    except JWTError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Token validation failed: {e}")


# ── SAML Provider Configuration ───────────────────────────────────────────
class SAMLProviderConfig:
    """SAML 2.0 Service Provider Configuration."""
    
    def __init__(
        self,
        entity_id: str,
        acs_url: str,
        slo_url: Optional[str] = None,
        x509_cert: str = "",
        private_key: str = "",
        idp_entity_id: str = "",
        idp_sso_url: str = "",
        idp_slo_url: Optional[str] = None,
        idp_x509_cert: str = "",
    ):
        self.entity_id = entity_id
        self.acs_url = acs_url
        self.slo_url = slo_url
        self.x509_cert = x509_cert
        self.private_key = private_key
        self.idp_entity_id = idp_entity_id
        self.idp_sso_url = idp_sso_url
        self.idp_slo_url = idp_slo_url
        self.idp_x509_cert = idp_x509_cert
    
    def get_sp_metadata(self) -> str:
        """Generate SP metadata XML."""
        from lxml import etree
        root = etree.Element(
            "md:EntityDescriptor",
            xmlns="urn:oasis:names:tc:SAML:2.0:metadata",
            entityID=self.entity_id,
        )
        sp_sso = etree.SubElement(root, "md:SPSSODescriptor")
        sp_sso.set("protocolSupportEnumeration", "urn:oasis:names:tc:SAML:2.0:protocol")
        # Add certificates, endpoints, etc.
        return etree.tostring(root, pretty_print=True).decode()


_SAML_PROVIDERS: Dict[str, SAMLProviderConfig] = {}


def configure_saml_provider(
    name: str,
    entity_id: str,
    acs_url: str,
    x509_cert: str,
    private_key: str,
    idp_entity_id: str,
    idp_sso_url: str,
    idp_x509_cert: str,
    **kwargs,
) -> SAMLProviderConfig:
    """Configure a SAML 2.0 provider."""
    provider = SAMLProviderConfig(
        entity_id=entity_id,
        acs_url=acs_url,
        x509_cert=x509_cert,
        private_key=private_key,
        idp_entity_id=idp_entity_id,
        idp_sso_url=idp_sso_url,
        idp_x509_cert=idp_x509_cert,
        **kwargs,
    )
    _SAML_PROVIDERS[name] = provider
    logger.info("Configured SAML provider: %s", name)
    return provider


def get_saml_provider(name: str) -> Optional[SAMLProviderConfig]:
    """Get configured SAML provider by name."""
    return _SAML_PROVIDERS.get(name)


def list_saml_providers() -> List[str]:
    """List configured SAML providers."""
    return list(_SAML_PROVIDERS.keys())


# ── FastAPI dependencies ─────────────────────────────────────────────────
def get_current_user(
    request: Request,
) -> str:
    """Validate bearer token and return the ``sub`` (user id).

    Supports:
    1. JWT ``access_token`` from ``/api/auth/login``
    2. Legacy static ``API_AUTH_TOKEN``
    """
    from app.config_loader import API_AUTH_TOKEN, API_REQUIRE_AUTH

    if not API_REQUIRE_AUTH:
        return "anonymous"

    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = auth_header[len("Bearer "):]

    # Legacy static token check
    if API_AUTH_TOKEN and token == API_AUTH_TOKEN:
        return "admin"

    # JWT check
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise HTTPException(status_code=401, detail="Token is not an access token")
        return payload.get("sub", "unknown")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")


# ── OIDC/SAML Authentication Endpoints ──────────────────────────────────
oidc_router = APIRouter(prefix="/api/auth/oidc", tags=["OIDC"])
saml_router = APIRouter(prefix="/api/auth/saml", tags=["SAML"])


@oidc_router.get("/login/{provider_name}")
async def oidc_login(provider_name: str, request: Request, redirect_after: str = "/"):
    """Initiate OIDC login flow."""
    provider = get_oidc_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"OIDC provider '{provider_name}' not configured")
    
    # Generate state and nonce for security
    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(32)
    
    # Store state in session/cache with TTL
    # (In production, use Redis or similar with TTL)
    
    params = {
        "client_id": provider.client_id,
        "redirect_uri": provider.redirect_uri,
        "response_type": "code",
        "scope": " ".join(provider.scopes),
        "state": state,
        "nonce": nonce,
    }
    
    auth_url = f"{provider.authorization_endpoint}?{urlencode(params)}"
    response = RedirectResponse(url=auth_url)
    response.set_cookie("oidc_state", state, httponly=True, max_age=600)
    response.set_cookie("oidc_nonce", nonce, httponly=True, max_age=600)
    response.set_cookie("redirect_after", redirect_after, httponly=True, max_age=600)
    return response


@oidc_router.get("/callback/{provider_name}")
async def oidc_callback(provider_name: str, request: Request, code: str = "", state: str = "", error: str = ""):
    """Handle OIDC callback from provider."""
    provider = get_oidc_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"OIDC provider '{provider_name}' not configured")
    
    if error:
        raise HTTPException(status_code=400, detail=f"OIDC error: {error}")
    
    # Verify state
    stored_state = request.cookies.get("oidc_state")
    if not stored_state or stored_state != state:
        raise HTTPException(status_code=400, detail="Invalid state parameter")
    
    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            provider.token_endpoint,
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": provider.redirect_uri,
                "client_id": provider.client_id,
                "client_secret": provider.client_secret,
            },
            headers={"Accept": "application/json"},
        )
        token_data = token_response.json()
    
    # Verify ID token
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="No ID token in response")
    
    # Validate ID token
    try:
        claims = await validate_id_token(id_token, provider)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid ID token: {e}")
    
    # Verify nonce
    stored_nonce = request.cookies.get("oidc_nonce")
    if claims.get("nonce") != stored_nonce:
        raise HTTPException(status_code=400, detail="Invalid nonce")
    
    # Create user session
    user_id = claims.get("sub") or claims.get("email")
    access_token = create_access_token(user_id, extra={"auth_method": "oidc", "provider": provider_name})
    refresh_token = create_refresh_token(user_id)
    
    redirect_after = request.cookies.get("redirect_after", "/")
    response = RedirectResponse(url=redirect_after)
    response.set_cookie("access_token", access_token, httponly=True, max_age=900)
    response.set_cookie("refresh_token", refresh_token, httponly=True, max_age=604800)
    response.delete_cookie("oidc_state")
    response.delete_cookie("oidc_nonce")
    response.delete_cookie("redirect_after")
    
    return response


async def validate_id_token(id_token: str, provider: OIDCProviderConfig) -> dict:
    """Validate OIDC ID token."""
    jwks = await provider.fetch_jwks()
    header = jwt.get_unverified_header(id_token)
    kid = header.get("kid")
    key = provider.get_signing_key(kid)
    if not key:
        raise ValueError("No matching signing key found")
    
    claims = jwt.decode(
        id_token,
        key,
        algorithms=["RS256"],
        audience=provider.client_id,
        issuer=provider.issuer,
        options={"verify_exp": True, "verify_iss": True},
    )
    return claims


# SAML SP-initiated login
@saml_router.get("/login/{provider_name}")
async def saml_login(provider_name: str, request: Request, relay_state: str = "/"):
    provider = get_saml_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"SAML provider '{provider_name}' not configured")
    
    # Generate SAML AuthnRequest
    from saml2 import Saml2Config
    from saml2.client import Saml2Client
    
    config = Saml2Config()
    config.entityid = "http://localhost:8000/api/auth/saml/metadata"
    config.allow_unknown_attributes = True
    config.service.sp = {
        "endpoints": {
            "assertion_consumer_service": [
                (f"{request.base_url}api/auth/saml/acs/{provider_name}", "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"),
            ],
        }
    }
    
    client = Saml2Client(config)
    req_id, authn_request = client.prepare_for_authenticate(
        entityid=provider.idp_entity_id,
        relay_state="/",
    )
    
    # Store request ID in session
    response = RedirectResponse(url=authn_request["headers"][0][1])
    response.set_cookie("saml_request_id", req_id, httponly=True, max_age=600)
    response.set_cookie("saml_relay_state", relay_state, httponly=True, max_age=600)
    return response


@saml_router.post("/acs/{provider_name}")
async def saml_acs(provider_name: str, request: Request, SAMLResponse: str = Form(...), RelayState: str = ""):
    """SAML Assertion Consumer Service endpoint."""
    provider = get_saml_provider(provider_name)
    if not provider:
        raise HTTPException(status_code=404, detail=f"SAML provider '{provider_name}' not configured")
    
    # Parse and validate SAML response
    from saml2.response import AuthnResponse
    from saml2 import config as saml_config
    
    config = saml_config.Config()
    # ... configure SP settings from provider ...
    
    client = Saml2Client(config)
    authn_response = client.parse_authn_request_response(
        SAMLResponse,
        entity_id=provider.idp_entity_id,
    )
    
    # Extract user identity
    user_id = authn_response.get_subject().text
    attributes = authn_response.get_identity()
    
    # Create session
    access_token = create_access_token(user_id, extra={"auth_method": "saml", "provider": provider_name})
    refresh_token = create_refresh_token(user_id)
    
    redirect_after = RelayState or "/"
    response = RedirectResponse(url=redirect_after)
    response.set_cookie("access_token", access_token, httponly=True, max_age=900)
    response.set_cookie("refresh_token", refresh_token, httponly=True, max_age=604800)
    
    return response


# ── RBAC (Role-Based Access Control) ────────────────────────────────────────
class Role:
    """Role definition with permissions."""
    def __init__(self, name: str, description: str, permissions: List[str]):
        self.name = name
        self.description = description
        self.permissions = set(permissions)

    def has_permission(self, permission: str) -> bool:
        return permission in self.permissions


# Predefined roles
DEFAULT_ROLES = {
    "admin": Role("admin", "Full administrative access", ["*"]),
    "operator": Role("operator", "Operational access", ["read", "write", "execute"]),
    "viewer": Role("viewer", "Read-only access", ["read"]),
    "developer": Role("developer", "Development access", ["read", "write", "execute"]),
    "auditor": Role("auditor", "Audit access", ["read", "audit"]),
}

_ROLE_REGISTRY: Dict[str, Role] = {name: role for name, role in DEFAULT_ROLES.items()}
_USER_ROLES: Dict[str, Set[str]] = {}  # user_id -> set of role names


def register_role(role: Role) -> None:
    """Register a custom role."""
    _ROLE_REGISTRY[role.name] = role
    logger.info("Registered role: %s", role.name)


def get_role(name: str) -> Optional[Role]:
    """Get a role by name."""
    return _ROLE_REGISTRY.get(name)


def assign_role(user_id: str, role_name: str) -> bool:
    """Assign a role to a user."""
    if role_name not in _ROLE_REGISTRY:
        return False
    if user_id not in _USER_ROLES:
        _USER_ROLES[user_id] = set()
    _USER_ROLES[user_id].add(role_name)
    logger.info("Assigned role %s to user %s", role_name, user_id)
    return True


def revoke_role(user_id: str, role_name: str) -> bool:
    """Revoke a role from a user."""
    if user_id in _USER_ROLES:
        _USER_ROLES[user_id].discard(role_name)
        logger.info("Revoked role %s from user %s", role_name, user_id)
        return True
    return False


def get_user_roles(user_id: str) -> List[str]:
    """Get all roles assigned to a user."""
    return list(_USER_ROLES.get(user_id, set()))


def check_permission(user_id: str, permission: str) -> bool:
    """Check if a user has a specific permission."""
    user_roles = _USER_ROLES.get(user_id, set())
    for role_name in user_roles:
        role = _ROLE_REGISTRY.get(role_name)
        if role and role.has_permission(permission):
            return True
    return False


def require_permission(permission: str):
    """FastAPI dependency for permission-based access control."""
    async def permission_checker(user_id: str = Depends(get_current_user)) -> str:
        if not check_permission(user_id, permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: requires '{permission}'"
            )
        return user_id
    return permission_checker


def require_role(role_name: str):
    """FastAPI dependency for role-based access control."""
    async def role_checker(user_id: str = Depends(get_current_user)) -> str:
        user_roles = get_user_roles(user_id)
        if role_name not in user_roles:
            raise HTTPException(
                status_code=403,
                detail=f"Role required: {role_name}"
            )
        return user_id
    return role_checker


# Include routers
__all__ = [
    "router",
    "oidc_router",
    "saml_router",
    "configure_oidc_provider",
    "get_oidc_provider",
    "list_oidc_providers",
    "configure_saml_provider",
    "get_saml_provider",
    "list_saml_providers",
    # RBAC
    "Role",
    "DEFAULT_ROLES",
    "register_role",
    "get_role",
    "assign_role",
    "revoke_role",
    "get_user_roles",
    "check_permission",
    "require_permission",
    "require_role",
]
