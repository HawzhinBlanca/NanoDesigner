"""Unit tests for Redis caching service."""

import json
from unittest.mock import Mock, patch
import pytest

from app.services.redis import (
    cache_get_set,
    sha1key,
    get_redis_client,
    publish_job_update,
    get_job_status,
    set_job_status
)


class TestRedisService:
    """Test cases for Redis caching service."""

    def test_sha1key_generation(self):
        """Test SHA1 key generation with various inputs."""
        # Test basic key generation
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
    def test_get_redis_client_success(self, mock_redis_class):
        """Test successful Redis client creation."""
        mock_client = Mock()
        mock_redis_class.from_url.return_value = mock_client
        
        with patch('app.services.redis.settings') as mock_settings:
            mock_settings.redis_url = "redis://localhost:6379/0"
            
            client = get_redis_client()
            
            assert client == mock_client
            mock_redis_class.from_url.assert_called_once_with(
                "redis://localhost:6379/0", 
                decode_responses=True
            )

    def test_cache_get_set_cache_hit(self):
        """Test cache_get_set when value exists in cache."""
        mock_client = Mock()
        mock_client.get.return_value = b'cached_value'
        
        factory_function = Mock()
        factory_function.return_value = 'new_value'
        
        result = cache_get_set(mock_client, 'test_key', factory_function, ttl=3600)
        
        # Should return cached value
        assert result == b'cached_value'
        
        # Should not call factory function
        factory_function.assert_not_called()
        
        # Should not set new value
        mock_client.setex.assert_not_called()

    def test_cache_get_set_cache_miss(self):
        """Test cache_get_set when value doesn't exist in cache."""
        mock_client = Mock()
        mock_client.get.return_value = None  # Cache miss
        
        factory_function = Mock()
        factory_function.return_value = b'new_value'
        
        result = cache_get_set(mock_client, 'test_key', factory_function, ttl=3600)
        
        # Should return factory result
        assert result == b'new_value'
        
        # Should call factory function
        factory_function.assert_called_once()
        
        # Should set new value in cache
        mock_client.setex.assert_called_once_with('test_key', 3600, b'new_value')

    def test_cache_get_set_default_ttl(self):
        """Test cache_get_set with default TTL."""
        mock_client = Mock()
        mock_client.get.return_value = None
        
        factory_function = Mock()
        factory_function.return_value = 'value'
        
        cache_get_set(mock_client, 'key', factory_function)
        
        # Should use default TTL of 86400
        mock_client.setex.assert_called_once_with('key', 86400, 'value')

    def test_cache_get_set_string_key_conversion(self):
        """Test cache_get_set with callable key."""
        mock_client = Mock()
        mock_client.get.return_value = None
        
        # Test with string key
        key_func = lambda: 'computed_key'
        factory_func = Mock()
        factory_func.return_value = 'value'
        
        result = cache_get_set(mock_client, key_func, factory_func)
        
        # Should call key function and use result
        mock_client.get.assert_called_once_with('computed_key')

    @patch('app.services.redis.get_redis_client')
    def test_publish_job_update(self, mock_get_client):
        """Test publishing job status updates."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        update_data = {
            'status': 'in_progress',
            'progress': 50,
            'message': 'Processing...'
        }
        
        publish_job_update('job123', update_data)
        
        # Should publish to correct channel
        expected_channel = 'job:job123'
        expected_message = json.dumps(update_data)
        mock_client.publish.assert_called_once_with(expected_channel, expected_message)

    @patch('app.services.redis.get_redis_client')
    def test_get_job_status(self, mock_get_client):
        """Test retrieving job status."""
        mock_client = Mock()
        mock_client.hgetall.return_value = {
            'status': 'completed',
            'result_url': 'https://example.com/result.png'
        }
        mock_get_client.return_value = mock_client
        
        status = get_job_status('job123')
        
        # Should query correct key
        mock_client.hgetall.assert_called_once_with('job:job123')
        assert status == {
            'status': 'completed',
            'result_url': 'https://example.com/result.png'
        }

    @patch('app.services.redis.get_redis_client')
    def test_set_job_status(self, mock_get_client):
        """Test setting job status."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        status_data = {
            'status': 'in_progress',
            'started_at': '2024-01-01T00:00:00Z'
        }
        
        set_job_status('job123', status_data)
        
        # Should set hash with correct key and data
        mock_client.hset.assert_called_once_with('job:job123', mapping=status_data)

    @patch('app.services.redis.get_redis_client')
    def test_set_job_status_with_expiry(self, mock_get_client):
        """Test setting job status with expiry."""
        mock_client = Mock()
        mock_get_client.return_value = mock_client
        
        status_data = {'status': 'completed'}
        
        set_job_status('job123', status_data, ttl=3600)
        
        # Should set hash and expiry
        mock_client.hset.assert_called_once_with('job:job123', mapping=status_data)
        mock_client.expire.assert_called_once_with('job:job123', 3600)

    def test_cache_get_set_factory_exception(self):
        """Test cache_get_set when factory function raises exception."""
        mock_client = Mock()
        mock_client.get.return_value = None  # Cache miss
        
        def failing_factory():
            raise ValueError("Factory failed")
        
        with pytest.raises(ValueError, match="Factory failed"):
            cache_get_set(mock_client, 'test_key', failing_factory)
        
        # Should not set value in cache when factory fails
        mock_client.setex.assert_not_called()

    @patch('app.services.redis.get_redis_client')
    def test_redis_connection_error(self, mock_get_client):
        """Test handling Redis connection errors."""
        mock_client = Mock()
        mock_client.get.side_effect = ConnectionError("Redis unavailable")
        mock_get_client.return_value = mock_client
        
        # Should propagate Redis connection errors
        with pytest.raises(ConnectionError):
            cache_get_set(mock_client, 'key', lambda: 'value')

    def test_cache_get_set_bytes_vs_string(self):
        """Test cache_get_set handling of bytes vs string values."""
        mock_client = Mock()
        mock_client.get.return_value = None
        
        # Test with bytes factory
        bytes_factory = Mock()
        bytes_factory.return_value = b'bytes_value'
        
        result = cache_get_set(mock_client, 'key1', bytes_factory)
        assert result == b'bytes_value'
        
        # Test with string factory
        string_factory = Mock()
        string_factory.return_value = 'string_value'
        
        mock_client.get.return_value = None  # Reset for second test
        result = cache_get_set(mock_client, 'key2', string_factory)
        assert result == 'string_value'