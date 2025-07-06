"""Advanced security and access control service."""

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any, Tuple
from enum import Enum
import hashlib
import secrets
from dataclasses import dataclass

from sqlalchemy.orm import Session
from app.models.user import User
from app.models.project import Project
from app.models.code_document import CodeDocument
from app.core.config import settings

logger = logging.getLogger(__name__)


class Permission(Enum):
    """Permission types for resource access."""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"
    EXECUTE = "execute"
    SHARE = "share"


class ResourceType(Enum):
    """Types of resources that can be secured."""
    PROJECT = "project"
    DOCUMENT = "document"
    SEARCH = "search"
    CHAT = "chat"
    EMBEDDING = "embedding"
    FEEDBACK = "feedback"


@dataclass
class AccessRule:
    """Access control rule definition."""
    resource_type: ResourceType
    resource_id: Optional[str] = None
    permission: Permission = Permission.READ
    conditions: Dict[str, Any] = None
    expiry: Optional[datetime] = None
    metadata: Dict[str, Any] = None
    
    def is_expired(self) -> bool:
        """Check if rule has expired."""
        return self.expiry is not None and datetime.utcnow() > self.expiry
    
    def matches(self, resource_type: ResourceType, resource_id: str = None) -> bool:
        """Check if rule matches given resource."""
        if self.resource_type != resource_type:
            return False
        if self.resource_id is not None and self.resource_id != resource_id:
            return False
        return not self.is_expired()


@dataclass
class SecurityContext:
    """Security context for requests."""
    user_id: int
    user_roles: Set[str]
    ip_address: str
    user_agent: str
    session_id: str
    authenticated_at: datetime
    permissions: Set[Permission]
    resource_access: Dict[str, Set[Permission]]
    security_level: str = "standard"  # standard, elevated, restricted
    
    def has_permission(self, permission: Permission, 
                      resource_type: ResourceType = None,
                      resource_id: str = None) -> bool:
        """Check if context has specific permission."""
        if permission in self.permissions:
            return True
        
        if resource_type and resource_id:
            resource_key = f"{resource_type.value}:{resource_id}"
            return permission in self.resource_access.get(resource_key, set())
        
        return False


