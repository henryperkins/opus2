#!/usr/bin/env python3
"""
Fix incorrect Azure OpenAI API usage patterns.
This script identifies and suggests fixes for common Azure OpenAI API issues.
"""

import os
import re
from pathlib import Path
from typing import List, Dict, Any

def find_azure_api_issues() -> List[Dict[str, Any]]:
    """Find Azure OpenAI API usage issues in the codebase."""
    issues = []
    backend_path = Path(__file__).parent

    # Issue 1: Check for deprecated deployment name usage
    deployment_patterns = [
        r'azure_openai_chat_deployment',
        r'azure_openai_embeddings_deployment',
        r'settings\.azure_openai.*deployment',
        r'/openai/deployments/',
        r'deployment[-_]name'
    ]

    # Issue 2: Check for incorrect API version usage
    api_version_patterns = [
        r'api[-_]version.*=.*["\'](?!preview)[^"\']*["\']',
        r'api_version.*=.*["\'](?!preview)[^"\']*["\']'
    ]

    # Issue 3: Check for old base URL patterns
    old_url_patterns = [
        r'azure_endpoint',
        r'\.openai\.azure\.com[^/]',
        r'\.openai\.azure\.com$'
    ]

    # Scan Python files
    for py_file in backend_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        try:
            content = py_file.read_text()

            # Check for deployment usage
            for pattern in deployment_patterns:
                matches = re.finditer(pattern, content, re.IGNORECASE)
                for match in matches:
                    issues.append({
                        "type": "deprecated_deployment",
                        "file": str(py_file),
                        "line": content[:match.start()].count('\n') + 1,
                        "match": match.group(),
                        "suggestion": "Use model ID directly with v1 API"
                    })

            # Check for API version issues
            for pattern in api_version_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    issues.append({
                        "type": "incorrect_api_version",
                        "file": str(py_file),
                        "line": content[:match.start()].count('\n') + 1,
                        "match": match.group(),
                        "suggestion": "Use 'preview' for v1 API surface"
                    })

            # Check for old URL patterns
            for pattern in old_url_patterns:
                matches = re.finditer(pattern, content)
                for match in matches:
                    issues.append({
                        "type": "old_url_pattern",
                        "file": str(py_file),
                        "line": content[:match.start()].count('\n') + 1,
                        "match": match.group(),
                        "suggestion": "Use base_url with /openai/v1/ path"
                    })

        except Exception as e:
            print(f"Error reading {py_file}: {e}")

    return issues

def generate_fixes() -> Dict[str, str]:
    """Generate code fixes for common Azure OpenAI issues."""
    fixes = {}

    # Fix 1: Updated client factory
    fixes["client_factory_fix"] = """
# Updated Azure client factory
def get_azure_client() -> AsyncAzureOpenAI:
    '''Return a fully configured AsyncAzureOpenAI instance for v1 API.'''

    resource_endpoint = (
        settings.azure_openai_endpoint or "https://example.openai.azure.com"
    ).rstrip("/")

    # Always use v1 API surface
    base_url = f"{resource_endpoint}/openai/v1/"

    kwargs = {
        "base_url": base_url,
        "api_version": "preview",  # Required for v1 surface
        "default_query": {"api-version": "preview"},
        "timeout": getattr(settings, "openai_timeout", 300),
        "max_retries": 0
    }

    # Use API key authentication
    if not settings.azure_openai_api_key:
        raise ValueError("AZURE_OPENAI_API_KEY is required")

    kwargs["api_key"] = settings.azure_openai_api_key

    return AsyncAzureOpenAI(**kwargs)
"""

    # Fix 2: Updated config validation
    fixes["config_validation_fix"] = """
# Remove deployment-specific validation
def validate_azure_config(config: dict) -> List[str]:
    '''Validate Azure OpenAI configuration for v1 API.'''
    errors = []

    # Check required fields
    if not config.get("endpoint"):
        errors.append("Azure OpenAI endpoint is required")

    if not config.get("api_key"):
        errors.append("Azure OpenAI API key is required")

    # Validate endpoint format
    endpoint = config.get("endpoint", "")
    if endpoint and not endpoint.endswith(".openai.azure.com"):
        errors.append("Azure OpenAI endpoint must end with .openai.azure.com")

    # Model validation (no deployment names needed)
    model_id = config.get("model_id")
    if model_id and not _is_valid_azure_model(model_id):
        errors.append(f"Model {model_id} not supported by Azure OpenAI")

    return errors
"""

    # Fix 3: Updated provider initialization
    fixes["provider_init_fix"] = """
# Updated Azure provider initialization
class AzureOpenAIProvider(LLMProvider):
    def __init__(self, **kwargs):
        # Remove deployment-specific config
        self.use_responses_api = kwargs.get("use_responses_api", False)
        super().__init__(**kwargs)

    def _initialize_client(self) -> None:
        '''Initialize Azure OpenAI client for v1 API.'''
        endpoint = self.config.get("endpoint")
        if not endpoint:
            raise ValueError("Azure OpenAI endpoint is required")

        # Ensure correct endpoint format
        if not endpoint.endswith(".openai.azure.com"):
            raise ValueError("Invalid Azure OpenAI endpoint format")

        # Use v1 API surface
        base_url = f"{endpoint.rstrip('/')}/openai/v1/"

        client_kwargs = {
            "base_url": base_url,
            "api_version": "preview",
            "default_query": {"api-version": "preview"},
            "timeout": self.config.get("timeout", 300),
            "max_retries": 0,
        }

        # API key authentication
        api_key = self.config.get("api_key")
        if not api_key:
            raise ValueError("Azure OpenAI API key is required")
        client_kwargs["api_key"] = api_key

        self.client = AsyncAzureOpenAI(**client_kwargs)
"""

    return fixes

def main():
    """Main function to identify and report Azure API issues."""
    print("🔍 Scanning for Azure OpenAI API usage issues...\n")

    issues = find_azure_api_issues()

    if not issues:
        print("✅ No Azure OpenAI API issues found!")
        return

    # Group issues by type
    issue_groups = {}
    for issue in issues:
        issue_type = issue["type"]
        if issue_type not in issue_groups:
            issue_groups[issue_type] = []
        issue_groups[issue_type].append(issue)

    # Report issues
    print(f"❌ Found {len(issues)} Azure OpenAI API issues:\n")

    for issue_type, group_issues in issue_groups.items():
        print(f"📍 {issue_type.replace('_', ' ').title()}: {len(group_issues)} issues")
        print("-" * 60)

        for issue in group_issues[:5]:  # Show first 5 of each type
            rel_path = os.path.relpath(issue["file"])
            print(f"   {rel_path}:{issue['line']} - {issue['match']}")
            print(f"   💡 {issue['suggestion']}")
            print()

        if len(group_issues) > 5:
            print(f"   ... and {len(group_issues) - 5} more\n")

    # Show recommended fixes
    print("\n🔧 Recommended Fixes:")
    print("=" * 80)

    fixes = generate_fixes()
    for fix_name, fix_code in fixes.items():
        print(f"\n{fix_name.replace('_', ' ').title()}:")
        print(fix_code)

    print("\n📋 Summary of Required Changes:")
    print("-" * 40)
    print("1. Remove all deployment name references")
    print("2. Use 'preview' API version consistently")
    print("3. Always use /openai/v1/ base URL")
    print("4. Pass model IDs directly (not deployment names)")
    print("5. Update configuration validation logic")

if __name__ == "__main__":
    main()
