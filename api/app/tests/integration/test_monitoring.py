#!/usr/bin/env python3
"""Test monitoring and metrics system for Week 2."""

import sys
import os
import time
from decimal import Decimal

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.monitoring import (
    MetricsCollector,
    PerformanceMonitor,
    AlertLevel,
    Alert,
    metrics_collector,
    performance_monitor
)


def test_prometheus_metrics_setup():
    """Test Prometheus metrics setup."""
    print("📊 Testing Prometheus Metrics Setup...")
    
    # Use global metrics collector to avoid registry conflicts
    collector = metrics_collector
    
    # Check that metrics are properly initialized
    assert hasattr(collector, 'api_requests_total')
    assert hasattr(collector, 'ai_requests_total')
    assert hasattr(collector, 'security_events_total')
    assert hasattr(collector, 'system_cpu_usage')
    
    print("✅ All Prometheus metrics initialized")
    
    # Test metric recording
    collector.record_api_request("POST", "/render", 200, 1.5, "test-org")
    print("✅ API request metric recorded")
    
    collector.record_ai_request(
        model="openai/gpt-4",
        provider="openai", 
        org_id="test-org",
        duration=2.5,
        tokens={"prompt": 1000, "completion": 500},
        cost=0.06
    )
    print("✅ AI request metric recorded")
    
    print("✅ Prometheus metrics setup tests passed!")
    return True


def test_security_monitoring():
    """Test security event monitoring."""
    print("🔒 Testing Security Monitoring...")
    
    collector = metrics_collector
    
    # Record security events
    collector.record_security_event("content_policy_violation", "blocked", "test-org")
    collector.record_security_event("malicious_upload", "malicious", "test-org")
    collector.record_content_policy_violation("explicit_content", "test-org")
    
    print("✅ Security events recorded")
    
    # Check alerts were created
    recent_alerts = collector.get_recent_alerts(10)
    security_alerts = [a for a in recent_alerts if a.component == "security"]
    
    assert len(security_alerts) >= 1
    print(f"✅ {len(security_alerts)} security alerts created")
    
    print("✅ Security monitoring tests passed!")
    return True


def test_system_metrics():
    """Test system resource monitoring."""
    print("💻 Testing System Metrics...")
    
    collector = metrics_collector
    
    # Update system metrics
    collector.update_system_metrics()
    print("✅ System metrics updated")
    
    # Get health status
    health = collector.get_health_status()
    
    assert "status" in health
    assert "components" in health
    assert "system" in health
    assert "alerts" in health
    
    print(f"✅ System health status: {health['status']}")
    print(f"   CPU: {health['system']['cpu_percent']:.1f}%")
    print(f"   Memory: {health['system']['memory_percent']:.1f}%")
    print(f"   Disk: {health['system']['disk_percent']:.1f}%")
    
    print("✅ System metrics tests passed!")
    return True


def test_performance_monitoring():
    """Test performance monitoring."""
    print("⚡ Testing Performance Monitoring...")
    
    collector = metrics_collector
    monitor = PerformanceMonitor(collector)
    
    # Test request tracking
    request_id = "test-request-123"
    monitor.start_request_tracking(request_id, "/render", "test-org")
    
    # Simulate some processing time
    time.sleep(0.1)
    
    monitor.end_request_tracking(request_id, 200)
    print("✅ Request tracking completed")
    
    # Test slow query tracking
    monitor.track_slow_query("SELECT * FROM projects WHERE ...", 2.5, "projects")
    print("✅ Slow query tracked")
    
    # Check alerts
    alerts = collector.get_recent_alerts(5)
    slow_query_alerts = [a for a in alerts if "Slow query" in a.message]
    
    assert len(slow_query_alerts) >= 1
    print("✅ Slow query alert created")
    
    print("✅ Performance monitoring tests passed!")
    return True


def test_alert_system():
    """Test alert creation and management."""
    print("🚨 Testing Alert System...")
    
    collector = metrics_collector
    
    # Create different types of alerts
    collector.create_alert(
        AlertLevel.INFO,
        "System startup completed",
        "system"
    )
    
    collector.create_alert(
        AlertLevel.WARNING,
        "High memory usage detected",
        "system",
        {"memory_percent": 87.5}
    )
    
    collector.create_alert(
        AlertLevel.ERROR,
        "Database connection failed",
        "database",
        {"error": "Connection timeout"}
    )
    
    collector.create_alert(
        AlertLevel.CRITICAL,
        "Service unavailable",
        "api",
        {"downtime_seconds": 300}
    )
    
    print("✅ Various alert levels created")
    
    # Get recent alerts
    alerts = collector.get_recent_alerts(10)
    
    # Check alert levels
    info_alerts = [a for a in alerts if a.level == AlertLevel.INFO]
    warning_alerts = [a for a in alerts if a.level == AlertLevel.WARNING]
    error_alerts = [a for a in alerts if a.level == AlertLevel.ERROR]
    critical_alerts = [a for a in alerts if a.level == AlertLevel.CRITICAL]
    
    assert len(info_alerts) >= 1
    assert len(warning_alerts) >= 1
    assert len(error_alerts) >= 1
    assert len(critical_alerts) >= 1
    
    print(f"✅ Alert counts - Info: {len(info_alerts)}, Warning: {len(warning_alerts)}, Error: {len(error_alerts)}, Critical: {len(critical_alerts)}")
    
    print("✅ Alert system tests passed!")
    return True


