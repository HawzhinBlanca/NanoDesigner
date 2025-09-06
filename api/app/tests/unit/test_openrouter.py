"""Unit tests for OpenRouter service module."""

import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx

from app.services.openrouter import (
    call_openrouter,
    call_openrouter_images,
    call_task,
    _extract_message_text,
    _headers
)
from app.services.langfuse import Trace


class TestOpenRouterService:
    """Test cases for OpenRouter service functions."""

    def test_headers_generation(self):
        """Test that headers are generated correctly."""
        with patch.dict('os.environ', {'OPENROUTER_API_KEY': 'test-key'}):
            headers = _headers()
            
            assert headers['Authorization'] == 'Bearer test-key'
            assert headers['HTTP-Referer'] == 'https://yourapp'
            assert headers['Content-Type'] == 'application/json'
            assert 'X-Title' in headers

    @patch('app.services.openrouter.httpx.Client')
    def test_call_openrouter_success(self, mock_client):
        """Test successful OpenRouter API call."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': 'Test response'}}]
        }
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client.return_value = mock_client_instance

        # Test the call
        result = call_openrouter(
            model="test-model",
            messages=[{"role": "user", "content": "test"}]
        )

        # Assertions
        assert result == {'choices': [{'message': {'content': 'Test response'}}]}
        mock_client_instance.post.assert_called_once()

    @patch('app.services.openrouter.httpx.Client')
    def test_call_openrouter_http_error(self, mock_client):
        """Test OpenRouter API call with HTTP error."""
        # Setup mock to raise HTTP error
        mock_response = Mock()
        mock_response.status_code = 429
        mock_response.text = 'Rate limit exceeded'
        
        mock_client_instance = Mock()
        mock_client_instance.post.side_effect = httpx.HTTPStatusError(
            "Rate limit", request=Mock(), response=mock_response
        )
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client.return_value = mock_client_instance

        # Test the call and expect RuntimeError
        with pytest.raises(RuntimeError, match="OpenRouter error 429"):
            call_openrouter(
                model="test-model",
                messages=[{"role": "user", "content": "test"}]
            )

    @patch('app.services.openrouter.httpx.Client')
    def test_call_openrouter_images_success(self, mock_client):
        """Test successful OpenRouter Images API call."""
        # Setup mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            'data': [{'b64_json': 'base64encodedimage'}]
        }
        mock_client_instance = Mock()
        mock_client_instance.post.return_value = mock_response
        mock_client_instance.__enter__.return_value = mock_client_instance
        mock_client_instance.__exit__.return_value = None
        mock_client.return_value = mock_client_instance

        # Test the call
        result = call_openrouter_images(
            model="gemini-2.5-flash-image",
            prompt="Generate an image",
            n=1,
            size="1024x1024"
        )

        # Assertions
        assert result == {'data': [{'b64_json': 'base64encodedimage'}]}
        mock_client_instance.post.assert_called_once()

    def test_extract_message_text_string_content(self):
        """Test extracting text from string content."""
        response = {
            'choices': [{'message': {'content': 'Simple text response'}}]
        }
        
        result = _extract_message_text(response)
        assert result == 'Simple text response'

    def test_extract_message_text_list_content(self):
        """Test extracting text from list content."""
        response = {
            'choices': [
                {
                    'message': {
                        'content': [
                            {'text': 'First part'},
                            {'text': 'Second part'},
                            {'type': 'image'}  # Non-text content
                        ]
                    }
                }
            ]
        }
        
        result = _extract_message_text(response)
        assert result == 'First part\nSecond part'

    def test_extract_message_text_empty_response(self):
        """Test extracting text from empty response."""
        response = {'choices': []}
        
        result = _extract_message_text(response)
        assert result == ''

    @patch('app.services.openrouter.load_policy')
    @patch('app.services.openrouter.call_openrouter')
    def test_call_task_success(self, mock_call_openrouter, mock_load_policy):
        """Test successful task call with policy routing."""
        # Setup mock policy
        mock_policy = Mock()
        mock_policy.model_for.return_value = 'test-model'
        mock_policy.fallbacks_for.return_value = ['fallback-model']
        mock_policy.timeout_ms_for.return_value = 30000
        mock_load_policy.return_value = mock_policy

        # Setup mock response
        mock_call_openrouter.return_value = {
            'choices': [{'message': {'content': 'Task response'}}]
        }

        # Test the call
        result = call_task(
            task='planner',
            messages=[{'role': 'user', 'content': 'test'}]
        )

        # Assertions
        assert result == {'choices': [{'message': {'content': 'Task response'}}]}
        mock_call_openrouter.assert_called_once()

    @patch('app.services.openrouter.load_policy')
    @patch('app.services.openrouter.call_openrouter')
    def test_call_task_with_fallback(self, mock_call_openrouter, mock_load_policy):
        """Test task call that uses fallback model."""
        # Setup mock policy
        mock_policy = Mock()
        mock_policy.model_for.return_value = 'primary-model'
        mock_policy.fallbacks_for.return_value = ['fallback-model']
        mock_policy.timeout_ms_for.return_value = 30000
        mock_load_policy.return_value = mock_policy

        # Setup mock to fail on first call, succeed on second
        mock_call_openrouter.side_effect = [
            Exception("Primary model failed"),
            {'choices': [{'message': {'content': 'Fallback response'}}]}
        ]

        # Test the call
        result = call_task(
            task='planner',
            messages=[{'role': 'user', 'content': 'test'}]
        )

        # Assertions
        assert result == {'choices': [{'message': {'content': 'Fallback response'}}]}
        assert mock_call_openrouter.call_count == 2

    @patch('app.services.openrouter.load_policy')
    @patch('app.services.openrouter.call_openrouter')
    def test_call_task_with_trace(self, mock_call_openrouter, mock_load_policy):
        """Test task call with tracing enabled."""
        # Setup mock policy
        mock_policy = Mock()
        mock_policy.model_for.return_value = 'test-model'
        mock_policy.fallbacks_for.return_value = []
        mock_policy.timeout_ms_for.return_value = 30000
        mock_load_policy.return_value = mock_policy

        # Setup mock response
        mock_call_openrouter.return_value = {
            'choices': [{'message': {'content': 'Traced response'}}]
        }

        # Setup mock trace
        mock_trace = Mock()
        mock_span = Mock()
        mock_trace.span.return_value = mock_span
        mock_span.__enter__.return_value = mock_span
        mock_span.__exit__.return_value = None

        # Test the call
        result = call_task(
            task='planner',
            messages=[{'role': 'user', 'content': 'test'}],
            trace=mock_trace
        )

        # Assertions
        assert result == {'choices': [{'message': {'content': 'Traced response'}}]}
        mock_trace.span.assert_called_once_with('openrouter:planner', {'model': 'test-model'})