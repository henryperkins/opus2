#!/usr/bin/env python3
"""
Simplified Azure OpenAI configuration validator.
This script validates that the Azure OpenAI configuration is properly set up.
"""

import os
import json
from pathlib import Path

def validate_environment_variables():
    """Validate that required Azure OpenAI environment variables are set."""
    print("🔧 Validating Azure OpenAI environment variables...")
    
    required_vars = {
        'LLM_PROVIDER': 'azure',
        'AZURE_OPENAI_API_KEY': 'API key for Azure OpenAI',
        'AZURE_OPENAI_ENDPOINT': 'Azure OpenAI endpoint URL',
        'AZURE_OPENAI_API_VERSION': 'API version',
        'LLM_DEFAULT_MODEL': 'Default model deployment name'
    }
    
    # Read .env file
    env_file = Path(__file__).parent / '.env'
    env_vars = {}
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # Check each required variable
    all_valid = True
    for var, description in required_vars.items():
        value = env_vars.get(var) or os.getenv(var)
        
        if not value:
            print(f"❌ {var}: Not set ({description})")
            all_valid = False
        elif var == 'LLM_PROVIDER' and value.lower() != 'azure':
            print(f"❌ {var}: Set to '{value}', should be 'azure'")
            all_valid = False
        elif var == 'AZURE_OPENAI_API_KEY' and len(value) < 10:
            print(f"❌ {var}: Too short, likely invalid")
            all_valid = False
        elif var == 'AZURE_OPENAI_ENDPOINT' and not value.startswith('https://'):
            print(f"❌ {var}: Should start with 'https://'")
            all_valid = False
        else:
            # Mask API key for security
            display_value = value
            if var == 'AZURE_OPENAI_API_KEY':
                display_value = f"{'*' * 20}...{value[-4:] if len(value) > 4 else value}"
            print(f"✅ {var}: {display_value}")
    
    return all_valid

def validate_deployment_names():
    """Validate the deployment names are correctly configured."""
    print("\n🔧 Validating deployment names...")
    
    env_file = Path(__file__).parent / '.env'
    env_vars = {}
    
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    default_model = env_vars.get('LLM_DEFAULT_MODEL') or os.getenv('LLM_DEFAULT_MODEL')
    
    # Check if it's one of the supported deployment names
    supported_deployments = ['gpt-4.1', 'o3']
    
    if default_model in supported_deployments:
        print(f"✅ Default model '{default_model}' is a supported deployment name")
        return True
    else:
        print(f"❌ Default model '{default_model}' is not in supported deployments: {supported_deployments}")
        print("   Available deployment names:")
        for deployment in supported_deployments:
            print(f"   - {deployment}")
        return False

def validate_backend_config():
    """Validate the backend configuration files."""
    print("\n🔧 Validating backend configuration...")
    
    backend_dir = Path(__file__).parent / 'backend'
    
    # Check if copilot router exists
    copilot_router = backend_dir / 'app' / 'routers' / 'copilot.py'
    if copilot_router.exists():
        print("✅ Copilot router exists")
        
        # Check if it imports the LLM client correctly
        with open(copilot_router) as f:
            content = f.read()
            if 'from ..llm.client import llm_client' in content:
                print("✅ Copilot router imports LLM client correctly")
            else:
                print("❌ Copilot router missing LLM client import")
                return False
    else:
        print("❌ Copilot router not found")
        return False
    
    # Check if config router has Azure models
    config_router = backend_dir / 'app' / 'routers' / 'config.py'
    if config_router.exists():
        print("✅ Config router exists")
        
        with open(config_router) as f:
            content = f.read()
            if 'gpt-4.1' in content and 'o3' in content:
                print("✅ Config router includes supported deployment names")
            else:
                print("❌ Config router missing supported deployment names")
                return False
    else:
        print("❌ Config router not found")
        return False
    
    return True

def validate_frontend_config():
    """Validate the frontend configuration."""
    print("\n🔧 Validating frontend configuration...")
    
    frontend_dir = Path(__file__).parent / 'frontend'
    
    # Check if ModelSwitcher includes Azure models
    model_switcher = frontend_dir / 'src' / 'components' / 'chat' / 'ModelSwitcher.jsx'
    if model_switcher.exists():
        print("✅ ModelSwitcher component exists")
        
        with open(model_switcher) as f:
            content = f.read()
            if 'gpt-4.1' in content and 'Azure' in content:
                print("✅ ModelSwitcher includes Azure deployment names")
            else:
                print("❌ ModelSwitcher missing Azure deployment names")
                return False
    else:
        print("❌ ModelSwitcher component not found")
        return False
    
    # Check if useCodeEditor includes Monacopilot
    use_code_editor = frontend_dir / 'src' / 'hooks' / 'useCodeEditor.js'
    if use_code_editor.exists():
        print("✅ useCodeEditor hook exists")
        
        with open(use_code_editor) as f:
            content = f.read()
            if 'monacopilot' in content and 'registerCompletion' in content:
                print("✅ useCodeEditor integrates Monacopilot")
            else:
                print("❌ useCodeEditor missing Monacopilot integration")
                return False
    else:
        print("❌ useCodeEditor hook not found")
        return False
    
    return True

def validate_monacopilot_endpoint():
    """Validate the Monacopilot endpoint configuration."""
    print("\n🔧 Validating Monacopilot endpoint configuration...")
    
    # Check if the copilot endpoint is properly configured
    copilot_router = Path(__file__).parent / 'backend' / 'app' / 'routers' / 'copilot.py'
    
    if copilot_router.exists():
        with open(copilot_router) as f:
            content = f.read()
            
            checks = [
                ('rate_limit', 'Rate limiting configured'),
                ('await llm_client.reconfigure()', 'LLM client reconfiguration'),
                ('build_completion_prompt', 'Prompt building function'),
                ('clean_completion', 'Response cleaning function'),
                ('/copilot', 'Correct endpoint path'),
            ]
            
            all_valid = True
            for check, description in checks:
                if check in content:
                    print(f"✅ {description}")
                else:
                    print(f"❌ Missing: {description}")
                    all_valid = False
            
            return all_valid
    
    return False

def main():
    """Run all validation checks."""
    print("🚀 Azure OpenAI + Monacopilot Configuration Validator")
    print("=" * 55)
    
    results = []
    
    # Run all validation checks
    results.append(validate_environment_variables())
    results.append(validate_deployment_names())
    results.append(validate_backend_config())
    results.append(validate_frontend_config())
    results.append(validate_monacopilot_endpoint())
    
    print("\n" + "=" * 55)
    print(f"📊 Validation Results: {sum(results)}/{len(results)} passed")
    
    if all(results):
        print("🎉 All validations passed! Azure OpenAI + Monacopilot is properly configured!")
        print("\n📋 Configuration Summary:")
        print("  ✅ Environment variables set correctly")
        print("  ✅ Deployment names configured (gpt-4.1, o3)")
        print("  ✅ Backend copilot endpoint ready")
        print("  ✅ Frontend components integrated")
        print("  ✅ Monacopilot endpoint configured")
        print("\n🚀 Ready to use Azure OpenAI with Monacopilot!")
    else:
        print("⚠️  Some validations failed. Please fix the issues above.")
        return 1
    
    return 0

if __name__ == "__main__":
    import sys
    sys.exit(main())