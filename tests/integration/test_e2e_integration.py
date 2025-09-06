"""Integration tests for E2E components."""

import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
import json
import time
from datetime import datetime, timedelta

# Import the FastAPI app
from api.app.main import app

# Import E2E services for mocking
from api.app.services.e2e_monitoring import E2EMonitoringService
from api.app.services.journey_optimizer import JourneyOptimizer
from api.app.services.error_experience import ErrorExperience
from api.app.services.e2e_performance import E2EPerformanceOptimizer

class TestE2EIntegration:
    """Test suite for E2E component integration."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_e2e_services(self):
        """Mock all E2E services."""
        with patch('api.app.services.e2e_monitoring.E2EMonitoringService') as mock_monitoring, \
             patch('api.app.services.journey_optimizer.JourneyOptimizer') as mock_optimizer, \
             patch('api.app.services.error_experience.ErrorExperience') as mock_error, \
             patch('api.app.services.e2e_performance.E2EPerformanceOptimizer') as mock_perf:
            
            # Setup mock instances
            mock_monitoring_instance = AsyncMock()
            mock_optimizer_instance = AsyncMock()
            mock_error_instance = AsyncMock()
            mock_perf_instance = AsyncMock()
            
            mock_monitoring.return_value = mock_monitoring_instance
            mock_optimizer.return_value = mock_optimizer_instance
            mock_error.return_value = mock_error_instance
            mock_perf.return_value = mock_perf_instance
            
            yield {
                'monitoring': mock_monitoring_instance,
                'optimizer': mock_optimizer_instance,
                'error': mock_error_instance,
                'performance': mock_perf_instance
            }
    
    def test_middleware_integration(self, client):
        """Test that all middleware is properly integrated."""
        response = client.get("/health/status")
        
        # Check that middleware added headers
        assert "X-Request-ID" in response.headers
        assert "X-Processing-Time" in response.headers
        assert "X-API-Version" in response.headers
        
        # Check CORS headers
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Expose-Headers" in response.headers
        
        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        assert "X-XSS-Protection" in response.headers
    
    def test_response_format_consistency(self, client):
        """Test that responses follow consistent format."""
        response = client.get("/health/status")
        data = response.json()
        
        # Check response structure
        assert "status" in data
        assert "meta" in data
        
        # Check meta information
        meta = data["meta"]
        assert "request_id" in meta
        assert "timestamp" in meta
        assert "version" in meta
        assert "processing_time_ms" in meta
    
    def test_error_handling_integration(self, client):
        """Test that error handling works consistently."""
        # Test non-existent endpoint
        response = client.get("/non-existent-endpoint")
        assert response.status_code == 404
        
        data = response.json()
        assert "status" in data
        assert "error" in data
        assert "meta" in data
    
    def test_e2e_health_endpoint(self, client, mock_e2e_services):
        """Test E2E health endpoint."""
        response = client.get("/e2e/health")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] in ["healthy", "degraded"]
        assert "services" in data
        assert "timestamp" in data
        
        services = data["services"]
        assert "monitoring" in services
        assert "optimization" in services
        assert "error_experience" in services
        assert "performance" in services
    
    def test_e2e_status_endpoint(self, client, mock_e2e_services):
        """Test E2E status endpoint."""
        # Setup mock responses
        mock_e2e_services['monitoring'].get_status.return_value = {
            "status": "active",
            "journeys_tracked": 100
        }
        mock_e2e_services['optimizer'].get_status.return_value = {
            "status": "active",
            "optimizations_applied": 25
        }
        mock_e2e_services['error'].get_status.return_value = {
            "status": "active",
            "errors_enhanced": 50
        }
        mock_e2e_services['performance'].get_status.return_value = {
            "status": "active",
            "optimizations_active": 10
        }
        
        response = client.get("/e2e/status")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "data" in data
        assert "timestamp" in data
    
    def test_journey_monitoring_integration(self, client, mock_e2e_services):
        """Test journey monitoring endpoints."""
        journey_id = "test-journey-123"
        
        # Setup mock data
        mock_journey_data = {
            "journey_id": journey_id,
            "user_id": "user-123",
            "start_time": datetime.now().isoformat(),
            "stages": [
                {
                    "stage": "request_received",
                    "timestamp": datetime.now().isoformat(),
                    "duration_ms": 10
                }
            ],
            "status": "completed"
        }
        
        mock_e2e_services['monitoring'].get_journey_details.return_value = mock_journey_data
        
        response = client.get(f"/e2e/monitoring/journey/{journey_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["journey_id"] == journey_id
        
        # Test journey analytics
        mock_analytics = {
            "total_journeys": 100,
            "successful_journeys": 95,
            "average_duration_ms": 1500,
            "error_rate": 0.05
        }
        
        mock_e2e_services['monitoring'].get_journey_analytics.return_value = mock_analytics
        
        response = client.get("/e2e/monitoring/analytics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["total_journeys"] == 100
    
    def test_optimization_integration(self, client, mock_e2e_services):
        """Test optimization endpoints."""
        # Test getting suggestions
        mock_suggestions = [
            {
                "type": "caching",
                "priority": "high",
                "description": "Add caching for frequently accessed data"
            }
        ]
        
        mock_e2e_services['optimizer'].get_optimization_suggestions.return_value = mock_suggestions
        
        response = client.get("/e2e/optimization/suggestions")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert len(data["data"]["suggestions"]) == 1
        
        # Test applying optimization
        optimization_data = {"type": "caching", "target": "user_data"}
        mock_result = {"success": True, "optimization_id": "opt-123"}
        
        mock_e2e_services['optimizer'].apply_optimization.return_value = mock_result
        
        response = client.post("/e2e/optimization/apply", json=optimization_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["success"] is True
    
    def test_error_experience_integration(self, client, mock_e2e_services):
        """Test error experience endpoints."""
        error_code = "VALIDATION_ERROR"
        
        mock_experience = {
            "error_code": error_code,
            "user_message": "Please check your input and try again",
            "suggested_actions": [
                "Verify all required fields are filled",
                "Check data format requirements"
            ],
            "help_links": [
                {"title": "API Documentation", "url": "/docs"}
            ]
        }
        
        mock_e2e_services['error'].get_error_experience.return_value = mock_experience
        
        response = client.get(f"/e2e/errors/experience/{error_code}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["error_code"] == error_code
        
        # Test error analytics
        mock_analytics = {
            "total_errors": 50,
            "error_types": {
                "validation": 30,
                "authentication": 15,
                "rate_limit": 5
            },
            "resolution_rate": 0.95
        }
        
        mock_e2e_services['error'].get_error_analytics.return_value = mock_analytics
        
        response = client.get("/e2e/errors/analytics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["total_errors"] == 50
    
    def test_performance_integration(self, client, mock_e2e_services):
        """Test performance optimization endpoints."""
        # Test getting metrics
        mock_metrics = {
            "avg_response_time": 150,
            "p95_response_time": 300,
            "throughput": 100,
            "error_rate": 0.02,
            "active_optimizations": 5
        }
        
        mock_e2e_services['performance'].get_performance_metrics.return_value = mock_metrics
        
        response = client.get("/e2e/performance/metrics")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["avg_response_time"] == 150
        
        # Test triggering optimization
        mock_result = {"success": True, "improvement": "20% faster response time"}
        
        mock_e2e_services['performance'].optimize_performance.return_value = mock_result
        
        response = client.post("/e2e/performance/optimize?optimization_type=caching")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["success"] is True
        
        # Test dashboard
        mock_dashboard = {
            "performance_score": 85,
            "recent_optimizations": 3,
            "metrics": mock_metrics
        }
        
        mock_e2e_services['performance'].get_dashboard_data.return_value = mock_dashboard
        
        response = client.get("/e2e/performance/dashboard")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["data"]["performance_score"] == 85
    
    def test_rate_limiting_integration(self, client):
        """Test that rate limiting middleware works."""
        # Make multiple rapid requests
        responses = []
        for i in range(5):
            response = client.get("/health/status")
            responses.append(response)
        
        # All should succeed under normal rate limits
        for response in responses:
            assert response.status_code == 200
            assert "X-RateLimit-Limit" in response.headers
            assert "X-RateLimit-Remaining" in response.headers
    
    def test_cors_integration(self, client):
        """Test CORS middleware integration."""
        # Test preflight request
        response = client.options(
            "/health/status",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET"
            }
        )
        
        assert response.status_code == 200
        assert "Access-Control-Allow-Origin" in response.headers
        assert "Access-Control-Allow-Methods" in response.headers
    
    def test_security_headers_integration(self, client):
        """Test security headers middleware."""
        response = client.get("/health/status")
        
        # Check security headers
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert response.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "Content-Security-Policy" in response.headers
    
    def test_end_to_end_request_flow(self, client, mock_e2e_services):
        """Test complete request flow with all E2E components."""
        # Make a request that should trigger all middleware and E2E services
        response = client.get("/health/status")
        
        # Verify response structure
        assert response.status_code == 200
        data = response.json()
        
        # Check standard response format
        assert "status" in data
        assert "meta" in data
        
        # Check middleware headers
        assert "X-Request-ID" in response.headers
        assert "X-Processing-Time" in response.headers
        assert "X-API-Version" in response.headers
        
        # Check security headers
        assert "X-Content-Type-Options" in response.headers
        assert "X-Frame-Options" in response.headers
        
        # Check CORS headers
        assert "Access-Control-Expose-Headers" in response.headers
        
        # Check rate limiting headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
    
    @pytest.mark.asyncio
    async def test_service_initialization_cleanup(self, mock_e2e_services):
        """Test that services are properly initialized and cleaned up."""
        # Verify initialization was called
        mock_e2e_services['monitoring'].initialize.assert_called_once()
        mock_e2e_services['optimizer'].initialize.assert_called_once()
        mock_e2e_services['error'].initialize.assert_called_once()
        mock_e2e_services['performance'].initialize.assert_called_once()
        
        # Test cleanup (would be called during shutdown)
        await mock_e2e_services['monitoring'].cleanup()
        await mock_e2e_services['optimizer'].cleanup()
        await mock_e2e_services['error'].cleanup()
        await mock_e2e_services['performance'].cleanup()
        
        mock_e2e_services['monitoring'].cleanup.assert_called_once()
        mock_e2e_services['optimizer'].cleanup.assert_called_once()
        mock_e2e_services['error'].cleanup.assert_called_once()
        mock_e2e_services['performance'].cleanup.assert_called_once()

if __name__ == "__main__":
    pytest.main([__file__, "-v"])