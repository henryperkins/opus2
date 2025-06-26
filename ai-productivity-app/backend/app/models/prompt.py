# Prompt template model for managing reusable AI prompts
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship, validates
from .base import Base, TimestampMixin
import re


class PromptTemplate(Base, TimestampMixin):
    """Prompt template model for reusable AI prompts"""

    __tablename__ = "prompt_templates"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, comment="Template name")
    description = Column(Text, nullable=True, comment="Template description")
    category = Column(String(100), nullable=False, default="Custom", comment="Template category")
    
    # Prompt content
    system_prompt = Column(Text, nullable=True, comment="System prompt for AI")
    user_prompt_template = Column(Text, nullable=False, comment="User prompt template with variables")
    
    # Template configuration
    variables = Column(JSONB, default=list, nullable=False, comment="Template variables definition")
    model_preferences = Column(JSONB, default=dict, nullable=False, comment="Model-specific preferences")
    
    # Ownership and visibility
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="Template owner")
    is_public = Column(Boolean, default=False, nullable=False, comment="Whether template is public")
    is_default = Column(Boolean, default=False, nullable=False, comment="Whether template is a default/system template")
    
    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False, comment="Number of times template was used")
    
    # Relationships
    user = relationship("User", back_populates="prompt_templates")

    @validates("name")
    def validate_name(self, key, name):
        """Validate template name"""
        if not name or len(name.strip()) < 1:
            raise ValueError("Template name is required")
        if len(name) > 255:
            raise ValueError("Template name must be 255 characters or less")
        return name.strip()

    @validates("category")
    def validate_category(self, key, category):
        """Validate template category"""
        valid_categories = [
            "Code Generation", "Code Review", "Documentation", "Testing",
            "Debugging", "Refactoring", "Architecture", "Custom"
        ]
        if category not in valid_categories:
            raise ValueError(f"Category must be one of: {', '.join(valid_categories)}")
        return category

    @validates("user_prompt_template")
    def validate_user_prompt_template(self, key, template):
        """Validate user prompt template"""
        if not template or len(template.strip()) < 1:
            raise ValueError("User prompt template is required")
        return template

    @validates("variables")
    def validate_variables(self, key, variables):
        """Validate variables structure"""
        if not isinstance(variables, list):
            raise ValueError("Variables must be a list")
        
        for var in variables:
            if not isinstance(var, dict):
                raise ValueError("Each variable must be a dictionary")
            if "name" not in var:
                raise ValueError("Each variable must have a 'name' field")
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", var["name"]):
                raise ValueError("Variable names must be valid identifiers")
        
        return variables

    def increment_usage(self):
        """Increment usage count"""
        self.usage_count = (self.usage_count or 0) + 1

    def render_prompt(self, variable_values):
        """Render the template with provided variable values"""
        prompt = self.user_prompt_template
        
        # Replace variables in the format {{variableName}}
        for var in self.variables:
            var_name = var["name"]
            if var_name in variable_values:
                value = str(variable_values[var_name])
                prompt = prompt.replace(f"{{{{{var_name}}}}}", value)
            elif var.get("required", False):
                raise ValueError(f"Required variable '{var_name}' not provided")
            else:
                # Replace with empty string if not required
                prompt = prompt.replace(f"{{{{{var_name}}}}}", "")
        
        return prompt

    def __repr__(self):
        return f"<PromptTemplate(id={self.id}, name='{self.name}', category='{self.category}')>"