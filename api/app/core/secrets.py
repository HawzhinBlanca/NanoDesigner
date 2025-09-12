"""Secrets management system for secure credential handling.

This module provides secure secrets management with encryption,
rotation, and audit logging capabilities.
"""

import os
import json
import base64
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import hvac
import boto3
from abc import ABC, abstractmethod

from ..core.structured_logging import LoggerFactory

logger = LoggerFactory.get_logger(__name__)


@dataclass
class Secret:
    """Represents a secret value with metadata."""
    name: str
    value: str
    version: int = 1
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    tags: Dict[str, str] = field(default_factory=dict)
    rotation_enabled: bool = False
    rotation_period_days: int = 90
    
    def is_expired(self) -> bool:
        """Check if secret has expired."""
        if self.expires_at:
            return datetime.now() > self.expires_at
        return False
    
    def needs_rotation(self) -> bool:
        """Check if secret needs rotation."""
        if not self.rotation_enabled:
            return False
        rotation_due = self.created_at + timedelta(days=self.rotation_period_days)
        return datetime.now() > rotation_due


class SecretProvider(ABC):
    """Abstract base class for secret providers."""
    
    @abstractmethod
    async def get_secret(self, name: str) -> Optional[str]:
        """Retrieve a secret by name."""
        pass
    
    @abstractmethod
    async def set_secret(self, name: str, value: str, **metadata) -> bool:
        """Store a secret."""
        pass
    
    @abstractmethod
    async def delete_secret(self, name: str) -> bool:
        """Delete a secret."""
        pass
    
    @abstractmethod
    async def list_secrets(self) -> List[str]:
        """List available secret names."""
        pass


class EnvironmentSecretProvider(SecretProvider):
    """Secret provider using environment variables."""
    
    def __init__(self, prefix: str = "NANODESIGNER_"):
        self.prefix = prefix
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from environment variable."""
        env_name = f"{self.prefix}{name.upper()}"
        value = os.environ.get(env_name)
        
        if value:
            logger.debug(f"Retrieved secret {name} from environment")
        else:
            logger.warning(f"Secret {name} not found in environment")
        
        return value
    
    async def set_secret(self, name: str, value: str, **metadata) -> bool:
        """Environment variables cannot be set at runtime."""
        logger.error("Cannot set secrets in environment provider")
        return False
    
    async def delete_secret(self, name: str) -> bool:
        """Environment variables cannot be deleted at runtime."""
        logger.error("Cannot delete secrets in environment provider")
        return False
    
    async def list_secrets(self) -> List[str]:
        """List secrets available in environment."""
        secrets = []
        for key in os.environ:
            if key.startswith(self.prefix):
                secret_name = key[len(self.prefix):].lower()
                secrets.append(secret_name)
        return secrets


class HashiCorpVaultProvider(SecretProvider):
    """Secret provider using HashiCorp Vault."""
    
    def __init__(self, vault_url: str, vault_token: str, mount_point: str = "secret"):
        self.client = hvac.Client(url=vault_url, token=vault_token)
        self.mount_point = mount_point
        
        if not self.client.is_authenticated():
            raise ValueError("Vault authentication failed")
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from Vault."""
        try:
            response = self.client.secrets.kv.v2.read_secret_version(
                path=name,
                mount_point=self.mount_point
            )
            value = response["data"]["data"].get("value")
            
            logger.debug(f"Retrieved secret {name} from Vault")
            return value
        except Exception as e:
            logger.error(f"Failed to retrieve secret {name} from Vault: {e}")
            return None
    
    async def set_secret(self, name: str, value: str, **metadata) -> bool:
        """Store secret in Vault."""
        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=name,
                secret={"value": value, **metadata},
                mount_point=self.mount_point
            )
            logger.info(f"Stored secret {name} in Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret {name} in Vault: {e}")
            return False
    
    async def delete_secret(self, name: str) -> bool:
        """Delete secret from Vault."""
        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=name,
                mount_point=self.mount_point
            )
            logger.info(f"Deleted secret {name} from Vault")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name} from Vault: {e}")
            return False
    
    async def list_secrets(self) -> List[str]:
        """List secrets in Vault."""
        try:
            response = self.client.secrets.kv.v2.list_secrets(
                mount_point=self.mount_point
            )
            return response.get("data", {}).get("keys", [])
        except Exception as e:
            logger.error(f"Failed to list secrets from Vault: {e}")
            return []


