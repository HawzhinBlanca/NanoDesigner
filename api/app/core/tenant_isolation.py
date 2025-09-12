"""Tenant isolation system for multi-org security."""

import hashlib
import re
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum

from fastapi import HTTPException, status


class IsolationLevel(Enum):
    """Tenant isolation levels."""
    SHARED = "shared"          # Shared resources with logical separation
    ISOLATED = "isolated"      # Dedicated resources per tenant
    ENCRYPTED = "encrypted"    # Encrypted isolation with separate keys


@dataclass
class TenantContext:
    """Tenant context for isolation."""
    org_id: str
    user_id: str
    isolation_level: IsolationLevel
    permissions: List[str]
    metadata: Dict[str, Any] = None


class TenantIsolationManager:
    """Manages tenant isolation across all services."""
    
    def __init__(self):
        self.isolation_config = self._load_isolation_config()
    
    def _load_isolation_config(self) -> Dict[str, Any]:
        """Load tenant isolation configuration."""
        return {
            "qdrant": {
                "collection_prefix": "org_",
                "isolation_level": IsolationLevel.ISOLATED,
                "max_collections_per_org": 10
            },
            "postgres": {
                "enable_rls": True,
                "isolation_level": IsolationLevel.ISOLATED,
                "schema_per_org": False
            },
            "storage": {
                "prefix_strategy": "org_id",
                "isolation_level": IsolationLevel.ISOLATED,
                "encryption_per_org": True
            },
            "redis": {
                "key_prefix": "org:",
                "isolation_level": IsolationLevel.SHARED,
                "separate_dbs": False
            }
        }
    
    def validate_org_id(self, org_id: str) -> bool:
        """Validate organization ID format and security."""
        if not org_id:
            return False
        
        # Must be alphanumeric with hyphens/underscores, 3-50 chars
        if not re.match(r'^[a-zA-Z0-9_-]{3,50}$', org_id):
            return False
        
        # Cannot be reserved names
        reserved_names = {
            'admin', 'root', 'system', 'public', 'private', 'internal',
            'api', 'www', 'mail', 'ftp', 'test', 'staging', 'prod'
        }
        if org_id.lower() in reserved_names:
            return False
        
        return True
    
    def create_tenant_context(self, org_id: str, user_id: str, 
                            permissions: List[str] = None) -> TenantContext:
        """Create tenant context with validation."""
        if not self.validate_org_id(org_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid organization ID: {org_id}"
            )
        
        if not user_id or not re.match(r'^[a-zA-Z0-9_-]{1,100}$', user_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid user ID: {user_id}"
            )
        
        return TenantContext(
            org_id=org_id,
            user_id=user_id,
            isolation_level=IsolationLevel.ISOLATED,
            permissions=permissions or [],
            metadata={}
        )
    
    def get_qdrant_collection_name(self, tenant: TenantContext, 
                                 collection_type: str = "vectors") -> str:
        """Generate isolated Qdrant collection name."""
        config = self.isolation_config["qdrant"]
        
        # Sanitize collection type
        collection_type = re.sub(r'[^a-zA-Z0-9_]', '_', collection_type)
        
        # Create collection name with org isolation
        collection_name = f"{config['collection_prefix']}{tenant.org_id}_{collection_type}"
        
        # Ensure collection name is valid for Qdrant
        collection_name = re.sub(r'[^a-zA-Z0-9_-]', '_', collection_name)
        
        # Limit length (Qdrant has collection name limits)
        if len(collection_name) > 63:
            # Hash the org_id to ensure uniqueness while keeping length manageable
            org_hash = hashlib.sha256(tenant.org_id.encode()).hexdigest()[:8]
            collection_name = f"{config['collection_prefix']}{org_hash}_{collection_type}"
        
        return collection_name
    
    def get_postgres_rls_policy(self, tenant: TenantContext, table_name: str) -> str:
        """Generate Postgres Row Level Security policy."""
        config = self.isolation_config["postgres"]
        
        if not config["enable_rls"]:
            return ""
        
        # Create RLS policy that filters by org_id
        policy_name = f"tenant_isolation_{table_name}_{tenant.org_id}"
        
        return f"""
        CREATE POLICY {policy_name} ON {table_name}
        FOR ALL TO authenticated
        USING (org_id = '{tenant.org_id}')
        WITH CHECK (org_id = '{tenant.org_id}');
        """
    
    def get_storage_path(self, tenant: TenantContext, object_key: str) -> str:
        """Generate isolated storage path."""
        config = self.isolation_config["storage"]
        
        # Sanitize object key
        object_key = re.sub(r'[^a-zA-Z0-9._/-]', '_', object_key)
        
        # Remove any path traversal attempts
        object_key = re.sub(r'\.\./', '', object_key)
        object_key = object_key.lstrip('/')
        
        if config["prefix_strategy"] == "org_id":
            return f"orgs/{tenant.org_id}/{object_key}"
        else:
            # Hash-based isolation for additional security
            org_hash = hashlib.sha256(tenant.org_id.encode()).hexdigest()[:16]
            return f"isolated/{org_hash}/{object_key}"
    
    def get_redis_key(self, tenant: TenantContext, key: str) -> str:
        """Generate isolated Redis key."""
        config = self.isolation_config["redis"]
        
        # Sanitize key
        key = re.sub(r'[^a-zA-Z0-9:._-]', '_', key)
        
        return f"{config['key_prefix']}{tenant.org_id}:{key}"
    
    def validate_cross_tenant_access(self, requesting_tenant: TenantContext,
                                   resource_org_id: str, 
                                   operation: str = "read") -> bool:
        """Validate if tenant can access resource from another org."""
        
        # Same org - always allowed
        if requesting_tenant.org_id == resource_org_id:
            return True
        
        # Check if user has cross-tenant permissions
        cross_tenant_permissions = [
            "admin:global",
            f"cross_tenant:{operation}",
            f"org:{resource_org_id}:{operation}"
        ]
        
        return any(perm in requesting_tenant.permissions for perm in cross_tenant_permissions)
    
    def enforce_tenant_isolation(self, tenant: TenantContext, 
                               resource_org_id: str,
                               operation: str = "read"):
        """Enforce tenant isolation - raise exception if access denied."""
        if not self.validate_cross_tenant_access(tenant, resource_org_id, operation):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": "Cross-tenant access denied",
                    "requesting_org": tenant.org_id,
                    "resource_org": resource_org_id,
                    "operation": operation
                }
            )
    
    def get_tenant_resource_limits(self, tenant: TenantContext) -> Dict[str, int]:
        """Get resource limits for tenant."""
        # Default limits - could be loaded from database
        base_limits = {
            "max_storage_mb": 1000,
            "max_api_calls_per_hour": 1000,
            "max_concurrent_requests": 10,
            "max_file_uploads_per_day": 100,
            "max_vector_collections": 5
        }
        
        # Check if tenant has premium permissions
        if "premium" in tenant.permissions:
            return {
                "max_storage_mb": 10000,
                "max_api_calls_per_hour": 10000,
                "max_concurrent_requests": 50,
                "max_file_uploads_per_day": 1000,
                "max_vector_collections": 20
            }
        
        return base_limits
    
    def log_tenant_access(self, tenant: TenantContext, resource: str, 
                         operation: str, success: bool):
        """Log tenant access for audit purposes."""
        log_entry = {
            "timestamp": "now",  # Would use proper timestamp
            "org_id": tenant.org_id,
            "user_id": tenant.user_id,
            "resource": resource,
            "operation": operation,
            "success": success,
            "isolation_level": tenant.isolation_level.value
        }
        
        # In production, this would go to a secure audit log
        print(f"🔍 TENANT ACCESS: {log_entry}")


