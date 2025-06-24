/**
 * Utility functions for testing message creation and validation
 */

export const validateMessagePayload = (payload) => {
    const requiredFields = ['role', 'content'];
    const optionalFields = ['code_snippets', 'referenced_files', 'referenced_chunks', 'applied_commands'];

    const errors = [];

    // Check required fields
    requiredFields.forEach(field => {
        if (!payload.hasOwnProperty(field)) {
            errors.push(`Missing required field: ${field}`);
        }
    });

    // Validate role
    if (payload.role && !['user', 'assistant', 'system'].includes(payload.role)) {
        errors.push(`Invalid role: ${payload.role}. Must be one of: user, assistant, system`);
    }

    // Validate content
    if (payload.content && (typeof payload.content !== 'string' || payload.content.length === 0)) {
        errors.push('Content must be a non-empty string');
    }

    if (payload.content && payload.content.length > 10000) {
        errors.push('Content exceeds maximum length of 10,000 characters');
    }

    // Validate optional arrays
    ['code_snippets', 'referenced_files', 'referenced_chunks'].forEach(field => {
        if (payload[field] && !Array.isArray(payload[field])) {
            errors.push(`${field} must be an array`);
        }
    });

    // Validate applied_commands
    if (payload.applied_commands && typeof payload.applied_commands !== 'object') {
        errors.push('applied_commands must be an object');
    }

    return {
        isValid: errors.length === 0,
        errors
    };
};

export const createTestMessagePayload = (overrides = {}) => {
    return {
        role: 'user',
        content: 'Test message content',
        code_snippets: [],
        referenced_files: [],
        referenced_chunks: [],
        applied_commands: {},
        ...overrides
    };
};

export const createMetadataFromFrontend = (frontendMetadata = {}) => {
    return {
        role: 'user',
        content: frontendMetadata.content || 'Test message',
        code_snippets: frontendMetadata.code_snippets || [],
        referenced_files: frontendMetadata.referenced_files || [],
        referenced_chunks: frontendMetadata.referenced_chunks || [],
        applied_commands: frontendMetadata.applied_commands || {},
    };
};

// Test the transformation from old format to new format
export const testMessageTransformation = () => {
    const oldFormat = {
        content: 'Hello world',
        metadata: {
            code_snippets: [{ language: 'python', code: 'print("hello")' }],
            referenced_files: ['test.py'],
        }
    };

    const newFormat = createMetadataFromFrontend({
        content: oldFormat.content,
        ...oldFormat.metadata
    });

    const validation = validateMessagePayload(newFormat);

    console.log('Old format:', oldFormat);
    console.log('New format:', newFormat);
    console.log('Validation:', validation);

    return validation.isValid;
};
