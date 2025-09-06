"""Enhanced error experience service.

This module provides intelligent error handling, user-friendly error messages,
error recovery suggestions, and comprehensive error tracking for better UX.
"""

from __future__ import annotations

import re
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import logging

from ..models.exceptions import SGDBaseException
from ..models.responses import (
    create_error_response,
    create_validation_error_response,
    ErrorDetail
)
from .redis import get_client as get_redis_client
from .e2e_monitoring import monitoring_service, MetricType

logger = logging.getLogger(__name__)

class ErrorSeverity(str, Enum):
    """Error severity levels for better user experience."""
    LOW = "low"          # Minor issues, user can continue
    MEDIUM = "medium"    # Significant issues, workarounds available  
    HIGH = "high"        # Major issues, user action required
    CRITICAL = "critical" # System issues, immediate attention needed

class ErrorCategory(str, Enum):
    """Categories of errors for better organization."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    VALIDATION = "validation"
    RATE_LIMITING = "rate_limiting"
    AI_SERVICE = "ai_service"
    STORAGE = "storage"
    NETWORK = "network"
    SYSTEM = "system"
    BUSINESS_LOGIC = "business_logic"
    USER_INPUT = "user_input"

@dataclass
class ErrorContext:
    """Context information for error analysis."""
    user_id: Optional[str]
    project_id: Optional[str]
    journey_id: Optional[str]
    endpoint: str
    request_method: str
    user_agent: Optional[str]
    ip_address: Optional[str]
    timestamp: datetime
    metadata: Dict[str, Any] = None

@dataclass
class ErrorSolution:
    """Suggested solution for an error."""
    title: str
    description: str
    action_steps: List[str]
    helpful_links: List[Dict[str, str]] = None
    estimated_fix_time: Optional[str] = None
    success_probability: float = 0.5  # 0-1 probability this will work
    
@dataclass
class EnhancedError:
    """Enhanced error with user-friendly information."""
    original_error: Exception
    error_code: str
    user_message: str
    technical_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    solutions: List[ErrorSolution]
    context: ErrorContext
    correlation_id: str
    similar_errors_count: int = 0
    metadata: Dict[str, Any] = None

class ErrorExperienceService:
    """Service for enhancing error user experience."""
    
    def __init__(self):
        self.error_patterns = self._load_error_patterns()
        self.solution_templates = self._load_solution_templates()
        
    def _load_error_patterns(self) -> Dict[str, Dict[str, Any]]:
        """Load error patterns for classification and messaging."""
        
        return {
            "auth_token_expired": {
                "pattern": r"token.*expired|jwt.*expired|authentication.*expired",
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "Your session has expired. Please sign in again.",
                "solutions": [
                    {
                        "title": "Sign in again",
                        "description": "Refresh your authentication token by signing in",
                        "action_steps": [
                            "Click the 'Sign In' button",
                            "Enter your credentials",
                            "Retry your previous action"
                        ],
                        "estimated_fix_time": "1 minute",
                        "success_probability": 0.95
                    }
                ]
            },
            
            "auth_token_invalid": {
                "pattern": r"invalid.*token|token.*invalid|unauthorized|401",
                "category": ErrorCategory.AUTHENTICATION,
                "severity": ErrorSeverity.HIGH,
                "user_message": "Authentication failed. Please check your credentials.",
                "solutions": [
                    {
                        "title": "Verify API credentials",
                        "description": "Check that your API key or token is correct",
                        "action_steps": [
                            "Verify your API key in settings",
                            "Check for typos in the token",
                            "Ensure the token has proper permissions"
                        ],
                        "estimated_fix_time": "2 minutes",
                        "success_probability": 0.8
                    }
                ]
            },
            
            "rate_limit_exceeded": {
                "pattern": r"rate.*limit|too.*many.*requests|429",
                "category": ErrorCategory.RATE_LIMITING,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "You're making requests too quickly. Please wait a moment and try again.",
                "solutions": [
                    {
                        "title": "Wait and retry",
                        "description": "Wait for the rate limit window to reset",
                        "action_steps": [
                            "Wait 60 seconds before retrying",
                            "Reduce the frequency of your requests",
                            "Consider upgrading your plan for higher limits"
                        ],
                        "estimated_fix_time": "1-2 minutes",
                        "success_probability": 0.9
                    }
                ]
            },
            
            "ai_service_unavailable": {
                "pattern": r"openrouter.*unavailable|ai.*service.*down|model.*unavailable|502|503",
                "category": ErrorCategory.AI_SERVICE,
                "severity": ErrorSeverity.HIGH,
                "user_message": "AI service is temporarily unavailable. We're working to restore it.",
                "solutions": [
                    {
                        "title": "Try again in a few minutes",
                        "description": "The AI service may be experiencing high load",
                        "action_steps": [
                            "Wait 2-3 minutes before retrying",
                            "Try using a simpler prompt",
                            "Check our status page for updates"
                        ],
                        "helpful_links": [
                            {"title": "Status Page", "url": "https://status.example.com"}
                        ],
                        "estimated_fix_time": "5-15 minutes",
                        "success_probability": 0.7
                    }
                ]
            },
            
            "validation_error": {
                "pattern": r"validation.*failed|invalid.*input|422|bad.*request",
                "category": ErrorCategory.VALIDATION,
                "severity": ErrorSeverity.LOW,
                "user_message": "Some information in your request needs to be corrected.",
                "solutions": [
                    {
                        "title": "Check your input",
                        "description": "Review and correct the highlighted fields",
                        "action_steps": [
                            "Review the error details below",
                            "Correct any highlighted fields",
                            "Ensure all required fields are filled",
                            "Submit your request again"
                        ],
                        "estimated_fix_time": "1-3 minutes",
                        "success_probability": 0.85
                    }
                ]
            },
            
            "storage_error": {
                "pattern": r"storage.*failed|upload.*failed|s3.*error|file.*error",
                "category": ErrorCategory.STORAGE,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "There was a problem saving your files. Please try again.",
                "solutions": [
                    {
                        "title": "Retry the upload",
                        "description": "The storage service may be temporarily busy",
                        "action_steps": [
                            "Wait a moment and try again",
                            "Check your internet connection",
                            "Ensure your files aren't too large",
                            "Contact support if the problem persists"
                        ],
                        "estimated_fix_time": "2-5 minutes",
                        "success_probability": 0.75
                    }
                ]
            },
            
            "network_timeout": {
                "pattern": r"timeout|connection.*failed|network.*error",
                "category": ErrorCategory.NETWORK,
                "severity": ErrorSeverity.MEDIUM,
                "user_message": "Request timed out. Your internet connection may be slow.",
                "solutions": [
                    {
                        "title": "Check connection and retry",
                        "description": "Ensure you have a stable internet connection",
                        "action_steps": [
                            "Check your internet connection",
                            "Try again with a simpler request",
                            "Wait a moment before retrying",
                            "Switch to a different network if possible"
                        ],
                        "estimated_fix_time": "2-5 minutes",
                        "success_probability": 0.7
                    }
                ]
            },
            
            "content_policy_violation": {
                "pattern": r"content.*policy|banned.*term|inappropriate.*content",
                "category": ErrorCategory.USER_INPUT,
                "severity": ErrorSeverity.LOW,
                "user_message": "Your content doesn't meet our community guidelines.",
                "solutions": [
                    {
                        "title": "Modify your content",
                        "description": "Remove or replace any inappropriate content",
                        "action_steps": [
                            "Review our content guidelines",
                            "Remove any flagged terms or concepts",
                            "Use more neutral language",
                            "Try submitting again"
                        ],
                        "helpful_links": [
                            {"title": "Content Guidelines", "url": "https://example.com/guidelines"}
                        ],
                        "estimated_fix_time": "2-3 minutes",
                        "success_probability": 0.9
                    }
                ]
            },
            
            "quota_exceeded": {
                "pattern": r"quota.*exceeded|limit.*reached|usage.*limit",
                "category": ErrorCategory.RATE_LIMITING,
                "severity": ErrorSeverity.HIGH,
                "user_message": "You've reached your usage limit for this period.",
                "solutions": [
                    {
                        "title": "Upgrade your plan",
                        "description": "Increase your usage limits with a higher tier plan",
                        "action_steps": [
                            "Go to your account settings",
                            "View available plans",
                            "Upgrade to a higher tier",
                            "Or wait until your quota resets"
                        ],
                        "helpful_links": [
                            {"title": "Upgrade Plan", "url": "https://example.com/pricing"}
                        ],
                        "estimated_fix_time": "5 minutes or next billing cycle",
                        "success_probability": 0.95
                    }
                ]
            }
        }
    
    def _load_solution_templates(self) -> Dict[str, List[ErrorSolution]]:
        """Load reusable solution templates."""
        
        return {
            "generic_retry": [
                ErrorSolution(
                    title="Try again",
                    description="Wait a moment and retry your request",
                    action_steps=[
                        "Wait 30 seconds",
                        "Retry your request",
                        "Contact support if the problem persists"
                    ],
                    estimated_fix_time="1 minute",
                    success_probability=0.6
                )
            ],
            
            "contact_support": [
                ErrorSolution(
                    title="Contact support",
                    description="Get help from our support team",
                    action_steps=[
                        "Copy the error details below",
                        "Visit our support page",
                        "Submit a support ticket with the error information"
                    ],
                    helpful_links=[
                        {"title": "Support Center", "url": "https://example.com/support"}
                    ],
                    estimated_fix_time="1-24 hours",
                    success_probability=0.95
                )
            ],
            
            "check_documentation": [
                ErrorSolution(
                    title="Check documentation", 
                    description="Review our API documentation for guidance",
                    action_steps=[
                        "Visit our API documentation",
                        "Review the relevant endpoint documentation",
                        "Check the example requests and responses",
                        "Adjust your request accordingly"
                    ],
                    helpful_links=[
                        {"title": "API Documentation", "url": "https://example.com/docs"}
                    ],
                    estimated_fix_time="5-10 minutes",
                    success_probability=0.8
                )
            ]
        }
    
    async def enhance_error(
        self,
        error: Exception,
        context: ErrorContext
    ) -> EnhancedError:
        """Enhance an error with user-friendly information."""
        
        # Generate correlation ID for tracking
        correlation_id = f"err_{int(datetime.utcnow().timestamp())}_{hash(str(error)) % 10000:04d}"
        
        # Classify the error
        error_code, category, severity = await self._classify_error(error)
        
        # Generate user-friendly messages
        user_message, technical_message = await self._generate_messages(error, error_code)
        
        # Find solutions
        solutions = await self._find_solutions(error, error_code, context)
        
        # Check for similar errors
        similar_count = await self._count_similar_errors(error_code, context)
        
        enhanced_error = EnhancedError(
            original_error=error,
            error_code=error_code,
            user_message=user_message,
            technical_message=technical_message,
            severity=severity,
            category=category,
            solutions=solutions,
            context=context,
            correlation_id=correlation_id,
            similar_errors_count=similar_count,
            metadata={
                "enhanced_at": datetime.utcnow().isoformat(),
                "pattern_matched": self._get_matching_pattern(error),
                "user_impact": self._assess_user_impact(severity, category)
            }
        )
        
        # Store for analytics
        await self._store_error_for_analytics(enhanced_error)
        
        # Record metrics
        await monitoring_service.record_metric(
            "error.enhanced",
            1,
            MetricType.COUNTER,
            {
                "error_code": error_code,
                "category": category.value,
                "severity": severity.value,
                "endpoint": context.endpoint
            }
        )
        
        logger.info(
            f"Enhanced error {correlation_id}",
            extra={
                "correlation_id": correlation_id,
                "error_code": error_code,
                "category": category.value,
                "severity": severity.value,
                "user_id": context.user_id,
                "endpoint": context.endpoint
            }
        )
        
        return enhanced_error
    
    async def _classify_error(self, error: Exception) -> Tuple[str, ErrorCategory, ErrorSeverity]:
        """Classify error into code, category, and severity."""
        
        error_text = str(error).lower()
        error_type = type(error).__name__
        
        # Check against known patterns
        for pattern_name, pattern_info in self.error_patterns.items():
            if re.search(pattern_info["pattern"], error_text):
                return (
                    pattern_name.upper(),
                    pattern_info["category"],
                    pattern_info["severity"]
                )
        
        # Classify by exception type
        if "AuthenticationError" in error_type or "401" in error_text:
            return "AUTH_ERROR", ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH
        elif "ValidationError" in error_type or "422" in error_text:
            return "VALIDATION_ERROR", ErrorCategory.VALIDATION, ErrorSeverity.LOW
        elif "RateLimitError" in error_type or "429" in error_text:
            return "RATE_LIMIT", ErrorCategory.RATE_LIMITING, ErrorSeverity.MEDIUM
        elif "TimeoutError" in error_type or "timeout" in error_text:
            return "TIMEOUT_ERROR", ErrorCategory.NETWORK, ErrorSeverity.MEDIUM
        elif "ConnectionError" in error_type or "connection" in error_text:
            return "CONNECTION_ERROR", ErrorCategory.NETWORK, ErrorSeverity.HIGH
        
        # Default classification
        if "5" in error_text[:10]:  # 5xx errors
            return "SERVER_ERROR", ErrorCategory.SYSTEM, ErrorSeverity.CRITICAL
        elif "4" in error_text[:10]:  # 4xx errors
            return "CLIENT_ERROR", ErrorCategory.USER_INPUT, ErrorSeverity.LOW
        
        return "UNKNOWN_ERROR", ErrorCategory.SYSTEM, ErrorSeverity.MEDIUM
    
    async def _generate_messages(
        self, 
        error: Exception, 
        error_code: str
    ) -> Tuple[str, str]:
        """Generate user-friendly and technical messages."""
        
        # Try to find predefined message
        error_text = str(error).lower()
        for pattern_name, pattern_info in self.error_patterns.items():
            if pattern_name.upper() == error_code:
                user_msg = pattern_info["user_message"]
                tech_msg = f"{pattern_info['category'].value.title()} Error: {str(error)}"
                return user_msg, tech_msg
        
        # Generate contextual messages based on error code
        if "AUTH" in error_code:
            user_msg = "Authentication failed. Please check your credentials and try again."
        elif "VALIDATION" in error_code:
            user_msg = "Some information in your request is incorrect. Please review and try again."
        elif "RATE_LIMIT" in error_code:
            user_msg = "You're making requests too quickly. Please wait and try again."
        elif "TIMEOUT" in error_code:
            user_msg = "The request took too long to complete. Please try again."
        elif "SERVER" in error_code:
            user_msg = "We're experiencing technical difficulties. Please try again in a few minutes."
        else:
            user_msg = "Something went wrong. Please try again or contact support if the problem persists."
        
        tech_msg = f"{error_code}: {str(error)}"
        
        return user_msg, tech_msg
    
    async def _find_solutions(
        self,
        error: Exception,
        error_code: str,
        context: ErrorContext
    ) -> List[ErrorSolution]:
        """Find appropriate solutions for the error."""
        
        solutions = []
        
        # Check for predefined solutions
        error_text = str(error).lower()
        for pattern_name, pattern_info in self.error_patterns.items():
            if pattern_name.upper() == error_code and "solutions" in pattern_info:
                solutions.extend([
                    ErrorSolution(**sol) for sol in pattern_info["solutions"]
                ])
        
        # Add contextual solutions
        if not solutions:
            if "AUTH" in error_code:
                solutions.extend(self.solution_templates["generic_retry"])
            elif "VALIDATION" in error_code:
                solutions.extend(self.solution_templates["check_documentation"])
            elif "RATE_LIMIT" in error_code:
                solutions.append(ErrorSolution(
                    title="Wait and retry",
                    description="Rate limits reset automatically",
                    action_steps=[
                        "Wait 60 seconds",
                        "Retry your request",
                        "Consider reducing request frequency"
                    ],
                    estimated_fix_time="1-2 minutes",
                    success_probability=0.9
                ))
            else:
                solutions.extend(self.solution_templates["generic_retry"])
        
        # Always add support option for high severity errors
        if any("HIGH" in error_code or "CRITICAL" in error_code for _ in [1]):
            solutions.extend(self.solution_templates["contact_support"])
        
        # Customize solutions based on user context
        solutions = await self._customize_solutions(solutions, context)
        
        return solutions[:3]  # Limit to top 3 solutions
    
    async def _customize_solutions(
        self,
        solutions: List[ErrorSolution],
        context: ErrorContext
    ) -> List[ErrorSolution]:
        """Customize solutions based on user context."""
        
        customized = []
        
        for solution in solutions:
            # Create a copy to avoid modifying original
            custom_solution = ErrorSolution(
                title=solution.title,
                description=solution.description,
                action_steps=solution.action_steps.copy(),
                helpful_links=solution.helpful_links.copy() if solution.helpful_links else None,
                estimated_fix_time=solution.estimated_fix_time,
                success_probability=solution.success_probability
            )
            
            # Add context-specific steps
            if context.user_id and "sign in" in solution.description.lower():
                custom_solution.action_steps.insert(0, f"User ID: {context.user_id}")
            
            if context.project_id and "project" in solution.description.lower():
                custom_solution.action_steps.append(f"Project ID: {context.project_id}")
            
            # Add endpoint-specific guidance
            if context.endpoint == "/render" and "retry" in solution.title.lower():
                custom_solution.action_steps.append("Consider using simpler prompts")
                custom_solution.action_steps.append("Try reducing output count")
            
            customized.append(custom_solution)
        
        return customized
    
    async def _count_similar_errors(
        self,
        error_code: str,
        context: ErrorContext
    ) -> int:
        """Count similar errors in recent time period."""
        
        try:
            redis_client = get_redis_client()
            
            # Count errors with same code for this user in last hour
            user_key = f"user_errors:{context.user_id}:{error_code}"
            count = await redis_client.get(user_key)
            
            if count:
                return int(count)
            
        except Exception as e:
            logger.warning(f"Failed to count similar errors: {e}")
        
        return 0
    
    def _get_matching_pattern(self, error: Exception) -> Optional[str]:
        """Get the pattern name that matched this error."""
        
        error_text = str(error).lower()
        
        for pattern_name, pattern_info in self.error_patterns.items():
            if re.search(pattern_info["pattern"], error_text):
                return pattern_name
        
        return None
    
    def _assess_user_impact(self, severity: ErrorSeverity, category: ErrorCategory) -> str:
        """Assess the impact on user experience."""
        
        if severity == ErrorSeverity.CRITICAL:
            return "high_impact"
        elif severity == ErrorSeverity.HIGH:
            if category in [ErrorCategory.AI_SERVICE, ErrorCategory.AUTHENTICATION]:
                return "high_impact"
            return "medium_impact"
        elif severity == ErrorSeverity.MEDIUM:
            return "medium_impact"
        else:
            return "low_impact"
    
    async def _store_error_for_analytics(self, enhanced_error: EnhancedError):
        """Store enhanced error for analytics and tracking."""
        
        try:
            redis_client = get_redis_client()
            
            # Store error details
            error_data = {
                "correlation_id": enhanced_error.correlation_id,
                "error_code": enhanced_error.error_code,
                "category": enhanced_error.category.value,
                "severity": enhanced_error.severity.value,
                "user_message": enhanced_error.user_message,
                "technical_message": enhanced_error.technical_message,
                "context": {
                    "user_id": enhanced_error.context.user_id,
                    "project_id": enhanced_error.context.project_id,
                    "endpoint": enhanced_error.context.endpoint,
                    "timestamp": enhanced_error.context.timestamp.isoformat()
                },
                "solutions_provided": len(enhanced_error.solutions),
                "metadata": enhanced_error.metadata
            }
            
            # Store with 7-day TTL
            await redis_client.setex(
                f"error_analytics:{enhanced_error.correlation_id}",
                604800,  # 7 days
                json.dumps(error_data, default=str)
            )
            
            # Increment error counter for user
            if enhanced_error.context.user_id:
                user_key = f"user_errors:{enhanced_error.context.user_id}:{enhanced_error.error_code}"
                await redis_client.incr(user_key)
                await redis_client.expire(user_key, 3600)  # 1 hour TTL
            
        except Exception as e:
            logger.error(f"Failed to store error analytics: {e}")
    
    async def get_error_analytics(
        self,
        time_window_hours: int = 24
    ) -> Dict[str, Any]:
        """Get error analytics for the specified time window."""
        
        try:
            redis_client = get_redis_client()
            
            # Get all error keys
            error_keys = await redis_client.keys("error_analytics:*")
            
            if not error_keys:
                return {
                    "total_errors": 0,
                    "by_category": {},
                    "by_severity": {},
                    "top_error_codes": [],
                    "user_impact_distribution": {}
                }
            
            # Analyze errors
            cutoff_time = datetime.utcnow() - timedelta(hours=time_window_hours)
            
            errors_data = []
            for key in error_keys:
                error_data = await redis_client.get(key)
                if error_data:
                    try:
                        data = json.loads(error_data)
                        error_time = datetime.fromisoformat(data["context"]["timestamp"])
                        if error_time >= cutoff_time:
                            errors_data.append(data)
                    except (json.JSONDecodeError, KeyError, ValueError):
                        continue
            
            # Generate analytics
            analytics = self._analyze_errors_data(errors_data)
            analytics["time_window_hours"] = time_window_hours
            analytics["analysis_timestamp"] = datetime.utcnow().isoformat()
            
            return analytics
            
        except Exception as e:
            logger.error(f"Failed to get error analytics: {e}")
            return {"error": f"Analytics unavailable: {str(e)}"}
    
    def _analyze_errors_data(self, errors_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze errors data to generate insights."""
        
        total_errors = len(errors_data)
        
        if total_errors == 0:
            return {
                "total_errors": 0,
                "by_category": {},
                "by_severity": {},
                "top_error_codes": [],
                "user_impact_distribution": {}
            }
        
        # Count by category
        by_category = {}
        by_severity = {}
        error_codes = {}
        impact_distribution = {}
        
        for error in errors_data:
            # Category counts
            category = error.get("category", "unknown")
            by_category[category] = by_category.get(category, 0) + 1
            
            # Severity counts
            severity = error.get("severity", "unknown")
            by_severity[severity] = by_severity.get(severity, 0) + 1
            
            # Error code counts
            error_code = error.get("error_code", "unknown")
            error_codes[error_code] = error_codes.get(error_code, 0) + 1
            
            # Impact distribution
            impact = error.get("metadata", {}).get("user_impact", "unknown")
            impact_distribution[impact] = impact_distribution.get(impact, 0) + 1
        
        # Top error codes
        top_error_codes = sorted(
            error_codes.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        return {
            "total_errors": total_errors,
            "by_category": by_category,
            "by_severity": by_severity,
            "top_error_codes": [{"code": code, "count": count} for code, count in top_error_codes],
            "user_impact_distribution": impact_distribution
        }

# Global service instance
error_experience_service = ErrorExperienceService()

# Convenience functions
async def enhance_error_experience(
    error: Exception,
    context: ErrorContext
) -> EnhancedError:
    """Enhance an error with user-friendly information."""
    return await error_experience_service.enhance_error(error, context)

async def get_error_insights(time_window_hours: int = 24) -> Dict[str, Any]:
    """Get error analytics and insights."""
    return await error_experience_service.get_error_analytics(time_window_hours)