class QdrantTenantManager:
    """Qdrant-specific tenant isolation."""
    
    def __init__(self, isolation_manager: TenantIsolationManager):
        self.isolation_manager = isolation_manager
        self.collections_cache = {}
    
    async def ensure_tenant_collection(self, tenant: TenantContext, 
                                     collection_type: str = "vectors") -> str:
        """Ensure tenant has isolated collection."""
        collection_name = self.isolation_manager.get_qdrant_collection_name(
            tenant, collection_type
        )
        
        # In production, this would create the collection if it doesn't exist
        # For now, just return the name
        self.collections_cache[f"{tenant.org_id}:{collection_type}"] = collection_name
        
        return collection_name
    
    def get_tenant_collections(self, tenant: TenantContext) -> List[str]:
        """Get all collections for tenant."""
        prefix = f"{tenant.org_id}:"
        return [
            collection for key, collection in self.collections_cache.items()
            if key.startswith(prefix)
        ]


class PostgresTenantManager:
    """PostgreSQL-specific tenant isolation."""
    
    def __init__(self, isolation_manager: TenantIsolationManager):
        self.isolation_manager = isolation_manager
    
    def get_tenant_query_filter(self, tenant: TenantContext) -> str:
        """Get SQL filter for tenant isolation."""
        return f"org_id = '{tenant.org_id}'"
    
    def setup_rls_policies(self, tenant: TenantContext, tables: List[str]) -> List[str]:
        """Setup RLS policies for tenant."""
        policies = []
        for table in tables:
            policy = self.isolation_manager.get_postgres_rls_policy(tenant, table)
            if policy:
                policies.append(policy)
        return policies


# Global isolation manager
isolation_manager = TenantIsolationManager()
qdrant_tenant_manager = QdrantTenantManager(isolation_manager)
postgres_tenant_manager = PostgresTenantManager(isolation_manager)
