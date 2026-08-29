"""
Enterprise Authentication & Role-Based Access Control (RBAC) for QueryDesk.
Provides cryptographically secure password hashing (PBKDF2-HMAC-SHA256)
and JWT token generation/validation with standard claims.
"""

import hmac
import hashlib
import json
import base64
import time
import secrets
from typing import Dict, Any, Optional, List
from fastapi import HTTPException, Security, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from backend.config import Config

# JWT Secret sourced from Config (which reads from ENVIRONMENT / .env)
JWT_SECRET = Config.JWT_SECRET
JWT_ALGORITHM = 'HS256'
JWT_EXPIRATION_HOURS = 24

def hash_password(password: str, salt: Optional[str] = None) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    if not salt:
        salt = "salt_" + secrets.token_hex(4)
    iterations = 100_000
    derived = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        iterations
    )
    return f"pbkdf2_sha256${iterations}${salt}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify password against PBKDF2 hash."""
    if not stored_hash or not password:
        return False
    try:
        parts = stored_hash.split('$')
        if len(parts) == 4 and parts[0] == 'pbkdf2_sha256':
            iterations = int(parts[1])
            salt = parts[2]
            expected_hex = parts[3]
            derived = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode('utf-8'),
                salt.encode('utf-8'),
                iterations
            )
            return hmac.compare_digest(derived.hex(), expected_hex)
    except Exception:
        pass
    return False


# Demo Enterprise Accounts (pre-hashed with PBKDF2)
DEMO_USERS: Dict[str, Dict[str, Any]] = {
    "admin@querydesk.io": {
        "id": "usr-admin-01",
        "email": "admin@querydesk.io",
        "name": "Alex Admin",
        "role": "admin",
        "password_hash": hash_password("admin123", salt="qd_admin_salt"),
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Alex"
    },
    "agent.sarah@querydesk.io": {
        "id": "usr-agent-01",
        "email": "agent.sarah@querydesk.io",
        "name": "Sarah Connor",
        "role": "agent",
        "password_hash": hash_password("agent123", salt="qd_sarah_salt"),
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Sarah"
    },
    "agent.marcus@querydesk.io": {
        "id": "usr-agent-02",
        "email": "agent.marcus@querydesk.io",
        "name": "Marcus Vance",
        "role": "agent",
        "password_hash": hash_password("agent123", salt="qd_marcus_salt"),
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Marcus"
    }
}


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode('utf-8').rstrip('=')


def _base64url_decode(data: str) -> bytes:
    padding = '=' * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ''
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(data: Dict[str, Any], expires_in_hours: int = JWT_EXPIRATION_HOURS) -> str:
    """Create a signed JWT token using HMAC-SHA256."""
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    now = int(time.time())
    payload = data.copy()
    payload.update({
        "iat": now,
        "exp": now + (expires_in_hours * 3600),
        "iss": "querydesk-auth-service"
    })

    header_b64 = _base64url_encode(json.dumps(header, separators=(',', ':')).encode('utf-8'))
    payload_b64 = _base64url_encode(json.dumps(payload, separators=(',', ':')).encode('utf-8'))
    
    signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
    signature = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
    signature_b64 = _base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decode and verify a signed JWT token."""
    try:
        parts = token.split('.')
        if len(parts) != 3:
            raise ValueError("Invalid JWT format")

        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode('utf-8')
        expected_sig = hmac.new(JWT_SECRET.encode('utf-8'), signing_input, hashlib.sha256).digest()
        provided_sig = _base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            raise ValueError("Invalid signature")

        payload = json.loads(_base64url_decode(payload_b64).decode('utf-8'))
        now = int(time.time())
        if "exp" in payload and payload["exp"] < now:
            raise ValueError("Token expired")

        return payload
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"}
        )


http_bearer = HTTPBearer(auto_error=False)


async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(http_bearer)) -> Optional[Dict[str, Any]]:
    """FastAPI dependency to extract and validate authenticated user."""
    if not credentials:
        return None
    token = credentials.credentials
    payload = decode_access_token(token)
    email = payload.get("sub") or payload.get("email")
    if email and email in DEMO_USERS:
        user = DEMO_USERS[email].copy()
        user.pop("password_hash", None)
        return user
    return payload


def require_roles(allowed_roles: List[str]):
    """Role-Based Access Control decorator/dependency."""
    async def role_checker(user: Optional[Dict[str, Any]] = Depends(get_current_user)):
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        user_role = user.get("role", "user")
        if user_role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Requires one of roles {allowed_roles}"
            )
        return user
    return role_checker
