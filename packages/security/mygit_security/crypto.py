import base64
from pathlib import Path
from typing import Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


class KeyManager:
    """Manages Ed25519 cryptographic signing keypairs for commit & tag signatures."""

    @staticmethod
    def generate_keypair() -> Tuple[str, str]:
        """Generate Ed25519 private and public key in PEM format."""
        private_key = ed25519.Ed25519PrivateKey.generate()
        public_key = private_key.public_key()

        private_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ).decode("utf-8")

        public_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode("utf-8")

        return private_pem, public_pem

    @staticmethod
    def sign(private_pem: str, data: bytes) -> str:
        """Sign data using Ed25519 private key PEM and return base64 signature."""
        private_key = serialization.load_pem_private_key(
            private_pem.encode("utf-8"), password=None
        )
        if not isinstance(private_key, ed25519.Ed25519PrivateKey):
            raise ValueError("Key is not an Ed25519 private key.")

        signature = private_key.sign(data)
        return base64.b64encode(signature).decode("utf-8")

    @staticmethod
    def verify(public_pem: str, data: bytes, signature_b64: str) -> bool:
        """Verify base64 Ed25519 signature against data."""
        try:
            public_key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
            if not isinstance(public_key, ed25519.Ed25519PublicKey):
                return False

            signature = base64.b64decode(signature_b64.encode("utf-8"))
            public_key.verify(signature, data)
            return True
        except (InvalidSignature, Exception):
            return False