class SecurityService:
    """Advanced security and access control service."""
    
    def __init__(self):
        self.access_rules: Dict[int, List[AccessRule]] = {}  # user_id -> rules
        self.security_policies: Dict[str, Dict[str, Any]] = {}
        self.rate_limits: Dict[str, Dict[str, Any]] = {}
        self.failed_attempts: Dict[str, List[datetime]] = {}
        self.security_events: List[Dict[str, Any]] = []
        
        # Default security policies
        self._initialize_default_policies()
    
    def _initialize_default_policies(self):
        """Initialize default security policies."""
        self.security_policies = {
            "password_policy": {
                "min_length": 8,
                "require_uppercase": True,
                "require_lowercase": True,
                "require_numbers": True,
                "require_special": True,
                "max_age_days": 90,
                "history_count": 5
            },
            "session_policy": {
                "max_duration_hours": 24,
                "idle_timeout_minutes": 120,
                "concurrent_sessions": 3,
                "require_mfa": False
            },
            "access_policy": {
                "default_permissions": [Permission.READ],
                "admin_permissions": [Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN],
                "require_approval": [Permission.DELETE, Permission.ADMIN],
                "audit_all_access": True
            },
            "rate_limiting": {
                "api_requests_per_minute": 100,
                "search_queries_per_minute": 20,
                "upload_files_per_hour": 50,
                "failed_login_lockout_minutes": 15,
                "max_failed_attempts": 5
            },
            "data_protection": {
                "encryption_at_rest": True,
                "encryption_in_transit": True,
                "data_retention_days": 365,
                "auto_redact_secrets": True,
                "content_scanning": True
            }
        }
    
    async def create_security_context(self, 
                                    user: User,
                                    ip_address: str,
                                    user_agent: str,
                                    session_id: str) -> SecurityContext:
        """Create security context for user session."""
        try:
            # Get user roles and permissions
            user_roles = self._get_user_roles(user)
            permissions = self._calculate_permissions(user, user_roles)
            resource_access = await self._get_resource_access(user.id)
            
            # Determine security level
            security_level = self._determine_security_level(user, ip_address)
            
            context = SecurityContext(
                user_id=user.id,
                user_roles=user_roles,
                ip_address=ip_address,
                user_agent=user_agent,
                session_id=session_id,
                authenticated_at=datetime.utcnow(),
                permissions=permissions,
                resource_access=resource_access,
                security_level=security_level
            )
            
            # Log security event
            await self._log_security_event("context_created", {
                "user_id": user.id,
                "ip_address": ip_address,
                "security_level": security_level
            })
            
            return context
            
        except Exception as e:
            logger.error(f"Failed to create security context: {e}")
            raise
    
    def _get_user_roles(self, user: User) -> Set[str]:
        """Get user roles from user profile."""
        # Default role determination logic
        roles = {"user"}
        
        if hasattr(user, 'is_admin') and user.is_admin:
            roles.add("admin")
        
        if hasattr(user, 'is_moderator') and user.is_moderator:
            roles.add("moderator")
        
        # Add organization-specific roles if available
        if hasattr(user, 'organization_roles'):
            roles.update(user.organization_roles)
        
        return roles
    
    def _calculate_permissions(self, user: User, user_roles: Set[str]) -> Set[Permission]:
        """Calculate user permissions based on roles."""
        permissions = set(self.security_policies["access_policy"]["default_permissions"])
        
        if "admin" in user_roles:
            permissions.update(self.security_policies["access_policy"]["admin_permissions"])
        
        if "moderator" in user_roles:
            permissions.update([Permission.READ, Permission.WRITE, Permission.SHARE])
        
        return permissions
    
    async def _get_resource_access(self, user_id: int) -> Dict[str, Set[Permission]]:
        """Get user's resource-specific access permissions."""
        resource_access = {}
        
        # Get user's access rules
        if user_id in self.access_rules:
            for rule in self.access_rules[user_id]:
                if not rule.is_expired():
                    resource_key = f"{rule.resource_type.value}:{rule.resource_id or '*'}"
                    if resource_key not in resource_access:
                        resource_access[resource_key] = set()
                    resource_access[resource_key].add(rule.permission)
        
        return resource_access
    
    def _determine_security_level(self, user: User, ip_address: str) -> str:
        """Determine security level based on context."""
        # Check for suspicious patterns
        if self._is_suspicious_ip(ip_address):
            return "restricted"
        
        # Check user's security status
        if hasattr(user, 'security_flags') and user.security_flags:
            return "elevated"
        
        return "standard"
    
    def _is_suspicious_ip(self, ip_address: str) -> bool:
        """Check if IP address is suspicious."""
        # Simple checks - in production, this would use threat intelligence
        suspicious_patterns = [
            "192.168.",  # Internal networks should be flagged if unexpected
            "10.",       # Private networks
            "172.16.",   # Private networks
        ]
        
        # For demo purposes, flag these as suspicious when not expected
        return False  # Simplified for now
    
    async def check_access(self, 
                          context: SecurityContext,
                          resource_type: ResourceType,
                          resource_id: str,
                          permission: Permission) -> Tuple[bool, Optional[str]]:
        """Check if user has access to perform action on resource."""
        try:
            # Rate limiting check
            if not await self._check_rate_limit(context, resource_type):
                return False, "Rate limit exceeded"
            
            # Permission check
            if not context.has_permission(permission, resource_type, resource_id):
                await self._log_security_event("access_denied", {
                    "user_id": context.user_id,
                    "resource_type": resource_type.value,
                    "resource_id": resource_id,
                    "permission": permission.value,
                    "reason": "insufficient_permissions"
                })
                return False, "Insufficient permissions"
            
            # Resource-specific checks
            if not await self._check_resource_access(context, resource_type, resource_id):
                return False, "Resource access denied"
            
            # Security level checks
            if not self._check_security_level(context, permission):
                return False, "Security level insufficient"
            
            # Log successful access
            await self._log_security_event("access_granted", {
                "user_id": context.user_id,
                "resource_type": resource_type.value,
                "resource_id": resource_id,
                "permission": permission.value
            })
            
            return True, None
            
        except Exception as e:
            logger.error(f"Access check failed: {e}")
            return False, "Security check error"
    
    async def _check_rate_limit(self, 
                               context: SecurityContext,
                               resource_type: ResourceType) -> bool:
        """Check rate limiting for user actions."""
        rate_key = f"{context.user_id}:{resource_type.value}"
        current_time = datetime.utcnow()
        
        # Get rate limit window
        if rate_key not in self.rate_limits:
            self.rate_limits[rate_key] = {
                "requests": [],
                "window_start": current_time
            }
        
        rate_data = self.rate_limits[rate_key]
        
        # Clean old requests (1 minute window)
        window_start = current_time - timedelta(minutes=1)
        rate_data["requests"] = [
            req_time for req_time in rate_data["requests"]
            if req_time > window_start
        ]
        
        # Check limits based on resource type
        limits = self.security_policies["rate_limiting"]
        max_requests = limits.get("api_requests_per_minute", 100)
        
        if resource_type == ResourceType.SEARCH:
            max_requests = limits.get("search_queries_per_minute", 20)
        
        if len(rate_data["requests"]) >= max_requests:
            await self._log_security_event("rate_limit_exceeded", {
                "user_id": context.user_id,
                "resource_type": resource_type.value,
                "request_count": len(rate_data["requests"]),
                "limit": max_requests
            })
            return False
        
        # Add current request
        rate_data["requests"].append(current_time)
        return True
    
    async def _check_resource_access(self, 
                                   context: SecurityContext,
                                   resource_type: ResourceType,
                                   resource_id: str) -> bool:
        """Check access to specific resource."""
        # Project access check
        if resource_type == ResourceType.PROJECT:
            return await self._check_project_access(context.user_id, resource_id)
        
        # Document access check
        elif resource_type == ResourceType.DOCUMENT:
            return await self._check_document_access(context.user_id, resource_id)
        
        # Default: allow access
        return True
    
    async def _check_project_access(self, user_id: int, project_id: str) -> bool:
        """Check if user has access to project."""
        try:
            # Check if user has explicit access rules for this project
            if user_id in self.access_rules:
                for rule in self.access_rules[user_id]:
                    if (rule.resource_type == ResourceType.PROJECT and 
                        (rule.resource_id == project_id or rule.resource_id is None) and
                        not rule.is_expired()):
                        return True
            
            # Check if project_id is valid format
            try:
                project_int_id = int(project_id)
                # In a real implementation, this would query the database
                # For now, we allow access to valid project IDs
                return project_int_id > 0
            except ValueError:
                return False
                
        except Exception as e:
            logger.error(f"Project access check failed: {e}")
            return False
    
    async def _check_document_access(self, user_id: int, document_id: str) -> bool:
        """Check if user has access to document."""
        try:
            # Check if user has explicit access rules for this document
            if user_id in self.access_rules:
                for rule in self.access_rules[user_id]:
                    if (rule.resource_type == ResourceType.DOCUMENT and 
                        (rule.resource_id == document_id or rule.resource_id is None) and
                        not rule.is_expired()):
                        return True
            
            # Check if document_id is valid format
            try:
                doc_int_id = int(document_id)
                # In a real implementation, this would query the database to check:
                # 1. Document exists
                # 2. Document belongs to a project user has access to
                # 3. Document is not marked as private/restricted
                return doc_int_id > 0
            except ValueError:
                return False
                
        except Exception as e:
            logger.error(f"Document access check failed: {e}")
            return False
    
    def _check_security_level(self, context: SecurityContext, permission: Permission) -> bool:
        """Check if security level is sufficient for permission."""
        if context.security_level == "restricted":
            # Restricted users can only read
            return permission == Permission.READ
        
        if context.security_level == "elevated":
            # Elevated security - require additional checks for sensitive operations
            if permission in [Permission.DELETE, Permission.ADMIN]:
                # Check if session is recent enough for sensitive operations
                session_age = (datetime.utcnow() - context.authenticated_at).total_seconds()
                max_session_age = 3600  # 1 hour for admin operations
                
                if session_age > max_session_age:
                    logger.warning(f"Elevated operation denied - session too old: {session_age}s")
                    return False
                
                # In production, this would check for MFA verification
                # For now, we allow if session is recent and user has admin role
                return "admin" in context.user_roles
        
        return True
    
    async def _log_security_event(self, event_type: str, details: Dict[str, Any]):
        """Log security event for audit trail."""
        event = {
            "timestamp": datetime.utcnow(),
            "event_type": event_type,
            "details": details,
            "event_id": secrets.token_hex(16)
        }
        
        self.security_events.append(event)
        
        # Keep only recent events (for memory management)
        if len(self.security_events) > 10000:
            self.security_events = self.security_events[-5000:]
        
        logger.info(f"Security event: {event_type} - {details}")
    
    async def grant_access(self, 
                          user_id: int,
                          resource_type: ResourceType,
                          resource_id: str,
                          permission: Permission,
                          expiry: Optional[datetime] = None,
                          granted_by: int = None) -> bool:
        """Grant access permission to user for resource."""
        try:
            rule = AccessRule(
                resource_type=resource_type,
                resource_id=resource_id,
                permission=permission,
                expiry=expiry,
                metadata={"granted_by": granted_by, "granted_at": datetime.utcnow()}
            )
            
            if user_id not in self.access_rules:
                self.access_rules[user_id] = []
            
            self.access_rules[user_id].append(rule)
            
            await self._log_security_event("access_granted", {
                "user_id": user_id,
                "resource_type": resource_type.value,
                "resource_id": resource_id,
                "permission": permission.value,
                "granted_by": granted_by,
                "expiry": expiry.isoformat() if expiry else None
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to grant access: {e}")
            return False
    
    async def revoke_access(self, 
                           user_id: int,
                           resource_type: ResourceType,
                           resource_id: str,
                           permission: Permission,
                           revoked_by: int = None) -> bool:
        """Revoke access permission from user."""
        try:
            if user_id not in self.access_rules:
                return False
            
            # Find and remove matching rules
            rules_to_remove = []
            for i, rule in enumerate(self.access_rules[user_id]):
                if (rule.resource_type == resource_type and 
                    rule.resource_id == resource_id and 
                    rule.permission == permission):
                    rules_to_remove.append(i)
            
            # Remove rules in reverse order to maintain indices
            for i in reversed(rules_to_remove):
                del self.access_rules[user_id][i]
            
            await self._log_security_event("access_revoked", {
                "user_id": user_id,
                "resource_type": resource_type.value,
                "resource_id": resource_id,
                "permission": permission.value,
                "revoked_by": revoked_by,
                "rules_removed": len(rules_to_remove)
            })
            
            return len(rules_to_remove) > 0
            
        except Exception as e:
            logger.error(f"Failed to revoke access: {e}")
            return False
    
    async def audit_user_access(self, user_id: int) -> Dict[str, Any]:
        """Generate audit report for user access."""
        try:
            # Get user's current rules
            current_rules = self.access_rules.get(user_id, [])
            active_rules = [rule for rule in current_rules if not rule.is_expired()]
            
            # Get recent security events for user
            user_events = [
                event for event in self.security_events
                if event["details"].get("user_id") == user_id
            ][-100:]  # Last 100 events
            
            # Calculate access statistics
            permissions_by_resource = {}
            for rule in active_rules:
                resource_key = f"{rule.resource_type.value}:{rule.resource_id or '*'}"
                if resource_key not in permissions_by_resource:
                    permissions_by_resource[resource_key] = []
                permissions_by_resource[resource_key].append(rule.permission.value)
            
            return {
                "user_id": user_id,
                "audit_timestamp": datetime.utcnow(),
                "active_rules_count": len(active_rules),
                "expired_rules_count": len(current_rules) - len(active_rules),
                "permissions_by_resource": permissions_by_resource,
                "recent_events": user_events,
                "security_summary": {
                    "total_access_attempts": len([e for e in user_events if "access" in e["event_type"]]),
                    "failed_attempts": len([e for e in user_events if e["event_type"] == "access_denied"]),
                    "rate_limit_violations": len([e for e in user_events if e["event_type"] == "rate_limit_exceeded"])
                }
            }
            
        except Exception as e:
            logger.error(f"Audit failed for user {user_id}: {e}")
            return {"error": str(e)}
    
    async def get_security_metrics(self) -> Dict[str, Any]:
        """Get overall security metrics."""
        try:
            recent_events = self.security_events[-1000:]  # Last 1000 events
            
            event_counts = {}
            for event in recent_events:
                event_type = event["event_type"]
                event_counts[event_type] = event_counts.get(event_type, 0) + 1
            
            return {
                "timestamp": datetime.utcnow(),
                "total_events": len(self.security_events),
                "recent_events": len(recent_events),
                "event_breakdown": event_counts,
                "active_users": len(self.access_rules),
                "total_rules": sum(len(rules) for rules in self.access_rules.values()),
                "rate_limited_users": len(self.rate_limits),
                "security_policies": list(self.security_policies.keys())
            }
            
        except Exception as e:
            logger.error(f"Failed to get security metrics: {e}")
            return {"error": str(e)}


# Global security service instance
security_service = SecurityService()