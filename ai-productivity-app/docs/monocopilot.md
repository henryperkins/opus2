# Monacopilot
[![Monacopilot Banner](https://camo.githubusercontent.com/dffa610b98442f5b580c7a5d9e852faf9dd254af53c3c58e1fb6210a0b527829/68747470733a2f2f692e706f7374696d672e63632f47687047566a56472f6d6f6e61636f70696c6f742d62616e6e65722e706e67)](https://camo.githubusercontent.com/dffa610b98442f5b580c7a5d9e852faf9dd254af53c3c58e1fb6210a0b527829/68747470733a2f2f692e706f7374696d672e63632f47687047566a56472f6d6f6e61636f70696c6f742d62616e6e65722e706e67)

**Monacopilot** is a powerful and customizable AI auto-completion plugin for the Monaco Editor, inspired by GitHub Copilot.

---

## Motivation
[![Monacopilot Motivation](https://camo.githubusercontent.com/f02adca7f3c219bb151411e20f55d876ddbac2129cc3f89708afbab1616df46e/68747470733a2f2f692e706f7374696d672e63632f6334474d3771335a2f6d6f7469766174696f6e2e706e67)](https://camo.githubusercontent.com/f02adca7f3c219bb151411e20f55d876ddbac2129cc3f89708afbab1616df46e/68747470733a2f2f692e706f7374696d672e63632f6334474d3771335a2f6d6f7469766174696f6e2e706e67)

---

## Table of Contents

- [Examples](#examples)
- [Demo](#demo)
- [Installation](#installation)
- [Usage](#usage)
  - [API Handler](#api-handler)
  - [Register Completion with the Monaco Editor](#register-completion-with-the-monaco-editor)
- [Register Completion Options](#register-completion-options)
  - [Trigger Mode](#trigger-mode)
  - [Manually Trigger Completions](#manually-trigger-completions)
    - [Keyboard Shortcut](#trigger-completions-with-a-keyboard-shortcut)
    - [Editor Action](#trigger-completions-with-an-editor-action)
  - [Multi-File Context](#multi-file-context)
  - [Filename](#filename)
  - [Completions for Specific Technologies](#completions-for-specific-technologies)
  - [Max Context Lines](#max-context-lines)
  - [Caching Completions](#caching-completions)
  - [Handling Errors](#handling-errors)
  - [Custom Request Handler](#custom-request-handler)
- [Copilot Options](#copilot-options)
  - [Changing the Provider and Model](#changing-the-provider-and-model)
  - [Custom Model](#custom-model)
- [Completion Request Options](#completion-request-options)
  - [Custom Headers](#custom-headers-for-ai-model-requests)
  - [Custom Prompt](#custom-prompt)
- [Cross-Language API Handler Implementation](#cross-language-api-handler-implementation)
- [Contributing](#contributing)

---

## Examples

Here are some examples of how to integrate **Monacopilot** into your project:

- **Next.js**
  - [App Router](https://github.com/arshad-yaseen/monacopilot/tree/main/examples/nextjs/app)
  - [Pages Router](https://github.com/arshad-yaseen/monacopilot/tree/main/examples/nextjs/pages)
- **Remix** – <https://github.com/arshad-yaseen/monacopilot/tree/main/examples/remix>
- **Vue** – <https://github.com/arshad-yaseen/monacopilot/tree/main/examples/vue>

---

## Demo

[Inline Completions Demo Video](https://github.com/user-attachments/assets/f2ec4ae1-f658-4002-af9c-c6b1bbad70d9)

---

## Installation

```bash
npm i monacopilot          # or pnpm / yarn / bun
```

---

## Usage

### API Handler <a id="api-handler"></a>

Set up an API handler to manage auto-completion requests.

```ts
import express from 'express';
import { Copilot } from 'monacopilot';

const app   = express();
const port  = process.env.PORT || 3000;

const copilot = new Copilot(process.env.GROQ_API_KEY!, {
  provider: 'groq',
  model: 'llama-3-70b',
});

app.use(express.json());

app.post('/complete', async (req, res) => {
  const { completion, error } = await copilot.complete({ body: req.body });

  if (error) return res.status(500).json({ completion: null, error });
  res.status(200).json({ completion });
});

app.listen(port);
```

Expected response shape:

```jsonc
{ "completion": "Generated completion text" }
```

On error:

```jsonc
{ "completion": null, "error": "Error message" }
```

If you prefer another language, see [Cross-Language API Handler Implementation](#cross-language-api-handler-implementation).

---

### Register Completion with the Monaco Editor <a id="register-completion-with-the-monaco-editor"></a>

```ts
import * as monaco from 'monaco-editor';
import { registerCompletion } from 'monacopilot';

const editor = monaco.editor.create(document.getElementById('container'), {
  language: 'javascript',
});

registerCompletion(monaco, editor, {
  endpoint: 'https://api.example.com/complete', // or '/api/complete'
  language: 'javascript',
  maxContextLines: 60,  // Groq rate-limit recommendation
});
```

> **Note**
> `registerCompletion` returns an object with `deregister()`.
> Call it (e.g., in React’s `useEffect` cleanup) to dispose the completion provider.

🎉 Start typing—AI completions will appear!

---

## Register Completion Options

### Trigger Mode <a id="trigger-mode"></a>

```ts
registerCompletion(monaco, editor, { trigger: 'onTyping' });
```

| Trigger        | Description                                   | Notes                                                                                                                                            |
| -------------- | --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| `'onIdle'`     | Default. Trigger after a brief pause.         | Less resource-intensive.                                                                                                                         |
| `'onTyping'`   | Real-time suggestions while typing.           | Best for low-latency models (e.g., Groq). Uses predictive caching.                                                                               |
| `'onDemand'`   | Only when manually triggered.                 | Full control—use `completion.trigger()`.                                                                                                         |

[OnTyping Demo](https://github.com/user-attachments/assets/22c2ce44-334c-4963-b853-01b890b8e39f)

---

### Manually Trigger Completions <a id="manually-trigger-completions"></a>

```ts
const completion = registerCompletion(monaco, editor, { trigger: 'onDemand' });
completion.trigger();
```

#### Keyboard Shortcut <a id="trigger-completions-with-a-keyboard-shortcut"></a>

```ts
monaco.editor.addCommand(
  monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Space,
  () => completion.trigger(),
);
```

#### Editor Action <a id="trigger-completions-with-an-editor-action"></a>

```ts
monaco.editor.addEditorAction({
  id: 'monacopilot.triggerCompletion',
  label: 'Complete Code',
  contextMenuGroupId: 'navigation',
  keybindings: [
    monaco.KeyMod.CtrlCmd | monaco.KeyMod.Shift | monaco.KeyCode.Space,
  ],
  run: () => completion.trigger(),
});
```

---

### Multi-File Context <a id="multi-file-context"></a>

```ts
registerCompletion(monaco, editor, {
  relatedFiles: [
    {
      path: './utils.js',
      content: 'export const reverse = (str) => str.split("").reverse().join("")',
    },
  ],
});
```

---

### Filename <a id="filename"></a>

```ts
registerCompletion(monaco, editor, { filename: 'utils.js' });
```

---

### Completions for Specific Technologies <a id="completions-for-specific-technologies"></a>

```ts
registerCompletion(monaco, editor, {
  technologies: ['react', 'next.js', 'tailwindcss'],
});
```

---

### Max Context Lines <a id="max-context-lines"></a>

```ts
registerCompletion(monaco, editor, { maxContextLines: 80 });
```

> **Note**
> With Groq, keep this ≤ 60 due to rate limits (until pay-as-you-go arrives).

---

### Caching Completions <a id="caching-completions"></a>

Disable FIFO caching:

```ts
registerCompletion(monaco, editor, { enableCaching: false });
```

---

### Handling Errors <a id="handling-errors"></a>

```ts
registerCompletion(monaco, editor, {
  onError: err => console.error(err),
});
```

---

### Custom Request Handler <a id="custom-request-handler"></a>

```ts
registerCompletion(monaco, editor, {
  endpoint: 'https://api.example.com/complete',
  requestHandler: async ({ endpoint, body }) => {
    const res  = await fetch(endpoint, {
      method : 'POST',
      headers: { 'Content-Type': 'application/json' },
      body   : JSON.stringify(body),
    });

    const data = await res.json();
    return { completion: data.completion };
  },
});
```

| Property  | Type     | Description                                               |
|-----------|----------|-----------------------------------------------------------|
| endpoint  | string   | Same as the `endpoint` option.                            |
| body      | object   | Request payload generated by Monacopilot.                |

---

#### Example (with extra headers & error handling)

```ts
registerCompletion(monaco, editor, {
  endpoint: 'https://api.example.com/complete',
  requestHandler: async ({ endpoint, body }) => {
    try {
      const res = await fetch(endpoint, {
        method : 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-Request-ID': generateUniqueId(),
        },
        body: JSON.stringify({ ...body, additionalProperty: 'value' }),
      });

      if (!res.ok) throw new Error(`HTTP ${res.status}`);

      const data = await res.json();
      if (data.error) return { completion: null };

      return { completion: data.completion.trim() };
    } catch (err) {
      console.error('Fetch error:', err);
      return { completion: null };
    }
  },
});
```

---

## Copilot Options <a id="copilot-options"></a>

### Changing the Provider and Model <a id="changing-the-provider-and-model"></a>

```ts
const copilot = new Copilot(process.env.OPENAI_API_KEY, {
  provider: 'openai',
  model   : 'gpt-4o',
});
```

Default: `groq` / `llama-3-70b`.

| Provider | Models                                                                                  |
|----------|-----------------------------------------------------------------------------------------|
| Groq     | `llama-3-70b`                                                                           |
| OpenAI   | `gpt-4o`, `gpt-4o-mini`, `o1-preview`, `o1-mini`                                        |
| Anthropic| `claude-3-5-sonnet`, `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`                |

---

### Custom Model <a id="custom-model"></a>

```ts
const copilot = new Copilot(process.env.HUGGINGFACE_API_KEY, {
  model: {
    config: (apiKey, prompt) => ({
      endpoint: 'https://api-inference.huggingface.co/models/openai-community/gpt2',
      headers : { Authorization: `Bearer ${apiKey}` },
      body    : {
        inputs     : prompt.user,
        parameters : { max_length: 100, num_return_sequences: 1, temperature: 0.7 },
      },
    }),
    transformResponse: res => ({ text: res[0].generated_text }),
  },
});
```

| Function           | Type                                                                      | Purpose                                                  |
|--------------------|---------------------------------------------------------------------------|----------------------------------------------------------|
| `config`           | `(apiKey, prompt) => { endpoint, body?, headers? }`                       | Build request.                                           |
| `transformResponse`| `(response) => { text: string \| null }`                                  | Extract model output.                                    |

---

## Completion Request Options <a id="completion-request-options"></a>

### Custom Headers for AI Model Requests <a id="custom-headers-for-ai-model-requests"></a>

```ts
copilot.complete({
  options: {
    headers: { 'X-Custom-Header': 'custom-value' },
  },
});
```

---

### Custom Prompt <a id="custom-prompt"></a>

```ts
copilot.complete({
  options: {
    customPrompt: meta => ({
      system: 'You are an AI assistant specialized in React components.',
      user  : 'Please complete the following code…',
    }),
  },
});
```

#### Completion Metadata (partial)

| Property        | Type                                      | Description                                           |
|-----------------|-------------------------------------------|-------------------------------------------------------|
| language        | string                                    | Editor language.                                      |
| cursorPosition  | `{ lineNumber: number; column: number }`  | Current cursor.                                       |
| filename        | string \| undefined                       | Provided via `filename` option.                       |
| technologies    | string[] \| undefined                     | Provided via `technologies` option.                   |
| textBeforeCursor| string                                    | Code before cursor.                                   |
| textAfterCursor | string                                    | Code after cursor.                                    |
| editorState     | `{ completionMode: 'insert' \| 'complete' \| 'continue' }` | Context mode. |

Example React-focused prompt:

```ts
const customPrompt = ({ textBeforeCursor, textAfterCursor }) => ({
  system: 'You are an AI assistant specialized in React components.',
  user  : `Complete this React component:
${textBeforeCursor}
// Cursor
${textAfterCursor}
Use modern practices, hooks, and TypeScript where appropriate.
Return **only** the completed code.`,
});
```

---

## Cross-Language API Handler Implementation <a id="cross-language-api-handler-implementation"></a>

Even though examples use Node.js, you can implement the `/complete` endpoint in any language.

### Example: Python + FastAPI

```py
from fastapi import FastAPI, Request

app = FastAPI()

@app.post('/complete')
async def handle_completion(request: Request):
    try:
        body     = await request.json()
        metadata = body['completionMetadata']

        prompt = f"""Please complete the following {metadata['language']} code:
{metadata['textBeforeCursor']}
<cursor>
{metadata['textAfterCursor']}
Use modern {metadata['language']} practices and hooks where appropriate.
Return only the completed part of the code without comments."""

        # TODO: Send `prompt` to your model and obtain `response`
        response = "Your model's response here"

        return { 'completion': response, 'error': None }
    except Exception as e:
        return { 'completion': None, 'error': str(e) }
```

```ts
registerCompletion(monaco, editor, {
  endpoint: 'https://my-python-api.com/complete',
});
```

---

---
title: Custom Model
---

# Custom Model

You can use a custom LLM that isn't built into Monacopilot by setting up a `model` when you create a new CompletionCopilot. This feature lets you connect to LLMs from other services or your own custom-built models.

## Example

```javascript
const copilot = new CompletionCopilot(undefined, {
    // You don't need to set the provider if you are using a custom model.
    // provider: "openai",
    model: async prompt => {
        const response = await fetch(
            'https://api.openai.com/v1/chat/completions',
            {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    model: 'gpt-4o',
                    messages: [
                        {role: 'system', content: prompt.context},
                        {
                            role: 'user',
                            content: `${prompt.instruction}\n\n${prompt.fileContent}`,
                        },
                    ],
                    temperature: 0.2,
                    max_tokens: 256,
                }),
            },
        );

        const data = await response.json();

        return {
            text: data.choices[0].message.content,
        };
    },
});
```

## Implementation

The `model` option accepts an async function with the following signature:

```typescript
type CustomCopilotModel = (prompt: PromptData) => Promise<CustomModelResponse>;

type CustomModelResponse = {
    /** The generated text content, or null if no text was generated */
    text: string | null;
};
```

### Prompt Data Structure

The `prompt` parameter passed to the model function has the following structure:

```typescript
interface PromptData {
    /**
     * Contextual information about the code environment
     * @example filename, technologies, etc.
     */
    context: string;

    /**
     * Instructions for the AI model on how to generate the completion
     */
    instruction: string;

    /**
     * The content of the file being edited
     */
    fileContent: string;
}
```

## Model Accuracy Considerations

When using a custom model, the accuracy of completions becomes your responsibility. Monacopilot's built-in models like Codestral support Fill-in-the-Middle (FIM) capabilities, which significantly enhances completion accuracy by understanding both the prefix and suffix context.

If your custom model doesn't support FIM, you may need to:

- Improve the prompt engineering to compensate
- Use a higher-quality model

For best results, consider using code-optimized models when available.

## Editor Integration Options

When registering your completion with Monaco editor, there are some options especially relevant for custom models:

```javascript
registerCompletion(editor, {
    // Disable follow-up completions for general-purpose models
    allowFollowUpCompletions: false,
    // other options...
});
```

### <code>[allowFollowUpCompletions](/configuration/register-options.html#follow-up-completions)</code>

This option controls whether new follow-up completions are automatically triggered after accepting a completion. Set it to `false` when:

- Using general-purpose models like GPT-4o
- Working with models that don't have FIM capabilities
- Experiencing poor quality follow-up suggestions

Leave it enabled (`true`) when:

- Using custom models that have FIM capabilities
- Working with code-completion-optimized models

## Client SDKs Example

You can use client SDKs for various AI providers to simplify integration with your custom model. The following example demonstrates how to use the Anthropic SDK to connect Claude models to Monacopilot.

```javascript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
    apiKey: process.env.ANTHROPIC_API_KEY,
});

const copilot = new CompletionCopilot(undefined, {
    model: async prompt => {
        const completion = await anthropic.messages.create({
            model: 'claude-3-5-haiku-latest',
            max_tokens: 1024,
            messages: [
                {role: 'system', content: prompt.context},
                {
                    role: 'user',
                    content: `${prompt.instruction}\n\n${prompt.fileContent}`,
                },
            ],
            temperature: 0.1,
        });

        return {
            text: completion.content[0].text,
        };
    },
});
```

## Working with Different Models

When working with different models, you'll need to format the prompt data appropriately for your specific model:

- For chat-based models (OpenAI, Anthropic, etc.):

    ```javascript
    // OpenAI format
    messages: [
        {role: 'system', content: prompt.context},
        {
            role: 'user',
            content: `${prompt.instruction}\n\n${prompt.fileContent}`,
        },
    ];

    // Anthropic format
    system: prompt.context,
    messages: [
        {
            role: 'user',
            content: `${prompt.instruction}\n\n${prompt.fileContent}`,
        },
    ];
    ```

- For completion-based models:
    ```javascript
    // Single prompt format
    prompt: `Context: ${prompt.context}\nFile: ${prompt.fileContent}\nTask: ${prompt.instruction}`;
    ```

## Contributing

See the [contributing guide](https://github.com/arshad-yaseen/monacopilot/blob/main/CONTRIBUTING.md).
We welcome community contributions to make **Monacopilot** even better. ❤️
