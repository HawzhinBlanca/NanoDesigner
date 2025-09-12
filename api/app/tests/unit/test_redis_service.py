"""Unit tests for Redis caching service."""

import json
from unittest.mock import Mock, patch, ANY
import pytest

from app.services.redis import (
    cache_get_set,
    sha1key,
    get_client
)


class TestRedisService:
    """Test cases for Redis caching service."""

    def test_sha1key_generation(self):
        """Test SHA1 key generation consistency."""
        key1 = sha1key("test", "value1", "value2")
        key2 = sha1key("test", "value1", "value2")
        key3 = sha1key("test", "value1", "different")
        
        # Same inputs should produce same key
        assert key1 == key2
        
        # Different inputs should produce different keys
        assert key1 != key3
        
        # Key should be a reasonable length (SHA1 hex = 40 chars)
        assert len(key1) == 40
        assert all(c in '0123456789abcdef' for c in key1)

    def test_sha1key_with_none_values(self):
        """Test SHA1 key generation with None values."""
        key = sha1key("test", None, "value", None)
        
        # Should handle None values gracefully
        assert isinstance(key, str)
        assert len(key) == 40

    def test_sha1key_empty_inputs(self):
        """Test SHA1 key generation with empty inputs."""
        key1 = sha1key()  # No arguments
        key2 = sha1key("")  # Empty string
        
        assert isinstance(key1, str)
        assert isinstance(key2, str)
        assert key1 != key2

    @patch('app.services.redis.redis.Redis')
    @patch('app.services.redis.ConnectionPool.from_url')
    def test_get_client_success(self, mock_pool_from_url, mock_redis):
        """Test successful Redis client creation."""
        mock_pool = Mock()
        mock_client = Mock()
        mock_pool_from_url.return_value = mock_pool
        mock_redis.return_value = mock_client
        
        with patch('app.services.redis.settings') as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"
            
            # Clear the global pool to test initialization
            import app.services.redis
            app.services.redis._pool = None
            
            client = get_client()
            
            assert client == mock_client
            mock_pool_from_url.assert_called_once_with(
                "redis://localhost:6379/0",
                max_connections=100,
                retry_on_timeout=True,
                retry_on_error=ANY,
                health_check_interval=30,
                decode_responses=False,
                socket_connect_timeout=5,
                socket_timeout=5,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            mock_redis.assert_called_once_with(connection_pool=mock_pool)

    def test_cache_get_set_cache_hit(self):
        """Test cache_get_set when value exists in cache."""
        mock_client = Mock()
        cached_value = b'{"cached": "data"}'
        mock_client.get.return_value = cached_value
        
        factory_called = False
        def test_factory():
            nonlocal factory_called
            factory_called = True
            return b'{"new": "data"}'
        
        with patch('app.services.redis.get_client', return_value=mock_client):
            result = cache_get_set("test_key", test_factory, ttl=3600)
            
            # Should return cached value
            assert result == cached_value
            
            # Factory should not be called
            assert not factory_called
            
            # Redis get should be called
            mock_client.get.assert_called_once_with("test_key")
            
            # Redis setex should not be called
            mock_client.setex.assert_not_called()

    def test_cache_get_set_cache_miss(self):
        """Test cache_get_set when value doesn't exist in cache."""
        mock_client = Mock()
        mock_client.get.return_value = None  # Cache miss
        
        new_value = b'{"new": "data"}'
        def test_factory():
            return new_value
        
        with patch('app.services.redis.get_client', return_value=mock_client):
            result = cache_get_set("test_key", test_factory, ttl=3600)
            
            # Should return factory value
            assert result == new_value
            
            # Redis get should be called
            mock_client.get.assert_called_once_with("test_key")
            
            # Redis setex should be called with factory result
            mock_client.setex.assert_called_once_with("test_key", 3600, new_value)

    def test_cache_get_set_default_ttl(self):
        """Test cache_get_set uses default TTL when not specified."""
        mock_client = Mock()
        mock_client.get.return_value = None
        
        new_value = b'{"test": "data"}'
        def test_factory():
            return new_value
        
        with patch('app.services.redis.get_client', return_value=mock_client):
            cache_get_set("test_key", test_factory)  # No TTL specified
            
            # Should use default TTL of 86400 (24 hours)
            mock_client.setex.assert_called_once_with("test_key", 86400, new_value)

    def test_cache_get_set_factory_exception(self):
        """Test cache_get_set handles factory exceptions."""
        mock_client = Mock()
        mock_client.get.return_value = None
        
        def failing_factory():
            raise ValueError("Factory failed")
        
        with patch('app.services.redis.get_client', return_value=mock_client):
            with pytest.raises(ValueError, match="Factory failed"):
                cache_get_set("test_key", failing_factory)
            
            # Redis get should be called
            mock_client.get.assert_called_once_with("test_key")
            
            # Redis setex should not be called due to exception
            mock_client.setex.assert_not_called()

    def test_cache_get_set_redis_exception(self):
        """Test cache_get_set handles Redis exceptions gracefully."""
        mock_client = Mock()
        mock_client.get.side_effect = Exception("Redis connection failed")
        
        new_value = b'{"fallback": "data"}'
        def test_factory():
            return new_value
        
        with patch('app.services.redis.get_client', return_value=mock_client):
            # Should propagate Redis exceptions
            with pytest.raises(Exception, match="Redis connection failed"):
                cache_get_set("test_key", test_factory)

    def test_multiple_cache_operations(self):
        """Test multiple cache operations with different keys."""
        mock_client = Mock()
        
        # Setup different responses for different keys
        def get_side_effect(key):
            if key == "existing_key":
                return b'{"existing": "value"}'
            return None
        
        mock_client.get.side_effect = get_side_effect
        
        def factory1():
            return b'{"new1": "value"}'
        
        def factory2():
            return b'{"new2": "value"}'
        
        with patch('app.services.redis.get_client', return_value=mock_client):
            # Test cache hit
            result1 = cache_get_set("existing_key", factory1)
            assert result1 == b'{"existing": "value"}'
            
            # Test cache miss
            result2 = cache_get_set("new_key", factory2)
            assert result2 == b'{"new2": "value"}'
            
            # Verify calls
            assert mock_client.get.call_count == 2
            mock_client.setex.assert_called_once_with("new_key", 86400, b'{"new2": "value"}')