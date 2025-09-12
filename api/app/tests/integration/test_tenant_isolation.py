#!/usr/bin/env python3
"""Test tenant isolation system for Week 2."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.tenant_isolation import (
    TenantIsolationManager,
    QdrantTenantManager,
    PostgresTenantManager,
    TenantContext,
    IsolationLevel,
    isolation_manager
)
from fastapi import HTTPException


def test_org_id_validation():
    """Test organization ID validation."""
    print("🏢 Testing Organization ID Validation...")
    
    manager = TenantIsolationManager()
    
    # Valid org IDs
    valid_ids = ["company-123", "org_456", "startup2024", "enterprise-corp"]
    for org_id in valid_ids:
        assert manager.validate_org_id(org_id), f"Valid org ID rejected: {org_id}"
    
    print("✅ Valid org IDs accepted")
    
    # Invalid org IDs
    invalid_ids = [
        "",           # Empty
        "ab",         # Too short
        "a" * 51,     # Too long
        "org@123",    # Invalid characters
        "admin",      # Reserved name
        "system",     # Reserved name
        "../hack",    # Path traversal
    ]
    
    for org_id in invalid_ids:
        assert not manager.validate_org_id(org_id), f"Invalid org ID accepted: {org_id}"
    
    print("✅ Invalid org IDs rejected")
    print("✅ Organization ID validation tests passed!")
    return True


def test_tenant_context_creation():
    """Test tenant context creation."""
    print("👤 Testing Tenant Context Creation...")
    
    manager = TenantIsolationManager()
    
    # Valid tenant context
    tenant = manager.create_tenant_context(
        org_id="test-org",
        user_id="user123",
        permissions=["read", "write"]
    )
    
    assert tenant.org_id == "test-org"
    assert tenant.user_id == "user123"
    assert "read" in tenant.permissions
    print("✅ Valid tenant context created")
    
    # Invalid org ID should raise exception
    try:
        manager.create_tenant_context("invalid@org", "user123")
        assert False, "Should have raised exception for invalid org ID"
    except HTTPException:
        print("✅ Invalid org ID correctly rejected")
    
    # Invalid user ID should raise exception
    try:
        manager.create_tenant_context("valid-org", "invalid@user")
        assert False, "Should have raised exception for invalid user ID"
    except HTTPException:
        print("✅ Invalid user ID correctly rejected")
    
    print("✅ Tenant context creation tests passed!")
    return True


def test_qdrant_isolation():
    """Test Qdrant collection isolation."""
    print("🔍 Testing Qdrant Isolation...")
    
    manager = TenantIsolationManager()
    
    # Create tenant contexts
    tenant1 = manager.create_tenant_context("company-a", "user1")
    tenant2 = manager.create_tenant_context("company-b", "user2")
    
    # Get collection names
    collection1 = manager.get_qdrant_collection_name(tenant1, "vectors")
    collection2 = manager.get_qdrant_collection_name(tenant2, "vectors")
    
    # Collections should be different
    assert collection1 != collection2
    print(f"✅ Isolated collections: {collection1} != {collection2}")
    
    # Collections should include org ID
    assert "company-a" in collection1 or "company_a" in collection1
    assert "company-b" in collection2 or "company_b" in collection2
    print("✅ Collections contain org identifiers")
    
    # Test collection name sanitization
    long_org = "a" * 50
    tenant_long = manager.create_tenant_context(long_org, "user1")
    collection_long = manager.get_qdrant_collection_name(tenant_long, "vectors")
    
    # Should handle long names gracefully
    assert len(collection_long) <= 63  # Qdrant limit
    print("✅ Long org names handled correctly")
    
    print("✅ Qdrant isolation tests passed!")
    return True


def test_postgres_isolation():
    """Test PostgreSQL RLS isolation."""
    print("🗄️  Testing PostgreSQL Isolation...")
    
    manager = TenantIsolationManager()
    tenant = manager.create_tenant_context("test-org", "user1")
    
    # Get RLS policy
    policy = manager.get_postgres_rls_policy(tenant, "projects")
    
    # Policy should contain org_id filter
    assert "org_id = 'test-org'" in policy
    print("✅ RLS policy contains org filter")
    
    # Get query filter
    postgres_manager = PostgresTenantManager(manager)
    filter_clause = postgres_manager.get_tenant_query_filter(tenant)
    
    assert "org_id = 'test-org'" in filter_clause
    print("✅ Query filter contains org restriction")
    
    print("✅ PostgreSQL isolation tests passed!")
    return True


def test_storage_isolation():
    """Test storage path isolation."""
    print("💾 Testing Storage Isolation...")
    
    manager = TenantIsolationManager()
    
    tenant1 = manager.create_tenant_context("company-a", "user1")
    tenant2 = manager.create_tenant_context("company-b", "user2")
    
    # Get storage paths
    path1 = manager.get_storage_path(tenant1, "uploads/image.jpg")
    path2 = manager.get_storage_path(tenant2, "uploads/image.jpg")
    
    # Paths should be different
    assert path1 != path2
    print(f"✅ Isolated storage paths: {path1} != {path2}")
    
    # Paths should include org isolation
    assert "company-a" in path1 or "company_a" in path1
    assert "company-b" in path2 or "company_b" in path2
    print("✅ Storage paths contain org identifiers")
    
    # Test path traversal protection
    malicious_path = manager.get_storage_path(tenant1, "../../../etc/passwd")
    assert "../" not in malicious_path
    print("✅ Path traversal attacks prevented")
    
    print("✅ Storage isolation tests passed!")
    return True


def test_redis_isolation():
    """Test Redis key isolation."""
    print("🔑 Testing Redis Isolation...")
    
    manager = TenantIsolationManager()
    
    tenant1 = manager.create_tenant_context("company-a", "user1")
    tenant2 = manager.create_tenant_context("company-b", "user2")
    
    # Get Redis keys
    key1 = manager.get_redis_key(tenant1, "session:123")
    key2 = manager.get_redis_key(tenant2, "session:123")
    
    # Keys should be different
    assert key1 != key2
    print(f"✅ Isolated Redis keys: {key1} != {key2}")
    
    # Keys should include org prefix
    assert "company-a" in key1
    assert "company-b" in key2
    print("✅ Redis keys contain org prefixes")
    
    print("✅ Redis isolation tests passed!")
    return True


def test_cross_tenant_access():
    """Test cross-tenant access validation."""
    print("🚫 Testing Cross-Tenant Access Control...")
    
    manager = TenantIsolationManager()
    
    # Regular tenant
    tenant1 = manager.create_tenant_context("company-a", "user1", ["read", "write"])
    
    # Admin tenant
    tenant_admin = manager.create_tenant_context("company-b", "admin", ["admin:global"])
    
    # Same org access - should be allowed
    assert manager.validate_cross_tenant_access(tenant1, "company-a", "read")
    print("✅ Same-org access allowed")
    
    # Cross-org access without permissions - should be denied
    assert not manager.validate_cross_tenant_access(tenant1, "company-b", "read")
    print("✅ Cross-org access denied for regular user")
    
    # Cross-org access with admin permissions - should be allowed
    assert manager.validate_cross_tenant_access(tenant_admin, "company-a", "read")
    print("✅ Cross-org access allowed for admin")
    
    # Test enforcement
    try:
        manager.enforce_tenant_isolation(tenant1, "company-b", "read")
        assert False, "Should have raised exception"
    except HTTPException as e:
        assert e.status_code == 403
        print("✅ Cross-tenant access properly blocked")
    
    print("✅ Cross-tenant access control tests passed!")
    return True


def test_resource_limits():
    """Test tenant resource limits."""
    print("📊 Testing Resource Limits...")
    
    manager = TenantIsolationManager()
    
    # Regular tenant
    tenant_regular = manager.create_tenant_context("company-a", "user1")
    limits_regular = manager.get_tenant_resource_limits(tenant_regular)
    
    # Premium tenant
    tenant_premium = manager.create_tenant_context("company-b", "user2", ["premium"])
    limits_premium = manager.get_tenant_resource_limits(tenant_premium)
    
    # Premium should have higher limits
    assert limits_premium["max_storage_mb"] > limits_regular["max_storage_mb"]
    assert limits_premium["max_api_calls_per_hour"] > limits_regular["max_api_calls_per_hour"]
    
    print("✅ Premium tenant has higher limits")
    print(f"   Regular: {limits_regular['max_storage_mb']}MB storage")
    print(f"   Premium: {limits_premium['max_storage_mb']}MB storage")
    
    print("✅ Resource limits tests passed!")
    return True


async def test_qdrant_tenant_manager():
    """Test Qdrant tenant manager."""
    print("🔍 Testing Qdrant Tenant Manager...")
    
    manager = TenantIsolationManager()
    qdrant_manager = QdrantTenantManager(manager)
    
    tenant = manager.create_tenant_context("test-org", "user1")
    
    # Ensure collection
    collection_name = await qdrant_manager.ensure_tenant_collection(tenant, "embeddings")
    assert "test-org" in collection_name or "test_org" in collection_name
    print(f"✅ Collection created: {collection_name}")
    
    # Get tenant collections
    collections = qdrant_manager.get_tenant_collections(tenant)
    assert len(collections) >= 1
    print(f"✅ Found {len(collections)} collections for tenant")
    
    print("✅ Qdrant tenant manager tests passed!")
    return True


async def main():
    """Run all tenant isolation tests."""
    print("🏢 TENANT ISOLATION SYSTEM TESTS")
    print("=" * 50)
    
    sync_tests = [
        test_org_id_validation,
        test_tenant_context_creation,
        test_qdrant_isolation,
        test_postgres_isolation,
        test_storage_isolation,
        test_redis_isolation,
        test_cross_tenant_access,
        test_resource_limits,
    ]
    
    async_tests = [
        test_qdrant_tenant_manager
    ]
    
    passed = 0
    total = len(sync_tests) + len(async_tests)
    
    # Run sync tests
    for test in sync_tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            print()
    
    # Run async tests
    for test in async_tests:
        try:
            if await test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            print()
    
    print("=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TENANT ISOLATION TESTS PASSED!")
        return True
    else:
        print("❌ Some tenant isolation tests failed!")
        return False


if __name__ == "__main__":
    import asyncio
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
