
import asyncio
import json
from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.project import PromptTemplate
from app.schemas.generation import GenerationParams
from pydantic import ValidationError

FIELD_MAPPING = {
    'maxTokens': 'max_tokens',
    'topP': 'top_p',
    'topK': 'top_k',
    'frequencyPenalty': 'frequency_penalty',
    'presencePenalty': 'presence_penalty',
    'stopSequences': 'stop_sequences',
}

async def migrate_prompt_templates():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PromptTemplate))
        templates = result.scalars().all()

        for template in templates:
            if template.llm_preferences:
                migrated = {}
                # Handle if llm_preferences is a string
                if isinstance(template.llm_preferences, str):
                    try:
                        prefs = json.loads(template.llm_preferences)
                    except json.JSONDecodeError:
                        print(f"Could not decode llm_preferences for template {template.id}")
                        continue
                else:
                    prefs = template.llm_preferences

                for old_key, new_key in FIELD_MAPPING.items():
                    if old_key in prefs:
                        migrated[new_key] = prefs[old_key]
                
                # Preserve existing snake_case keys
                for key, value in prefs.items():
                    if key not in migrated and key not in FIELD_MAPPING:
                        migrated[key] = value

                try:
                    # Validate and apply defaults for missing fields
                    validated = GenerationParams(**migrated)
                    template.llm_preferences = validated.model_dump(exclude_unset=True)
                except ValidationError as e:
                    print(f"Template {template.id} validation failed: {e}")
                    # Apply defaults for invalid values
                    template.llm_preferences = GenerationParams().model_dump(exclude_unset=True)
        
        await session.commit()
        print(f"Successfully migrated {len(templates)} prompt templates.")

if __name__ == "__main__":
    asyncio.run(migrate_prompt_templates())
