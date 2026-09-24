"""Self-signed TLS certificate generation for development.

Auto-generates certs to ``data/certs/`` on first boot so HTTPS works
out of the box.  Tries ``openssl`` (subprocess) first, then falls back
to ``cryptography`` (pure Python).  Produces a self-signed RSA-2048 cert
with SAN for localhost + 127.0.0.1, valid for 10 years.
"""

import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger("api.certs")

_CERTS_DIR = Path(__file__).resolve().parent.parent / "data" / "certs"
_CERT_FILE = _CERTS_DIR / "cert.pem"
_KEY_FILE = _CERTS_DIR / "key.pem"

_OPENSSL_CONFIG = """[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_req
prompt = no
[req_distinguished_name]
C = US
ST = California
L = San Diego
O = Mai AI Inc
CN = localhost
[v3_req]
keyUsage = keyEncipherment, digitalSignature
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
"""


def _try_openssl() -> bool:
    """Generate certs via ``openssl`` subprocess."""
    try:
        _CERTS_DIR.mkdir(parents=True, exist_ok=True)
        cfg = _CERTS_DIR / "openssl.cnf"
        cfg.write_text(_OPENSSL_CONFIG)
        subprocess.run(
            [
                "openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes",
                "-keyout", str(_KEY_FILE),
                "-out", str(_CERT_FILE),
                "-days", "3650",
                "-config", str(cfg),
            ],
            capture_output=True, timeout=15, check=True,
        )
        cfg.unlink(missing_ok=True)
        logger.info("Generated dev certs via openssl -> %s", _CERTS_DIR)
        return True
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired) as e:
        logger.debug("openssl cert gen failed: %s", e)
        return False


def _try_cryptography() -> bool:
    """Generate certs via the ``cryptography`` library (pure Python)."""
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        import datetime

        _CERTS_DIR.mkdir(parents=True, exist_ok=True)

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "California"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Diego"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Mai AI Inc"),
            x509.NameAttribute(NameOID.COMMON_NAME, "localhost"),
        ])

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.timezone.utc))
            .not_valid_after(datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=3650))
            .add_extension(
                x509.SubjectAlternativeName([
                    x509.DNSName("localhost"),
                    x509.IPAddress(ipaddr := __import__("ipaddress").ip_address("127.0.0.1")),
                ]),
                critical=False,
            )
            .add_extension(
                x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )

        _KEY_FILE.write_bytes(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        _CERT_FILE.write_bytes(cert.public_bytes(serialization.Encoding.PEM))

        logger.info("Generated dev certs via cryptography -> %s", _CERTS_DIR)
        return True
    except ImportError:
        logger.debug("cryptography not available for cert gen")
        return False
    except Exception as e:
        logger.warning("cryptography cert gen failed: %s", e)
        return False


def ensure_dev_certs() -> tuple[str, str]:
    """Return ``(cert_path, key_path)``, generating self-signed certs if missing.

    Tries ``openssl`` first, then ``cryptography`` as fallback.
    Returns empty strings if neither approach works.
    """
    if _CERT_FILE.is_file() and _KEY_FILE.is_file():
        return str(_CERT_FILE), str(_KEY_FILE)

    logger.info("No TLS certs found - generating self-signed certs for development...")
    if not _try_openssl():
        if not _try_cryptography():
            logger.warning(
                "Could not generate dev certs. "
                "Install openssl or 'pip install cryptography', or set API_SSL_CERTFILE / API_SSL_KEYFILE manually."
            )
            return "", ""

    if _CERT_FILE.is_file() and _KEY_FILE.is_file():
        return str(_CERT_FILE), str(_KEY_FILE)
    return "", ""