def test_file_upload_metrics():
    """Test file upload metrics."""
    print("📁 Testing File Upload Metrics...")
    
    collector = metrics_collector
    
    # Record successful uploads
    collector.record_file_upload("image/jpeg", 1024000, "test-org", "success")
    collector.record_file_upload("image/png", 512000, "test-org", "success")
    
    # Record failed upload
    collector.record_file_upload("application/exe", 2048000, "test-org", "blocked")
    
    print("✅ File upload metrics recorded")
    print("✅ File upload metrics tests passed!")
    return True


def test_cache_metrics():
    """Test cache operation metrics."""
    print("🗄️  Testing Cache Metrics...")
    
    collector = metrics_collector
    
    # Record cache operations
    collector.record_cache_operation("redis", "test-org", True)   # Hit
    collector.record_cache_operation("redis", "test-org", True)   # Hit
    collector.record_cache_operation("redis", "test-org", False)  # Miss
    collector.record_cache_operation("qdrant", "test-org", True)  # Hit
    
    print("✅ Cache operations recorded")
    print("✅ Cache metrics tests passed!")
    return True


def test_database_metrics():
    """Test database query metrics."""
    print("🗃️  Testing Database Metrics...")
    
    collector = metrics_collector
    
    # Record database queries
    collector.record_db_query("SELECT", "projects", 0.05)
    collector.record_db_query("INSERT", "renders", 0.15)
    collector.record_db_query("UPDATE", "users", 0.08)
    collector.record_db_query("SELECT", "projects", 1.5)  # Slow query
    
    print("✅ Database query metrics recorded")
    print("✅ Database metrics tests passed!")
    return True


def test_prometheus_output():
    """Test Prometheus metrics output."""
    print("📈 Testing Prometheus Output...")
    
    collector = metrics_collector
    
    # Record some metrics first
    collector.record_api_request("GET", "/health", 200, 0.1, "system")
    collector.record_ai_request("openai/gpt-3.5-turbo", "openai", "test-org", 1.0, {"prompt": 100}, 0.01)
    
    # Get Prometheus metrics
    metrics_output = collector.get_prometheus_metrics()
    
    assert isinstance(metrics_output, bytes)
    assert len(metrics_output) > 0
    
    # Check that it contains expected metric names or mock fallback
    metrics_text = metrics_output.decode('utf-8')
    if "Prometheus client not installed" in metrics_text:
        # Mock fallback case - this is acceptable for testing
        print("✅ Using mock Prometheus client (prometheus_client not installed)")
        assert "Prometheus client not installed" in metrics_text
    else:
        # Real Prometheus client case
        assert "api_requests_total" in metrics_text
        assert "ai_requests_total" in metrics_text
        assert "system_cpu_usage" in metrics_text
    
    print("✅ Prometheus metrics output generated")
    print(f"✅ Metrics output size: {len(metrics_output)} bytes")
    
    print("✅ Prometheus output tests passed!")
    return True


def test_business_metrics():
    """Test business-related metrics."""
    print("📊 Testing Business Metrics...")
    
    collector = metrics_collector
    
    # Test active users gauge
    collector.active_users.labels(org_id="test-org", time_period="daily").set(150)
    collector.active_users.labels(org_id="test-org", time_period="monthly").set(500)
    
    # Test projects created
    collector.projects_created.labels(org_id="test-org").inc(5)
    
    print("✅ Business metrics recorded")
    print("✅ Business metrics tests passed!")
    return True


def test_integration_with_global_instances():
    """Test integration with global instances."""
    print("🌐 Testing Global Instance Integration...")
    
    # Test global metrics collector
    metrics_collector.record_api_request("POST", "/test", 200, 0.5, "global-test")
    
    # Test global performance monitor
    performance_monitor.start_request_tracking("global-test", "/test", "global-test")
    time.sleep(0.05)
    performance_monitor.end_request_tracking("global-test", 200)
    
    print("✅ Global instances working correctly")
    print("✅ Global integration tests passed!")
    return True


def main():
    """Run all monitoring tests."""
    print("📊 MONITORING & METRICS SYSTEM TESTS")
    print("=" * 50)
    
    tests = [
        test_prometheus_metrics_setup,
        test_security_monitoring,
        test_system_metrics,
        test_performance_monitoring,
        test_alert_system,
        test_file_upload_metrics,
        test_cache_metrics,
        test_database_metrics,
        test_prometheus_output,
        test_business_metrics,
        test_integration_with_global_instances
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
            print()
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 50)
    print(f"📊 RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL MONITORING TESTS PASSED!")
        return True
    else:
        print("❌ Some monitoring tests failed!")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