class AWSSecretsManagerProvider(SecretProvider):
    """Secret provider using AWS Secrets Manager."""
    
    def __init__(self, region_name: str = "us-east-1"):
        self.client = boto3.client("secretsmanager", region_name=region_name)
        self.region = region_name
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager."""
        try:
            response = self.client.get_secret_value(SecretId=name)
            
            if "SecretString" in response:
                value = response["SecretString"]
            else:
                # Binary secret
                value = base64.b64decode(response["SecretBinary"]).decode("utf-8")
            
            logger.debug(f"Retrieved secret {name} from AWS Secrets Manager")
            return value
        except self.client.exceptions.ResourceNotFoundException:
            logger.warning(f"Secret {name} not found in AWS Secrets Manager")
            return None
        except Exception as e:
            logger.error(f"Failed to retrieve secret {name}: {e}")
            return None
    
    async def set_secret(self, name: str, value: str, **metadata) -> bool:
        """Store secret in AWS Secrets Manager."""
        try:
            # Try to update existing secret
            try:
                self.client.update_secret(
                    SecretId=name,
                    SecretString=value
                )
            except self.client.exceptions.ResourceNotFoundException:
                # Create new secret
                self.client.create_secret(
                    Name=name,
                    SecretString=value,
                    Tags=[
                        {"Key": k, "Value": v}
                        for k, v in metadata.items()
                    ]
                )
            
            logger.info(f"Stored secret {name} in AWS Secrets Manager")
            return True
        except Exception as e:
            logger.error(f"Failed to store secret {name}: {e}")
            return False
    
    async def delete_secret(self, name: str) -> bool:
        """Delete secret from AWS Secrets Manager."""
        try:
            self.client.delete_secret(
                SecretId=name,
                ForceDeleteWithoutRecovery=False  # Allow recovery
            )
            logger.info(f"Scheduled deletion of secret {name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret {name}: {e}")
            return False
    
    async def list_secrets(self) -> List[str]:
        """List secrets in AWS Secrets Manager."""
        try:
            secrets = []
            paginator = self.client.get_paginator("list_secrets")
            
            for page in paginator.paginate():
                for secret in page.get("SecretList", []):
                    secrets.append(secret["Name"])
            
            return secrets
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class LocalEncryptedProvider(SecretProvider):
    """Local encrypted secret storage for development."""
    
    def __init__(self, storage_path: str = "/tmp/secrets.enc", password: Optional[str] = None):
        self.storage_path = storage_path
        self.cipher = self._create_cipher(password or os.environ.get("SECRET_KEY", "default"))
        self._cache: Dict[str, str] = {}
        self._load_secrets()
    
    def _create_cipher(self, password: str) -> Fernet:
        """Create encryption cipher from password with secure salt."""
        import secrets
        
        # Generate or load salt
        salt_file = f"{self.storage_path}.salt"
        if os.path.exists(salt_file):
            with open(salt_file, "rb") as f:
                salt = f.read()
        else:
            # Generate new random salt
            salt = secrets.token_bytes(32)
            with open(salt_file, "wb") as f:
                f.write(salt)
        
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return Fernet(key)
    
    def _load_secrets(self):
        """Load secrets from encrypted file."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "rb") as f:
                    encrypted_data = f.read()
                decrypted_data = self.cipher.decrypt(encrypted_data)
                self._cache = json.loads(decrypted_data.decode())
            except Exception as e:
                logger.error(f"Failed to load secrets: {e}")
                self._cache = {}
    
    def _save_secrets(self):
        """Save secrets to encrypted file."""
        try:
            data = json.dumps(self._cache).encode()
            encrypted_data = self.cipher.encrypt(data)
            with open(self.storage_path, "wb") as f:
                f.write(encrypted_data)
        except Exception as e:
            logger.error(f"Failed to save secrets: {e}")
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from local storage."""
        return self._cache.get(name)
    
    async def set_secret(self, name: str, value: str, **metadata) -> bool:
        """Store secret in local storage."""
        self._cache[name] = value
        self._save_secrets()
        return True
    
    async def delete_secret(self, name: str) -> bool:
        """Delete secret from local storage."""
        if name in self._cache:
            del self._cache[name]
            self._save_secrets()
            return True
        return False
    
    async def list_secrets(self) -> List[str]:
        """List secrets in local storage."""
        return list(self._cache.keys())


class SecretManager:
    """Centralized secret management with multiple providers."""
    
    def __init__(self):
        self.providers: List[SecretProvider] = []
        self._audit_log: List[Dict[str, Any]] = []
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize secret providers based on environment."""
        # Always add environment provider as fallback
        self.providers.append(EnvironmentSecretProvider())
        
        # Add Vault if configured
        vault_url = os.environ.get("VAULT_URL")
        vault_token = os.environ.get("VAULT_TOKEN")
        if vault_url and vault_token:
            try:
                self.providers.insert(0, HashiCorpVaultProvider(vault_url, vault_token))
                logger.info("Initialized HashiCorp Vault provider")
            except Exception as e:
                logger.warning(f"Failed to initialize Vault provider: {e}")
        
        # Add AWS Secrets Manager if in AWS
        if os.environ.get("AWS_REGION"):
            try:
                self.providers.insert(0, AWSSecretsManagerProvider())
                logger.info("Initialized AWS Secrets Manager provider")
            except Exception as e:
                logger.warning(f"Failed to initialize AWS provider: {e}")
        
        # Add local encrypted storage for development
        if os.environ.get("SERVICE_ENV") == "development":
            self.providers.append(LocalEncryptedProvider())
    
    async def get_secret(self, name: str) -> Optional[str]:
        """Get secret from first available provider."""
        for provider in self.providers:
            value = await provider.get_secret(name)
            if value:
                self._audit_log.append({
                    "action": "get",
                    "secret": name,
                    "provider": provider.__class__.__name__,
                    "timestamp": datetime.now().isoformat()
                })
                return value
        
        logger.error(f"Secret {name} not found in any provider")
        return None
    
    async def get_required_secret(self, name: str) -> str:
        """Get secret that must exist."""
        value = await self.get_secret(name)
        if not value:
            raise ValueError(f"Required secret {name} not found")
        return value
    
    def get_audit_log(self) -> List[Dict[str, Any]]:
        """Get audit log of secret operations."""
        return self._audit_log.copy()


# Global secret manager instance
secret_manager = SecretManager()