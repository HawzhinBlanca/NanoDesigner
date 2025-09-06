"""Unit tests for Guardrails validation service."""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch
import pytest
from fastapi import HTTPException

from app.services.guardrails import validate_contract, _load_schema


class TestGuardrailsService:
    """Test cases for Guardrails validation service."""

    def test_load_schema_success(self):
        """Test successful schema loading and caching."""
        # Create a temporary schema file
        schema_data = {
            "type": "object",
            "required": ["test_field"],
            "properties": {
                "test_field": {"type": "string"}
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(schema_data, f)
            temp_file = Path(f.name)
        
        try:
            # Mock the path resolution to point to our temp file
            with patch('app.services.guardrails.Path') as mock_path:
                mock_path_instance = Mock()
                mock_path_instance.resolve.return_value.parents = [Path('/app')]
                mock_path.return_value = mock_path_instance
                
                # Mock the schema path to point to our temp file
                with patch.object(Path, '__truediv__', return_value=temp_file):
                    validator = _load_schema('test_schema.json')
                    
                    # Test that validator is created and cached
                    assert validator is not None
                    
                    # Test caching - second call should return same validator
                    validator2 = _load_schema('test_schema.json')
                    assert validator is validator2
                    
        finally:
            temp_file.unlink()  # Clean up temp file

    def test_validate_contract_success(self):
        """Test successful contract validation."""
        valid_payload = {
            "goal": "Create a banner",
            "ops": ["text_overlay"],
            "safety": {
                "respect_logo_safe_zone": True,
                "palette_only": False
            }
        }
        
        # Mock the schema loading to return a simple validator
        with patch('app.services.guardrails._load_schema') as mock_load:
            mock_validator = Mock()
            mock_validator.iter_errors.return_value = []  # No errors
            mock_load.return_value = mock_validator
            
            # Should not raise any exception
            validate_contract('render_plan.json', valid_payload)
            
            mock_load.assert_called_once_with('render_plan.json')
            mock_validator.iter_errors.assert_called_once_with(valid_payload)

    def test_validate_contract_validation_errors(self):
        """Test contract validation with validation errors."""
        invalid_payload = {
            "goal": "X",  # Too short
            "ops": ["invalid_op"],  # Invalid enum value
            "safety": {}
        }
        
        # Create mock validation errors
        mock_error1 = Mock()
        mock_error1.path = ['goal']
        mock_error1.message = 'String too short'
        
        mock_error2 = Mock()
        mock_error2.path = ['ops', 0]
        mock_error2.message = 'Invalid enum value'
        
        # Mock the schema loading to return a validator with errors
        with patch('app.services.guardrails._load_schema') as mock_load:
            mock_validator = Mock()
            mock_validator.iter_errors.return_value = [mock_error1, mock_error2]
            mock_load.return_value = mock_validator
            
            # Should raise HTTPException with 422 status
            with pytest.raises(HTTPException) as exc_info:
                validate_contract('render_plan.json', invalid_payload)
            
            assert exc_info.value.status_code == 422
            assert 'guardrails' in exc_info.value.detail
            assert len(exc_info.value.detail['guardrails']) == 2
            assert "['goal']: String too short" in exc_info.value.detail['guardrails']
            assert "['ops', 0]: Invalid enum value" in exc_info.value.detail['guardrails']

    def test_validate_contract_empty_payload(self):
        """Test contract validation with empty payload."""
        empty_payload = {}
        
        # Create mock validation error for required fields
        mock_error = Mock()
        mock_error.path = []
        mock_error.message = "'goal' is a required property"
        
        # Mock the schema loading
        with patch('app.services.guardrails._load_schema') as mock_load:
            mock_validator = Mock()
            mock_validator.iter_errors.return_value = [mock_error]
            mock_load.return_value = mock_validator
            
            # Should raise HTTPException
            with pytest.raises(HTTPException) as exc_info:
                validate_contract('canon.json', empty_payload)
            
            assert exc_info.value.status_code == 422
            assert 'guardrails' in exc_info.value.detail

    def test_validate_contract_none_payload(self):
        """Test contract validation with None payload."""
        # Mock the schema loading
        with patch('app.services.guardrails._load_schema') as mock_load:
            mock_validator = Mock()
            mock_validator.iter_errors.return_value = []
            mock_load.return_value = mock_validator
            
            # Should handle None gracefully
            validate_contract('test.json', None)
            
            mock_validator.iter_errors.assert_called_once_with(None)

    def test_schema_cache_behavior(self):
        """Test that schema caching works correctly."""
        with patch('app.services.guardrails.Path') as mock_path, \
             patch('builtins.open'), \
             patch('json.load') as mock_json_load:
            
            # Setup mocks
            mock_path_instance = Mock()
            mock_path_instance.resolve.return_value.parents = [Path('/app')]
            mock_path.return_value = mock_path_instance
            
            mock_json_load.return_value = {
                "type": "object",
                "properties": {"test": {"type": "string"}}
            }
            
            # Clear the cache
            from app.services.guardrails import _SCHEMA_CACHE
            _SCHEMA_CACHE.clear()
            
            # First call should load the schema
            validator1 = _load_schema('test.json')
            
            # Second call should return cached version
            validator2 = _load_schema('test.json')
            
            # Should be the same object (cached)
            assert validator1 is validator2
            
            # JSON load should only be called once (cached)
            assert mock_json_load.call_count == 1

    def test_validate_contract_complex_nested_errors(self):
        """Test validation with complex nested validation errors."""
        # Create nested validation errors
        mock_error1 = Mock()
        mock_error1.path = ['palette_hex', 0]
        mock_error1.message = 'Invalid color format'
        
        mock_error2 = Mock()
        mock_error2.path = ['voice', 'tone']
        mock_error2.message = 'Missing required field'
        
        mock_error3 = Mock()
        mock_error3.path = ['fonts']
        mock_error3.message = 'Array too short'
        
        # Mock the schema loading
        with patch('app.services.guardrails._load_schema') as mock_load:
            mock_validator = Mock()
            mock_validator.iter_errors.return_value = [mock_error1, mock_error2, mock_error3]
            mock_load.return_value = mock_validator
            
            # Should raise HTTPException with detailed errors
            with pytest.raises(HTTPException) as exc_info:
                validate_contract('canon.json', {})
            
            assert exc_info.value.status_code == 422
            errors = exc_info.value.detail['guardrails']
            assert len(errors) == 3
            assert "['palette_hex', 0]: Invalid color format" in errors
            assert "['voice', 'tone']: Missing required field" in errors
            assert "['fonts']: Array too short" in errors