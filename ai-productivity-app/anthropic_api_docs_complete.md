# Anthropic API Documentation

*Complete API documentation compiled from docs.anthropic.com*

## Table of Contents

### Overview

- [Overview](#overview)

### Authentication & Setup

- [Client SDKs](#client-sdks)
- [Getting help](#getting-help)
- [OpenAI SDK compatibility](#openai-sdk-compatibility)

### Messages API

- [Cancel a Message Batch](#cancel-a-message-batch)
- [Create a Text Completion](#create-a-text-completion)
- [Create a Message Batch](#create-a-message-batch)
- [Delete a Message Batch](#delete-a-message-batch)
- [List Message Batches](#list-message-batches)
- [Messages](#messages)
- [Message Batches examples](#message-batches-examples)
- [Count Message tokens](#count-message-tokens)
- [Messages examples](#messages-examples)
- [Streaming Messages](#streaming-messages)
- [Migrating from Text Completions](#migrating-from-text-completions)
- [Retrieve Message Batch Results](#retrieve-message-batch-results)
- [Retrieve a Message Batch](#retrieve-a-message-batch)
- [Streaming Text Completions](#streaming-text-completions)

### Models

- [Get a Model](#get-a-model)
- [List Models](#list-models)

### Files

- [Download a File](#download-a-file)
- [Create a File](#create-a-file)
- [Delete a File](#delete-a-file)
- [List Files](#list-files)
- [Get File Metadata](#get-file-metadata)

### Administration

- [Get User](#get-user)
- [Get Invite](#get-invite)
- [List Users](#list-users)
- [Remove User](#remove-user)
- [Update User](#update-user)
- [Using the Admin](#using-the-admin)

### Advanced Features

- [Beta headers](#beta-headers)
- [Generate a prompt](#generate-a-prompt)
- [Improve a prompt](#improve-a-prompt)
- [Templatize a prompt](#templatize-a-prompt)
- [Prompt validation](#prompt-validation)
- [Versions](#versions)

### Integration Guides

- [Amazon Bedrock](#amazon-bedrock)
- [Vertex AI](#vertex-ai)

### Reference

- [Errors](#errors)
- [Handling stop reasons](#handling-stop-reasons)
- [IP addresses](#ip-addresses)
- [Rate limits](#rate-limits)
- [Service tiers](#service-tiers)
- [Supported Regions](#supported-regions)


---

# Overview

## Overview

*Source: https://docs.anthropic.com/en/api/getting-started*

##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
Accessing the API
The API is made available via our web [Console](https://console.anthropic.com/). You can use the [Workbench](https://console.anthropic.com/workbench/3b57d80a-99f2-4760-8316-d3bb14fbfb1e) to try out the API in the browser and then generate API keys in [Account Settings](https://console.anthropic.com/account/keys). Use [workspaces](https://console.anthropic.com/settings/workspaces) to segment your API keys and [control spend](/en/api/rate-limits) by use case.
All requests to the Anthropic API must include an `x-api-key` header with your API key. If you are using the Client SDKs, you will set the API when constructing a client, and then the SDK will send the header on your behalf with every request. If integrating directly with the API, you’ll need to send this header yourself.
Content types
The Anthropic API always accepts JSON in request bodies and returns JSON in response bodies. You will need to send the `content-type: application/json` header in requests. If you are using the Client SDKs, this will be taken care of automatically.
Response Headers
The Anthropic API includes the following headers in every response:
* `request-id`: A globally unique identifier for the request.
* `anthropic-organization-id`: The organization ID associated with the API key used in the request.
* curl
* Python
* TypeScript
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, world"}
]
}'
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, world"}
]
}'
Install via PyPI:
pip install anthropic
import anthropic
client = anthropic.Anthropic(
# defaults to os.environ.get("ANTHROPIC_API_KEY")
api_key="my_api_key",
)
message = client.messages.create(
model="claude-opus-4-20250514",
max_tokens=1024,
messages=[
{"role": "user", "content": "Hello, Claude"}
]
)
print(message.content)
Install via npm:
npm install @anthropic-ai/sdk
TypeScript
import Anthropic from '@anthropic-ai/sdk';
const anthropic = new Anthropic({
apiKey: 'my_api_key', // defaults to process.env["ANTHROPIC_API_KEY"]
});
const msg = await anthropic.messages.create({
model: "claude-opus-4-20250514",
max_tokens: 1024,
messages: [{ role: "user", content: "Hello, Claude" }],
});
console.log(msg);

---

# Authentication & Setup

## Client SDKs

*Source: https://docs.anthropic.com/en/api/client-sdks*

Client SDKs
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
> Additional configuration is needed to use Anthropic’s Client SDKs through a partner platform. If you are using Amazon Bedrock, see [this guide](/en/api/claude-on-amazon-bedrock); if you are using Google Cloud Vertex AI, see [this guide](/en/api/claude-on-vertex-ai).
Example:
import anthropic
client = anthropic.Anthropic(
# defaults to os.environ.get("ANTHROPIC_API_KEY")
api_key="my_api_key",
)
message = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
messages=[
{"role": "user", "content": "Hello, Claude"}
]
)
print(message.content)
Accepted `model` strings:
# Claude 4 Models
"claude-opus-4-20250514"
"claude-opus-4-0" # alias
"claude-sonnet-4-20250514"
"claude-sonnet-4-0" # alias
# Claude 3.7 Models
"claude-3-7-sonnet-20250219"
"claude-3-7-sonnet-latest" # alias
# Claude 3.5 Models
"claude-3-5-haiku-20241022"
"claude-3-5-haiku-latest" # alias
"claude-3-5-sonnet-20241022"
"claude-3-5-sonnet-latest" # alias
"claude-3-5-sonnet-20240620" # previous version
# Claude 3 Models
"claude-3-opus-20240229"
"claude-3-opus-latest" # alias
"claude-3-sonnet-20240229"
"claude-3-haiku-20240307"
TypeScript
While this library is in TypeScript, it can also be used in JavaScript libraries.
Example:
TypeScript
import Anthropic from '@anthropic-ai/sdk';
const anthropic = new Anthropic({
apiKey: 'my_api_key', // defaults to process.env["ANTHROPIC_API_KEY"]
});
const msg = await anthropic.messages.create({
model: "claude-sonnet-4-20250514",
max_tokens: 1024,
messages: [{ role: "user", content: "Hello, Claude" }],
});
console.log(msg);
Accepted `model` strings:
// Claude 4 Models
"claude-opus-4-20250514"
"claude-opus-4-0" // alias
"claude-sonnet-4-20250514"
"claude-sonnet-4-0" // alias
// Claude 3.7 Models
"claude-3-7-sonnet-20250219"
"claude-3-7-sonnet-latest" // alias
// Claude 3.5 Models
"claude-3-5-haiku-20241022"
"claude-3-5-haiku-latest" // alias
"claude-3-5-sonnet-20241022"
"claude-3-5-sonnet-latest" // alias
"claude-3-5-sonnet-20240620" // previous version
// Claude 3 Models
"claude-3-opus-20240229"
"claude-3-opus-latest" // alias
"claude-3-sonnet-20240229"
"claude-3-haiku-20240307"
Example:
import com.anthropic.models.Message;
import com.anthropic.models.MessageCreateParams;
import com.anthropic.models.Model;
MessageCreateParams params = MessageCreateParams.builder()
.maxTokens(1024L)
.addUserMessage("Hello, Claude")
.model(Model.CLAUDE_SONNET_4_0)
.build();
Message message = client.messages().create(params);
`model` enum values:
// Claude 4 Models
Model.CLAUDE_OPUS_4_0
Model.CLAUDE_OPUS_4_20250514
Model.CLAUDE_SONNET_4_0
Model.CLAUDE_SONNET_4_20250514
// Claude 3.7 Models
Model.CLAUDE_3_7_SONNET_LATEST
Model.CLAUDE_3_7_SONNET_20250219
// Claude 3.5 Models
Model.CLAUDE_3_5_HAIKU_LATEST
Model.CLAUDE_3_5_HAIKU_20241022
Model.CLAUDE_3_5_SONNET_LATEST
Model.CLAUDE_3_5_SONNET_20241022
Model.CLAUDE_3_5_SONNET_20240620
// Claude 3 Models
Model.CLAUDE_3_OPUS_LATEST
Model.CLAUDE_3_OPUS_20240229
Model.CLAUDE_3_SONNET_20240229
Model.CLAUDE_3_HAIKU_20240307
Example:
package main
import (
"context"
"fmt"
"github.com/anthropics/anthropic-sdk-go"
"github.com/anthropics/anthropic-sdk-go/option"
)
func main() {
client := anthropic.NewClient(
option.WithAPIKey("my-anthropic-api-key"),
)
message, err := client.Messages.New(context.TODO(), anthropic.MessageNewParams{
Model: anthropic.F(anthropic.ModelClaudeSonnet4_0),
MaxTokens: anthropic.F(int64(1024)),
Messages: anthropic.F([]anthropic.MessageParam{
anthropic.NewUserMessage(anthropic.NewTextBlock("What is a quaternion?")),
}),
})
if err != nil {
panic(err.Error())
}
fmt.Printf("%+v\n", message.Content)
}
`Model` constants:
// Claude 4 Models
anthropic.ModelClaudeOpus4_0
anthropic.ModelClaudeOpus4_20250514
anthropic.ModelClaudeSonnet4_0
anthropic.ModelClaudeSonnet4_20250514
// Claude 3.7 Models
anthropic.ModelClaude3_7SonnetLatest
anthropic.ModelClaude3_7Sonnet20250219
// Claude 3.5 Models
anthropic.ModelClaude3_5HaikuLatest
anthropic.ModelClaude3_5Haiku20241022
anthropic.ModelClaude3_5SonnetLatest
anthropic.ModelClaude3_5Sonnet20241022
anthropic.ModelClaude_3_5_Sonnet_20240620
// Claude 3 Models
anthropic.ModelClaude3OpusLatest
anthropic.ModelClaude_3_Opus_20240229
anthropic.ModelClaude_3_Sonnet_20240229
anthropic.ModelClaude_3_Haiku_20240307
Example:
ruby
require "bundler/setup"
require "anthropic"
anthropic = Anthropic::Client.new(
api_key: "my_api_key" # defaults to ENV["ANTHROPIC_API_KEY"]
)
message =
anthropic.messages.create(
max_tokens: 1024,
messages: [{
role: "user",
content: "Hello, Claude"
}],
model: "claude-sonnet-4-20250514"
)
puts(message.content)
Accepted `model` strings:
# Claude 4 Models
:"claude-opus-4-20250514"
:"claude-opus-4-0" # alias
:"claude-sonnet-4-20250514"
:"claude-sonnet-4-0" # alias
# Claude 3.7 Models
:"claude-3-7-sonnet-20250219"
:"claude-3-7-sonnet-latest" # alias
# Claude 3.5 Models
:"claude-3-5-haiku-20241022"
:"claude-3-5-haiku-latest" # alias
:"claude-3-5-sonnet-20241022"
:"claude-3-5-sonnet-latest" # alias
:"claude-3-5-sonnet-20240620" # previous version
# Claude 3 Models
:"claude-3-opus-20240229"
:"claude-3-opus-latest" # alias
:"claude-3-sonnet-20240229"
:"claude-3-haiku-20240307"
Beta namespace in client SDKs
Every SDK has a `beta` namespace that is available. This is used for new features Anthropic releases in a beta version. Use this in conjunction with [beta headers](/en/api/beta-headers) to use these features.
import anthropic
client = anthropic.Anthropic(
# defaults to os.environ.get("ANTHROPIC_API_KEY")
api_key="my_api_key",
)
message = client.beta.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
messages=[
{"role": "user", "content": "Hello, Claude"}
],
betas=["beta-feature-name"]
)
print(message.content)
[Prompt validation](/en/api/prompt-validation)[OpenAI SDK compatibility](/en/api/openai-sdk)

## Getting help

*Source: https://docs.anthropic.com/en/api/getting-help*

Getting help
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
We monitor the following inboxes:
* [privacy@anthropic.com](mailto:privacy@anthropic.com) to exercise your data access, portability, deletion, or correction rights per our [Privacy Policy](https://www.anthropic.com/privacy)
* [usersafety@anthropic.com](mailto:usersafety@anthropic.com) to report any erroneous, biased, or even offensive responses from Claude, so we can continue to learn and make improvements to ensure our model is safe, fair and beneficial to all

## OpenAI SDK compatibility

*Source: https://docs.anthropic.com/en/api/openai-sdk*

OpenAI SDK compatibility
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
This compatibility layer is primarily intended to test and compare model capabilities, and is not considered a long-term or production-ready solution for most use cases. While we do intend to keep it fully functional and not make breaking changes, our priority is the reliability and effectiveness of the [Anthropic API](/en/api/overview).
For more information on known compatibility limitations, see [Important OpenAI compatibility limitations](/_sites/docs.anthropic.com/en/api/openai-sdk#important-openai-compatibility-limitations).
If you encounter any issues with the OpenAI SDK compatibility feature, please let us know .
For the best experience and access to Anthropic API full feature set ([PDF processing](/en/docs/build-with-claude/pdf-support), [citations](/en/docs/build-with-claude/citations), [extended thinking](/en/docs/build-with-claude/extended-thinking), and [prompt caching](/en/docs/build-with-claude/prompt-caching)), we recommend using the native [Anthropic API](/en/api/getting-started).
Getting started with the OpenAI SDK
To use the OpenAI SDK compatibility feature, you’ll need to:
1. Use an official OpenAI SDK
2. Change the following
* Update your base URL to point to Anthropic’s API
* Replace your API key with an [Anthropic API key](https://console.anthropic.com/settings/keys)
* Update your model name to use a [Claude model](/en/docs/about-claude/models#model-names)
###
Quick start example
from openai import OpenAI
client = OpenAI(
api_key="ANTHROPIC_API_KEY", # Your Anthropic API key
base_url="https://api.anthropic.com/v1/" # Anthropic's API endpoint
)
response = client.chat.completions.create(
model="claude-opus-4-20250514", # Anthropic model name
messages=[
{"role": "system", "content": "You are a helpful assistant."},
{"role": "user", "content": "Who are you?"}
],
)
print(response.choices[0].message.content)
Important OpenAI compatibility limitations
####
API behavior
Here are the most substantial differences from using OpenAI:
* The `strict` parameter for function calling is ignored, which means the tool use JSON is not guaranteed to follow the supplied schema.
####
Output quality considerations
If you’ve done lots of tweaking to your prompt, it’s likely to be well-tuned to OpenAI specifically. Consider using our [prompt improver in the Anthropic Console](https://console.anthropic.com/dashboard) as a good starting point.
####
System / Developer message hoisting
####
You can enable [extended thinking](/en/docs/build-with-claude/extended-thinking) capabilities by adding the `thinking` parameter. While this will improve Claude’s reasoning for complex tasks, the OpenAI SDK won’t return Claude’s detailed thought process. For full extended thinking features, including access to Claude’s step-by-step reasoning output, use the native Anthropic API.
response = client.chat.completions.create(
model="claude-opus-4-20250514",
messages=...,
extra_body={
"thinking": { "type": "enabled", "budget_tokens": 2000 }
}
)
Rate limits
Rate limits follow Anthropic’s [standard limits](/en/api/rate-limits) for the `/v1/messages` endpoint.
###
Request fields
####
Simple fields
`model`| Use Claude model names
`max_tokens`
`max_completion_tokens`
`stream`
`stream_options`
`top_p`
`parallel_tool_calls`
`stop`| All non-whitespace stop sequences work
`temperature`| Between 0 and 1 (inclusive). Values greater than 1 are capped at 1.
`n`| Must be exactly 1
`logprobs`| Ignored
`metadata`| Ignored
`response_format`| Ignored
`prediction`| Ignored
`presence_penalty`| Ignored
`frequency_penalty`| Ignored
`seed`| Ignored
`service_tier`| Ignored
`audio`| Ignored
`logit_bias`| Ignored
`store`| Ignored
`user`| Ignored
`modalities`| Ignored
`top_logprobs`| Ignored
`reasoning_effort`| Ignored
####
`tools` / `functions` fields
Show fields
* Tools
* Functions
`tools[n].function` fields
`name`
`description`
`parameters`
`strict`| Ignored
`tools[n].function` fields
`name`
`description`
`parameters`
`strict`| Ignored
`functions[n]` fields
OpenAI has deprecated the `functions` field and suggests using `tools` instead.
`name`
`description`
`parameters`
`strict`| Ignored
####
`messages` array fields
Show fields
* Developer role
* System role
* User role
* Assistant role
* Tool role
* Function role
Fields for `messages[n].role == "developer"`
Developer messages are hoisted to beginning of conversation as part of the initial system message
`content`
`name`| Ignored
Fields for `messages[n].role == "developer"`
Developer messages are hoisted to beginning of conversation as part of the initial system message
`content`
`name`| Ignored
Fields for `messages[n].role == "system"`
System messages are hoisted to beginning of conversation as part of the initial system message
`content`
`name`| Ignored
Fields for `messages[n].role == "user"`
Field| Variant| Sub-field
---|---|---
`content`| `string`|
| `array`, `type == "text"`|
| `array`, `type == "image_url"`| `url`
| | `detail`| Ignored
| `array`, `type == "input_audio"`| | Ignored
| `array`, `type == "file"`| | Ignored
`name`| | | Ignored
Fields for `messages[n].role == "assistant"`
Field| Variant
---|---
`content`| `string`
| `array`, `type == "text"`
| `array`, `type == "refusal"`| Ignored
`tool_calls`|
`function_call`|
`audio`| | Ignored
`refusal`| | Ignored
Fields for `messages[n].role == "tool"`
Field| Variant
---|---
`content`| `string`
| `array`, `type == "text"`
`tool_call_id`|
`tool_choice`|
`name`| | Ignored
Fields for `messages[n].role == "function"`
Field| Variant
---|---
`content`| `string`
| `array`, `type == "text"`
`tool_choice`|
`name`| | Ignored
###
Response fields
`id`
`choices[]`| Will always have a length of 1
`choices[].finish_reason`
`choices[].index`
`choices[].message.role`
`choices[].message.content`
`choices[].message.tool_calls`
`object`
`created`
`model`
`finish_reason`
`content`
`usage.completion_tokens`
`usage.prompt_tokens`
`usage.total_tokens`
`usage.completion_tokens_details`| Always empty
`usage.prompt_tokens_details`| Always empty
`choices[].message.refusal`| Always empty
`choices[].message.audio`| Always empty
`logprobs`| Always empty
`service_tier`| Always empty
`system_fingerprint`| Always empty
###
Error message compatibility
The compatibility layer maintains consistent error formats with the OpenAI API. However, the detailed error messages will not be equivalent. We recommend only using the error messages for logging and debugging.
###
Header compatibility
`x-ratelimit-limit-requests`
`x-ratelimit-limit-tokens`
`x-ratelimit-remaining-requests`
`x-ratelimit-remaining-tokens`
`x-ratelimit-reset-requests`
`x-ratelimit-reset-tokens`
`retry-after`
`request-id`
`openai-version`| Always `2020-10-01`
`authorization`
`openai-processing-ms`| Always empty
[Client SDKs](/en/api/client-sdks)[Messages examples](/en/api/messages-examples)

---

# Messages API

## Cancel a Message Batch

*Source: https://docs.anthropic.com/en/api/canceling-message-batches*

Message Batches
Cancel a Message Batch
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
messages
/
batches
/
{message_batch_id}
/
cancel
curl --request POST https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d/cancel \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Path Parameters
message_batch_id
string
required
ID of the Message Batch.
#### Response
200
2004XX
application/json
Successful Response
archived_at
string | null
required
RFC 3339 datetime string representing the time at which the Message Batch was archived and its results became unavailable.
Examples:
`"2024-08-20T18:37:24.100435Z"`
cancel_initiated_at
string | null
required
RFC 3339 datetime string representing the time at which cancellation was initiated for the Message Batch. Specified only if cancellation was initiated.
Examples:
`"2024-08-20T18:37:24.100435Z"`
created_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch was created.
Examples:
`"2024-08-20T18:37:24.100435Z"`
ended_at
string | null
required
RFC 3339 datetime string representing the time at which processing for the Message Batch ended. Specified only once processing ends.
Processing ends when every request in a Message Batch has either succeeded, errored, canceled, or expired.
Examples:
`"2024-08-20T18:37:24.100435Z"`
expires_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch will expire and end processing, which is 24 hours after creation.
Examples:
`"2024-08-20T18:37:24.100435Z"`
id
string
required
Unique object identifier.
The format and length of IDs may change over time.
Examples:
`"msgbatch_013Zva2CMHLNnXjNJJKqJ2EF"`
processing_status
enum<string>
required
Processing status of the Message Batch.
Available options:
`in_progress`,
`canceling`,
`ended`
request_counts
object
required
Tallies requests within the Message Batch, categorized by their status.
Requests start as `processing` and move to one of the other statuses only once processing of the entire batch ends. The sum of all values always matches the total number of requests in the batch.
Show child attributes
request_counts.canceled
integer
default:0
required
Number of requests in the Message Batch that have been canceled.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
request_counts.errored
integer
default:0
required
Number of requests in the Message Batch that encountered an error.
This is zero until processing of the entire Message Batch has ended.
Examples:
`30`
request_counts.expired
integer
default:0
required
Number of requests in the Message Batch that have expired.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
request_counts.processing
integer
default:0
required
Number of requests in the Message Batch that are processing.
Examples:
`100`
request_counts.succeeded
integer
default:0
required
Number of requests in the Message Batch that have completed successfully.
This is zero until processing of the entire Message Batch has ended.
Examples:
`50`
results_url
string | null
required
URL to a `.jsonl` file containing the results of the Message Batch requests. Specified only once processing ends.
Results in the file are not guaranteed to be in the same order as requests. Use the `custom_id` field to match results to requests.
Examples:
`"https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results"`
type
enum<string>
default:message_batch
required
Object type.
For Message Batches, this is always `"message_batch"`.
Available options:
`message_batch`
[List Message Batches](/en/api/listing-message-batches)[Delete a Message Batch](/en/api/deleting-message-batches)
curl --request POST https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d/cancel \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}

## Create a Text Completion

*Source: https://docs.anthropic.com/en/api/complete*

Text Completions (Legacy)
Create a Text Completion
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
complete
curl https://api.anthropic.com/v1/complete \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-2.1",
"max_tokens_to_sample": 1024,
"prompt": "\n\nHuman: Hello, Claude\n\nAssistant:"
}'
{
"completion": " Hello! My name is Claude.",
"id": "compl_018CKm6gsux7P8yMcwZbeCPw",
"model": "claude-2.1",
"stop_reason": "stop_sequence",
"type": "completion"
}
#### Headers
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
#### Body
application/json
model
string
required
The model that will complete your prompt.
See [models](https://docs.anthropic.com/en/docs/models-overview) for additional details and options.
Examples:
`"claude-2.1"`
prompt
string
required
The prompt that you want Claude to complete.
For proper response generation you will need to format your prompt using alternating `\n\nHuman:` and `\n\nAssistant:` conversational turns. For example:
"\n\nHuman: {userQuestion}\n\nAssistant:"
See [prompt validation](https://docs.anthropic.com/en/api/prompt-validation) and our guide to [prompt design](https://docs.anthropic.com/en/docs/intro-to-prompting) for more details.
Minimum length: `1`
Examples:
`"\n\nHuman: Hello, world!\n\nAssistant:"`
max_tokens_to_sample
integer
required
The maximum number of tokens to generate before stopping.
Note that our models may stop _before_ reaching this maximum. This parameter only specifies the absolute maximum number of tokens to generate.
Required range: `x >= 1`
Examples:
`256`
stop_sequences
string[]
Sequences that will cause the model to stop generating.
Our models stop on `"\n\nHuman:"`, and may include additional built-in stop sequences in the future. By providing the stop_sequences parameter, you may include additional strings that will cause the model to stop generating.
temperature
number
Amount of randomness injected into the response.
Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0` for analytical / multiple choice, and closer to `1.0` for creative and generative tasks.
Note that even with `temperature` of `0.0`, the results will not be fully deterministic.
Required range: `0 <= x <= 1`
Examples:
`1`
top_p
number
Use nucleus sampling.
In nucleus sampling, we compute the cumulative distribution over all the options for each subsequent token in decreasing probability order and cut it off once it reaches a particular probability specified by `top_p`. You should either alter `temperature` or `top_p`, but not both.
Recommended for advanced use cases only. You usually only need to use `temperature`.
Required range: `0 <= x <= 1`
Examples:
`0.7`
top_k
integer
Only sample from the top K options for each subsequent token.
Used to remove "long tail" low probability responses. .
Recommended for advanced use cases only. You usually only need to use `temperature`.
Required range: `x >= 0`
Examples:
`5`
metadata
object
An object describing metadata about the request.
Show child attributes
metadata.user_id
string | null
An external identifier for the user who is associated with the request.
This should be a uuid, hash value, or other opaque identifier. Anthropic may use this id to help detect abuse. Do not include any identifying information such as name, email address, or phone number.
Maximum length: `256`
Examples:
`"13803d75-b4b5-4c3e-b2a2-6f21399b021b"`
stream
boolean
Whether to incrementally stream the response using server-sent events.
See [streaming](https://docs.anthropic.com/en/api/streaming) for details.
#### Response
200
2004XX
application/json
Text Completion object.
completion
string
required
The resulting completion up to and excluding the stop sequences.
Examples:
`" Hello! My name is Claude."`
id
string
required
Unique object identifier.
The format and length of IDs may change over time.
model
string
required
The model that handled the request.
Examples:
`"claude-2.1"`
stop_reason
string | null
required
The reason that we stopped.
This may be one the following values:
* `"stop_sequence"`: we reached a stop sequence — either provided by you via the `stop_sequences` parameter, or a stop sequence built into the model
* `"max_tokens"`: we exceeded `max_tokens_to_sample` or the model's maximum
Examples:
`"stop_sequence"`
type
enum<string>
default:completion
required
Object type.
For Text Completions, this is always `"completion"`.
Available options:
`completion`
[Migrating from Text Completions](/en/api/migrating-from-text-completions-to-messages)[Streaming Text Completions](/en/api/streaming)
curl https://api.anthropic.com/v1/complete \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-2.1",
"max_tokens_to_sample": 1024,
"prompt": "\n\nHuman: Hello, Claude\n\nAssistant:"
}'
{
"completion": " Hello! My name is Claude.",
"id": "compl_018CKm6gsux7P8yMcwZbeCPw",
"model": "claude-2.1",
"stop_reason": "stop_sequence",
"type": "completion"
}

## Create a Message Batch

*Source: https://docs.anthropic.com/en/api/creating-message-batches*

Message Batches
Create a Message Batch
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
messages
/
batches
curl https://api.anthropic.com/v1/messages/batches \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"requests": [
{
"custom_id": "my-first-request",
"params": {
"model": "claude-3-7-sonnet-20250219",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, world"}
]
}
},
{
"custom_id": "my-second-request",
"params": {
"model": "claude-3-7-sonnet-20250219",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hi again, friend"}
]
}
}
]
}'
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}
Batches may contain up to 100,000 requests and be up to 256 MB in total size.
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Body
application/json
requests
object[]
required
List of requests for prompt completion. Each is an individual request to create a Message.
Show child attributes
requests.custom_id
string
required
Developer-provided ID created for each request in a Message Batch. Useful for matching results to requests, as results may be given out of request order.
Must be unique for each request within the Message Batch.
Required string length: `1 - 64`
Examples:
`"my-custom-id-1"`
requests.params
object
required
Messages API creation parameters for the individual request.
Show child attributes
requests.params.model
string
required
The model that will complete your prompt.
See [models](https://docs.anthropic.com/en/docs/models-overview) for additional details and options.
Required string length: `1 - 256`
Examples:
`"claude-sonnet-4-20250514"`
requests.params.messages
object[]
required
Input messages.
Our models are trained to operate on alternating `user` and `assistant` conversational turns. When creating a new `Message`, you specify the prior conversational turns with the `messages` parameter, and the model then generates the next `Message` in the conversation. Consecutive `user` or `assistant` turns in your request will be combined into a single turn.
Each input message must be an object with a `role` and `content`. You can specify a single `user`-role message, or you can include multiple `user` and `assistant` messages.
If the final message uses the `assistant` role, the response content will continue immediately from the content in that message. This can be used to constrain part of the model's response.
Example with a single `user` message:
[{"role": "user", "content": "Hello, Claude"}]
Example with multiple conversational turns:
Example with a partially-filled response from Claude:
[
{"role": "user", "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"},
{"role": "assistant", "content": "The best answer is ("},
]
Each input message `content` may be either a single `string` or an array of content blocks, where each block has a specific `type`. Using a `string` for `content` is shorthand for an array of one content block of type `"text"`. The following input messages are equivalent:
{"role": "user", "content": "Hello, Claude"}
{"role": "user", "content": [{"type": "text", "text": "Hello, Claude"}]}
Starting with Claude 3 models, you can also send image content blocks:
{"role": "user", "content": [
{
"type": "image",
"source": {
"type": "base64",
"media_type": "image/jpeg",
"data": "/9j/4AAQSkZJRg...",
}
},
{"type": "text", "text": "What is in this image?"}
]}
See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for more input examples.
Note that if you want to include a [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use the top-level `system` parameter — there is no `"system"` role for input messages in the Messages API.
There is a limit of 100,000 messages in a single request.
Show child attributes
requests.params.messages.content
required
requests.params.messages.role
enum<string>
required
Available options:
`user`,
`assistant`
requests.params.max_tokens
integer
required
The maximum number of tokens to generate before stopping.
Note that our models may stop _before_ reaching this maximum. This parameter only specifies the absolute maximum number of tokens to generate.
Different models have different maximum values for this parameter. See [models](https://docs.anthropic.com/en/docs/models-overview) for details.
Required range: `x >= 1`
Examples:
`1024`
requests.params.container
string | null
Container identifier for reuse across requests.
requests.params.mcp_servers
object[]
MCP servers to be utilized in this request
Show child attributes
requests.params.mcp_servers.name
string
required
requests.params.mcp_servers.type
enum<string>
required
Available options:
`url`
requests.params.mcp_servers.url
string
required
requests.params.mcp_servers.authorization_token
string | null
requests.params.mcp_servers.tool_configuration
object | null
Show child attributes
requests.params.mcp_servers.tool_configuration.allowed_tools
string[] | null
requests.params.mcp_servers.tool_configuration.enabled
boolean | null
requests.params.metadata
object
An object describing metadata about the request.
Show child attributes
requests.params.metadata.user_id
string | null
An external identifier for the user who is associated with the request.
This should be a uuid, hash value, or other opaque identifier. Anthropic may use this id to help detect abuse. Do not include any identifying information such as name, email address, or phone number.
Maximum length: `256`
Examples:
`"13803d75-b4b5-4c3e-b2a2-6f21399b021b"`
requests.params.service_tier
enum<string>
Determines whether to use priority capacity (if available) or standard capacity for this request.
Anthropic offers different levels of service for your API requests. See [service-tiers](https://docs.anthropic.com/en/api/service-tiers) for details.
Available options:
`auto`,
`standard_only`
requests.params.stop_sequences
string[]
Custom text sequences that will cause the model to stop generating.
Our models will normally stop when they have naturally completed their turn, which will result in a response `stop_reason` of `"end_turn"`.
If you want the model to stop generating when it encounters custom strings of text, you can use the `stop_sequences` parameter. If the model encounters one of the custom sequences, the response `stop_reason` value will be `"stop_sequence"` and the response `stop_sequence` value will contain the matched stop sequence.
requests.params.stream
boolean
Whether to incrementally stream the response using server-sent events.
See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for details.
requests.params.system
System prompt.
A system prompt is a way of providing context and instructions to Claude, such as specifying a particular goal or role. See our [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).
Examples:
[
{
"text": "Today's date is 2024-06-01.",
"type": "text"
}
]
`"Today's date is 2023-01-01."`
requests.params.temperature
number
Amount of randomness injected into the response.
Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0` for analytical / multiple choice, and closer to `1.0` for creative and generative tasks.
Note that even with `temperature` of `0.0`, the results will not be fully deterministic.
Required range: `0 <= x <= 1`
Examples:
`1`
requests.params.thinking
object
Configuration for enabling Claude's extended thinking.
When enabled, responses include `thinking` content blocks showing Claude's thinking process before the final answer. Requires a minimum budget of 1,024 tokens and counts towards your `max_tokens` limit.
See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.
* Enabled
* Disabled
Show child attributes
requests.params.thinking.budget_tokens
integer
required
Determines how many tokens Claude can use for its internal reasoning process. Larger budgets can enable more thorough analysis for complex problems, improving response quality.
Must be ≥1024 and less than `max_tokens`.
See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.
Required range: `x >= 1024`
requests.params.thinking.type
enum<string>
required
Available options:
`enabled`
requests.params.tool_choice
object
How the model should use the provided tools. The model can use a specific tool, any available tool, decide by itself, or not use tools at all.
* Auto
* Any
* Tool
* None
Show child attributes
requests.params.tool_choice.type
enum<string>
required
Available options:
`auto`
requests.params.tool_choice.disable_parallel_tool_use
boolean
Whether to disable parallel tool use.
Defaults to `false`. If set to `true`, the model will output at most one tool use.
requests.params.tools
object[]
Definitions of tools that the model may use.
If you include `tools` in your API request, the model may return `tool_use` content blocks that represent the model's use of those tools. You can then run those tools using the tool input generated by the model and then optionally return results back to the model using `tool_result` content blocks.
Each tool definition includes:
* `name`: Name of the tool.
* `description`: Optional, but strongly-recommended description of the tool.
* `input_schema`: for the tool `input` shape that the model will produce in `tool_use` output content blocks.
For example, if you defined `tools` as:
[
{
"name": "get_stock_price",
"description": "Get the current stock price for a given ticker symbol.",
"input_schema": {
"type": "object",
"properties": {
"ticker": {
"type": "string",
"description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
}
},
"required": ["ticker"]
}
}
]
And then asked the model "What's the S&P 500 at today?", the model might produce `tool_use` content blocks in the response like this:
[
{
"type": "tool_use",
"id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
"name": "get_stock_price",
"input": { "ticker": "^GSPC" }
}
]
You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an input, and return the following back to the model in a subsequent `user` message:
[
{
"type": "tool_result",
"tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
"content": "259.75 USD"
}
]
Tools can be used for workflows that include running client-side tools and functions, or more generally whenever you want the model to produce a particular JSON structure of output.
See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.
* Custom tool
* Bash tool (2024-10-22)
* Bash tool (2025-01-24)
* Code execution tool (2025-05-22)
* Computer use tool (2024-01-22)
* Computer use tool (2025-01-24)
* Text editor tool (2024-10-22)
* Text editor tool (2025-01-24)
* Text editor tool (2025-04-29)
* Web search tool (2025-03-05)
Show child attributes
requests.params.tools.name
string
required
Name of the tool.
This is how the tool will be called by the model and in `tool_use` blocks.
Required string length: `1 - 128`
requests.params.tools.input_schema
object
required
for this tool's input.
This defines the shape of the `input` that your tool accepts and that the model will produce.
Show child attributes
requests.params.tools.input_schema.type
enum<string>
required
Available options:
`object`
requests.params.tools.input_schema.properties
object | null
requests.params.tools.input_schema.required
string[] | null
requests.params.tools.type
enum<string> | null
Available options:
`custom`
requests.params.tools.description
string
Description of what this tool does.
Tool descriptions should be as detailed as possible. The more information that the model has about what the tool is and how to use it, the better it will perform. You can use natural language descriptions to reinforce important aspects of the tool input JSON schema.
Examples:
`"Get the current weather in a given location"`
requests.params.tools.cache_control
object | null
Create a cache control breakpoint at this content block.
Show child attributes
requests.params.tools.cache_control.type
enum<string>
required
Available options:
`ephemeral`
requests.params.tools.cache_control.ttl
enum<string>
The time-to-live for the cache control breakpoint.
This may be one the following values:
* `5m`: 5 minutes
* `1h`: 1 hour
Defaults to `5m`.
Available options:
`5m`,
`1h`
Examples:
{
"description": "Get the current weather in a given location",
"input_schema": {
"properties": {
"location": {
"description": "The city and state, e.g. San Francisco, CA",
"type": "string"
},
"unit": {
"description": "Unit for the output - one of (celsius, fahrenheit)",
"type": "string"
}
},
"required": ["location"],
"type": "object"
},
"name": "get_weather"
}
requests.params.top_k
integer
Only sample from the top K options for each subsequent token.
Used to remove "long tail" low probability responses. .
Recommended for advanced use cases only. You usually only need to use `temperature`.
Required range: `x >= 0`
Examples:
`5`
requests.params.top_p
number
Use nucleus sampling.
In nucleus sampling, we compute the cumulative distribution over all the options for each subsequent token in decreasing probability order and cut it off once it reaches a particular probability specified by `top_p`. You should either alter `temperature` or `top_p`, but not both.
Recommended for advanced use cases only. You usually only need to use `temperature`.
Required range: `0 <= x <= 1`
Examples:
`0.7`
Example:
{
"max_tokens": 1024,
"messages": [
{ "content": "Hello, world", "role": "user" }
],
"model": "claude-sonnet-4-20250514"
}
#### Response
200
2004XX
application/json
Successful Response
archived_at
string | null
required
RFC 3339 datetime string representing the time at which the Message Batch was archived and its results became unavailable.
Examples:
`"2024-08-20T18:37:24.100435Z"`
cancel_initiated_at
string | null
required
RFC 3339 datetime string representing the time at which cancellation was initiated for the Message Batch. Specified only if cancellation was initiated.
Examples:
`"2024-08-20T18:37:24.100435Z"`
created_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch was created.
Examples:
`"2024-08-20T18:37:24.100435Z"`
ended_at
string | null
required
RFC 3339 datetime string representing the time at which processing for the Message Batch ended. Specified only once processing ends.
Processing ends when every request in a Message Batch has either succeeded, errored, canceled, or expired.
Examples:
`"2024-08-20T18:37:24.100435Z"`
expires_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch will expire and end processing, which is 24 hours after creation.
Examples:
`"2024-08-20T18:37:24.100435Z"`
id
string
required
Unique object identifier.
The format and length of IDs may change over time.
Examples:
`"msgbatch_013Zva2CMHLNnXjNJJKqJ2EF"`
processing_status
enum<string>
required
Processing status of the Message Batch.
Available options:
`in_progress`,
`canceling`,
`ended`
request_counts
object
required
Tallies requests within the Message Batch, categorized by their status.
Requests start as `processing` and move to one of the other statuses only once processing of the entire batch ends. The sum of all values always matches the total number of requests in the batch.
Show child attributes
request_counts.canceled
integer
default:0
required
Number of requests in the Message Batch that have been canceled.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
request_counts.errored
integer
default:0
required
Number of requests in the Message Batch that encountered an error.
This is zero until processing of the entire Message Batch has ended.
Examples:
`30`
request_counts.expired
integer
default:0
required
Number of requests in the Message Batch that have expired.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
request_counts.processing
integer
default:0
required
Number of requests in the Message Batch that are processing.
Examples:
`100`
request_counts.succeeded
integer
default:0
required
Number of requests in the Message Batch that have completed successfully.
This is zero until processing of the entire Message Batch has ended.
Examples:
`50`
results_url
string | null
required
URL to a `.jsonl` file containing the results of the Message Batch requests. Specified only once processing ends.
Results in the file are not guaranteed to be in the same order as requests. Use the `custom_id` field to match results to requests.
Examples:
`"https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results"`
type
enum<string>
default:message_batch
required
Object type.
For Message Batches, this is always `"message_batch"`.
Available options:
`message_batch`
[Get a Model](/en/api/models)[Retrieve a Message Batch](/en/api/retrieving-message-batches)
curl https://api.anthropic.com/v1/messages/batches \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"requests": [
{
"custom_id": "my-first-request",
"params": {
"model": "claude-3-7-sonnet-20250219",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, world"}
]
}
},
{
"custom_id": "my-second-request",
"params": {
"model": "claude-3-7-sonnet-20250219",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hi again, friend"}
]
}
}
]
}'
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}

## Delete a Message Batch

*Source: https://docs.anthropic.com/en/api/deleting-message-batches*

Message Batches
Delete a Message Batch
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
DELETE
/
v1
/
messages
/
batches
/
{message_batch_id}
curl -X DELETE https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"type": "message_batch_deleted"
}
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Path Parameters
message_batch_id
string
required
ID of the Message Batch.
#### Response
200
2004XX
application/json
Successful Response
id
string
required
ID of the Message Batch.
Examples:
`"msgbatch_013Zva2CMHLNnXjNJJKqJ2EF"`
type
enum<string>
default:message_batch_deleted
required
Deleted object type.
For Message Batches, this is always `"message_batch_deleted"`.
Available options:
`message_batch_deleted`
[Cancel a Message Batch](/en/api/canceling-message-batches)[Create a File](/en/api/files-create)
curl -X DELETE https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"type": "message_batch_deleted"
}

## List Message Batches

*Source: https://docs.anthropic.com/en/api/listing-message-batches*

Message Batches
List Message Batches
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
messages
/
batches
curl https://api.anthropic.com/v1/messages/batches \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"data": [
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}
],
"first_id": "<string>",
"has_more": true,
"last_id": "<string>"
}
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Query Parameters
before_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.
after_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.
limit
integer
default:20
Number of items to return per page.
Defaults to `20`. Ranges from `1` to `1000`.
Required range: `1 <= x <= 1000`
#### Response
200
2004XX
application/json
Successful Response
data
object[]
required
Show child attributes
data.archived_at
string | null
required
RFC 3339 datetime string representing the time at which the Message Batch was archived and its results became unavailable.
Examples:
`"2024-08-20T18:37:24.100435Z"`
data.cancel_initiated_at
string | null
required
RFC 3339 datetime string representing the time at which cancellation was initiated for the Message Batch. Specified only if cancellation was initiated.
Examples:
`"2024-08-20T18:37:24.100435Z"`
data.created_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch was created.
Examples:
`"2024-08-20T18:37:24.100435Z"`
data.ended_at
string | null
required
RFC 3339 datetime string representing the time at which processing for the Message Batch ended. Specified only once processing ends.
Processing ends when every request in a Message Batch has either succeeded, errored, canceled, or expired.
Examples:
`"2024-08-20T18:37:24.100435Z"`
data.expires_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch will expire and end processing, which is 24 hours after creation.
Examples:
`"2024-08-20T18:37:24.100435Z"`
data.id
string
required
Unique object identifier.
The format and length of IDs may change over time.
Examples:
`"msgbatch_013Zva2CMHLNnXjNJJKqJ2EF"`
data.processing_status
enum<string>
required
Processing status of the Message Batch.
Available options:
`in_progress`,
`canceling`,
`ended`
data.request_counts
object
required
Tallies requests within the Message Batch, categorized by their status.
Requests start as `processing` and move to one of the other statuses only once processing of the entire batch ends. The sum of all values always matches the total number of requests in the batch.
Show child attributes
data.request_counts.canceled
integer
default:0
required
Number of requests in the Message Batch that have been canceled.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
data.request_counts.errored
integer
default:0
required
Number of requests in the Message Batch that encountered an error.
This is zero until processing of the entire Message Batch has ended.
Examples:
`30`
data.request_counts.expired
integer
default:0
required
Number of requests in the Message Batch that have expired.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
data.request_counts.processing
integer
default:0
required
Number of requests in the Message Batch that are processing.
Examples:
`100`
data.request_counts.succeeded
integer
default:0
required
Number of requests in the Message Batch that have completed successfully.
This is zero until processing of the entire Message Batch has ended.
Examples:
`50`
data.results_url
string | null
required
URL to a `.jsonl` file containing the results of the Message Batch requests. Specified only once processing ends.
Results in the file are not guaranteed to be in the same order as requests. Use the `custom_id` field to match results to requests.
Examples:
`"https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results"`
data.type
enum<string>
default:message_batch
required
Object type.
For Message Batches, this is always `"message_batch"`.
Available options:
`message_batch`
first_id
string | null
required
First ID in the `data` list. Can be used as the `before_id` for the previous page.
has_more
boolean
required
Indicates if there are more results in the requested page direction.
last_id
string | null
required
Last ID in the `data` list. Can be used as the `after_id` for the next page.
[Retrieve Message Batch Results](/en/api/retrieving-message-batch-results)[Cancel a Message Batch](/en/api/canceling-message-batches)
curl https://api.anthropic.com/v1/messages/batches \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"data": [
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}
],
"first_id": "<string>",
"has_more": true,
"last_id": "<string>"
}

## Messages

*Source: https://docs.anthropic.com/en/api/messages*

##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
messages
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-sonnet-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, world"}
]
}'
{
"content": [
{
"text": "Hi! My name is Claude.",
"type": "text"
}
],
"id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
"model": "claude-sonnet-4-20250514",
"role": "assistant",
"stop_reason": "end_turn",
"stop_sequence": null,
"type": "message",
"usage": {
"input_tokens": 2095,
"output_tokens": 503
}
}
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Body
application/json
model
string
required
The model that will complete your prompt.
See [models](https://docs.anthropic.com/en/docs/models-overview) for additional details and options.
Required string length: `1 - 256`
Examples:
`"claude-sonnet-4-20250514"`
messages
object[]
required
Input messages.
Our models are trained to operate on alternating `user` and `assistant` conversational turns. When creating a new `Message`, you specify the prior conversational turns with the `messages` parameter, and the model then generates the next `Message` in the conversation. Consecutive `user` or `assistant` turns in your request will be combined into a single turn.
Each input message must be an object with a `role` and `content`. You can specify a single `user`-role message, or you can include multiple `user` and `assistant` messages.
If the final message uses the `assistant` role, the response content will continue immediately from the content in that message. This can be used to constrain part of the model's response.
Example with a single `user` message:
[{"role": "user", "content": "Hello, Claude"}]
Example with multiple conversational turns:
Example with a partially-filled response from Claude:
[
{"role": "user", "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"},
{"role": "assistant", "content": "The best answer is ("},
]
Each input message `content` may be either a single `string` or an array of content blocks, where each block has a specific `type`. Using a `string` for `content` is shorthand for an array of one content block of type `"text"`. The following input messages are equivalent:
{"role": "user", "content": "Hello, Claude"}
{"role": "user", "content": [{"type": "text", "text": "Hello, Claude"}]}
Starting with Claude 3 models, you can also send image content blocks:
{"role": "user", "content": [
{
"type": "image",
"source": {
"type": "base64",
"media_type": "image/jpeg",
"data": "/9j/4AAQSkZJRg...",
}
},
{"type": "text", "text": "What is in this image?"}
]}
See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for more input examples.
Note that if you want to include a [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use the top-level `system` parameter — there is no `"system"` role for input messages in the Messages API.
There is a limit of 100,000 messages in a single request.
Show child attributes
messages.content
required
messages.role
enum<string>
required
Available options:
`user`,
`assistant`
max_tokens
integer
required
The maximum number of tokens to generate before stopping.
Note that our models may stop _before_ reaching this maximum. This parameter only specifies the absolute maximum number of tokens to generate.
Different models have different maximum values for this parameter. See [models](https://docs.anthropic.com/en/docs/models-overview) for details.
Required range: `x >= 1`
Examples:
`1024`
container
string | null
Container identifier for reuse across requests.
mcp_servers
object[]
MCP servers to be utilized in this request
Show child attributes
mcp_servers.name
string
required
mcp_servers.type
enum<string>
required
Available options:
`url`
mcp_servers.url
string
required
mcp_servers.authorization_token
string | null
mcp_servers.tool_configuration
object | null
Show child attributes
mcp_servers.tool_configuration.allowed_tools
string[] | null
mcp_servers.tool_configuration.enabled
boolean | null
metadata
object
An object describing metadata about the request.
Show child attributes
metadata.user_id
string | null
An external identifier for the user who is associated with the request.
This should be a uuid, hash value, or other opaque identifier. Anthropic may use this id to help detect abuse. Do not include any identifying information such as name, email address, or phone number.
Maximum length: `256`
Examples:
`"13803d75-b4b5-4c3e-b2a2-6f21399b021b"`
service_tier
enum<string>
Determines whether to use priority capacity (if available) or standard capacity for this request.
Anthropic offers different levels of service for your API requests. See [service-tiers](https://docs.anthropic.com/en/api/service-tiers) for details.
Available options:
`auto`,
`standard_only`
stop_sequences
string[]
Custom text sequences that will cause the model to stop generating.
Our models will normally stop when they have naturally completed their turn, which will result in a response `stop_reason` of `"end_turn"`.
If you want the model to stop generating when it encounters custom strings of text, you can use the `stop_sequences` parameter. If the model encounters one of the custom sequences, the response `stop_reason` value will be `"stop_sequence"` and the response `stop_sequence` value will contain the matched stop sequence.
stream
boolean
Whether to incrementally stream the response using server-sent events.
See [streaming](https://docs.anthropic.com/en/api/messages-streaming) for details.
system
System prompt.
A system prompt is a way of providing context and instructions to Claude, such as specifying a particular goal or role. See our [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).
Examples:
[
{
"text": "Today's date is 2024-06-01.",
"type": "text"
}
]
`"Today's date is 2023-01-01."`
temperature
number
Amount of randomness injected into the response.
Defaults to `1.0`. Ranges from `0.0` to `1.0`. Use `temperature` closer to `0.0` for analytical / multiple choice, and closer to `1.0` for creative and generative tasks.
Note that even with `temperature` of `0.0`, the results will not be fully deterministic.
Required range: `0 <= x <= 1`
Examples:
`1`
thinking
object
Configuration for enabling Claude's extended thinking.
When enabled, responses include `thinking` content blocks showing Claude's thinking process before the final answer. Requires a minimum budget of 1,024 tokens and counts towards your `max_tokens` limit.
See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.
* Enabled
* Disabled
Show child attributes
thinking.budget_tokens
integer
required
Determines how many tokens Claude can use for its internal reasoning process. Larger budgets can enable more thorough analysis for complex problems, improving response quality.
Must be ≥1024 and less than `max_tokens`.
See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.
Required range: `x >= 1024`
thinking.type
enum<string>
required
Available options:
`enabled`
tool_choice
object
How the model should use the provided tools. The model can use a specific tool, any available tool, decide by itself, or not use tools at all.
* Auto
* Any
* Tool
* None
Show child attributes
tool_choice.type
enum<string>
required
Available options:
`auto`
tool_choice.disable_parallel_tool_use
boolean
Whether to disable parallel tool use.
Defaults to `false`. If set to `true`, the model will output at most one tool use.
tools
object[]
Definitions of tools that the model may use.
If you include `tools` in your API request, the model may return `tool_use` content blocks that represent the model's use of those tools. You can then run those tools using the tool input generated by the model and then optionally return results back to the model using `tool_result` content blocks.
Each tool definition includes:
* `name`: Name of the tool.
* `description`: Optional, but strongly-recommended description of the tool.
* `input_schema`: for the tool `input` shape that the model will produce in `tool_use` output content blocks.
For example, if you defined `tools` as:
[
{
"name": "get_stock_price",
"description": "Get the current stock price for a given ticker symbol.",
"input_schema": {
"type": "object",
"properties": {
"ticker": {
"type": "string",
"description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
}
},
"required": ["ticker"]
}
}
]
And then asked the model "What's the S&P 500 at today?", the model might produce `tool_use` content blocks in the response like this:
[
{
"type": "tool_use",
"id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
"name": "get_stock_price",
"input": { "ticker": "^GSPC" }
}
]
You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an input, and return the following back to the model in a subsequent `user` message:
[
{
"type": "tool_result",
"tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
"content": "259.75 USD"
}
]
Tools can be used for workflows that include running client-side tools and functions, or more generally whenever you want the model to produce a particular JSON structure of output.
See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.
* Custom tool
* Bash tool (2024-10-22)
* Bash tool (2025-01-24)
* Code execution tool (2025-05-22)
* Computer use tool (2024-01-22)
* Computer use tool (2025-01-24)
* Text editor tool (2024-10-22)
* Text editor tool (2025-01-24)
* Text editor tool (2025-04-29)
* Web search tool (2025-03-05)
Show child attributes
tools.name
string
required
Name of the tool.
This is how the tool will be called by the model and in `tool_use` blocks.
Required string length: `1 - 128`
tools.input_schema
object
required
for this tool's input.
This defines the shape of the `input` that your tool accepts and that the model will produce.
Show child attributes
tools.input_schema.type
enum<string>
required
Available options:
`object`
tools.input_schema.properties
object | null
tools.input_schema.required
string[] | null
tools.type
enum<string> | null
Available options:
`custom`
tools.description
string
Description of what this tool does.
Tool descriptions should be as detailed as possible. The more information that the model has about what the tool is and how to use it, the better it will perform. You can use natural language descriptions to reinforce important aspects of the tool input JSON schema.
Examples:
`"Get the current weather in a given location"`
tools.cache_control
object | null
Create a cache control breakpoint at this content block.
Show child attributes
tools.cache_control.type
enum<string>
required
Available options:
`ephemeral`
tools.cache_control.ttl
enum<string>
The time-to-live for the cache control breakpoint.
This may be one the following values:
* `5m`: 5 minutes
* `1h`: 1 hour
Defaults to `5m`.
Available options:
`5m`,
`1h`
Examples:
{
"description": "Get the current weather in a given location",
"input_schema": {
"properties": {
"location": {
"description": "The city and state, e.g. San Francisco, CA",
"type": "string"
},
"unit": {
"description": "Unit for the output - one of (celsius, fahrenheit)",
"type": "string"
}
},
"required": ["location"],
"type": "object"
},
"name": "get_weather"
}
top_k
integer
Only sample from the top K options for each subsequent token.
Used to remove "long tail" low probability responses. .
Recommended for advanced use cases only. You usually only need to use `temperature`.
Required range: `x >= 0`
Examples:
`5`
top_p
number
Use nucleus sampling.
In nucleus sampling, we compute the cumulative distribution over all the options for each subsequent token in decreasing probability order and cut it off once it reaches a particular probability specified by `top_p`. You should either alter `temperature` or `top_p`, but not both.
Recommended for advanced use cases only. You usually only need to use `temperature`.
Required range: `0 <= x <= 1`
Examples:
`0.7`
#### Response
200
2004XX
application/json
Message object.
id
string
required
Unique object identifier.
The format and length of IDs may change over time.
Examples:
`"msg_013Zva2CMHLNnXjNJJKqJ2EF"`
type
enum<string>
default:message
required
Object type.
For Messages, this is always `"message"`.
Available options:
`message`
role
enum<string>
default:assistant
required
Conversational role of the generated message.
This will always be `"assistant"`.
Available options:
`assistant`
content
object[]
required
Content generated by the model.
This is an array of content blocks, each of which has a `type` that determines its shape.
Example:
[{"type": "text", "text": "Hi, I'm Claude."}]
If the request input `messages` ended with an `assistant` turn, then the response `content` will continue directly from that last turn. You can use this to constrain the model's output.
For example, if the input `messages` were:
[
{"role": "user", "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"},
{"role": "assistant", "content": "The best answer is ("}
]
Then the response `content` might be:
[{"type": "text", "text": "B)"}]
* Thinking
* Redacted thinking
* Tool use
* Server tool use
* Web search tool result
* Code execution tool result
* MCP tool use
* MCP tool result
* Container upload
Show child attributes
content.signature
string
required
content.thinking
string
required
content.type
enum<string>
default:thinking
required
Available options:
`thinking`
Examples:
[
{
"text": "Hi! My name is Claude.",
"type": "text"
}
]
model
string
required
The model that handled the request.
Required string length: `1 - 256`
Examples:
`"claude-sonnet-4-20250514"`
stop_reason
enum<string> | null
required
The reason that we stopped.
This may be one the following values:
* `"end_turn"`: the model reached a natural stopping point
* `"max_tokens"`: we exceeded the requested `max_tokens` or the model's maximum
* `"stop_sequence"`: one of your provided custom `stop_sequences` was generated
* `"tool_use"`: the model invoked one or more tools
* `"pause_turn"`: we paused a long-running turn. You may provide the response back as-is in a subsequent request to let the model continue.
* `"refusal"`: when streaming classifiers intervene to handle potential policy violations
In non-streaming mode this value is always non-null. In streaming mode, it is null in the `message_start` event and non-null otherwise.
Available options:
`end_turn`,
`max_tokens`,
`stop_sequence`,
`tool_use`,
`pause_turn`,
`refusal`
stop_sequence
string | null
required
Which custom stop sequence was generated, if any.
This value will be a non-null string if one of your custom stop sequences was generated.
usage
object
required
Billing and rate-limit usage.
Anthropic's API bills and rate-limits by token counts, as tokens represent the underlying cost to our systems.
Under the hood, the API transforms requests into a format suitable for the model. The model's output then goes through a parsing stage before becoming an API response. As a result, the token counts in `usage` will not match one-to-one with the exact visible content of an API request or response.
For example, `output_tokens` will be non-zero, even for an empty string response from Claude.
Total input tokens in a request is the summation of `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`.
Show child attributes
usage.cache_creation
object | null
required
Breakdown of cached tokens by TTL
Show child attributes
usage.cache_creation.ephemeral_1h_input_tokens
integer
default:0
required
The number of input tokens used to create the 1 hour cache entry.
Required range: `x >= 0`
usage.cache_creation.ephemeral_5m_input_tokens
integer
default:0
required
The number of input tokens used to create the 5 minute cache entry.
Required range: `x >= 0`
usage.cache_creation_input_tokens
integer | null
required
The number of input tokens used to create the cache entry.
Required range: `x >= 0`
Examples:
`2051`
usage.cache_read_input_tokens
integer | null
required
The number of input tokens read from the cache.
Required range: `x >= 0`
Examples:
`2051`
usage.input_tokens
integer
required
The number of input tokens which were used.
Required range: `x >= 0`
Examples:
`2095`
usage.output_tokens
integer
required
The number of output tokens which were used.
Required range: `x >= 0`
Examples:
`503`
usage.server_tool_use
object | null
required
The number of server tool requests.
Show child attributes
usage.server_tool_use.web_search_requests
integer
default:0
required
The number of web search tool requests.
Required range: `x >= 0`
Examples:
`0`
usage.service_tier
enum<string> | null
required
If the request used the priority, standard, or batch tier.
Available options:
`standard`,
`priority`,
`batch`
container
object | null
required
Information about the container used in this request.
This will be non-null if a container tool (e.g. code execution) was used.
Show child attributes
container.expires_at
string
required
The time at which the container will expire.
container.id
string
required
Identifier for the container used in this request
[Beta headers](/en/api/beta-headers)[Count Message tokens](/en/api/messages-count-tokens)
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-sonnet-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, world"}
]
}'
{
"content": [
{
"text": "Hi! My name is Claude.",
"type": "text"
}
],
"id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
"model": "claude-sonnet-4-20250514",
"role": "assistant",
"stop_reason": "end_turn",
"stop_sequence": null,
"type": "message",
"usage": {
"input_tokens": 2095,
"output_tokens": 503
}
}

## Message Batches examples

*Source: https://docs.anthropic.com/en/api/messages-batch-examples*

Message Batches examples
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
Creating a Message Batch
import anthropic
from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
from anthropic.types.messages.batch_create_params import Request
client = anthropic.Anthropic()
message_batch = client.messages.batches.create(
requests=[
Request(
custom_id="my-first-request",
params=MessageCreateParamsNonStreaming(
model="claude-opus-4-20250514",
max_tokens=1024,
messages=[{
"role": "user",
"content": "Hello, world",
}]
)
),
Request(
custom_id="my-second-request",
params=MessageCreateParamsNonStreaming(
model="claude-opus-4-20250514",
max_tokens=1024,
messages=[{
"role": "user",
"content": "Hi again, friend",
}]
)
)
]
)
print(message_batch)
JSON
{
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"type": "message_batch",
"processing_status": "in_progress",
"request_counts": {
"processing": 2,
"succeeded": 0,
"errored": 0,
"canceled": 0,
"expired": 0
},
"ended_at": null,
"created_at": "2024-09-24T18:37:24.100435Z",
"expires_at": "2024-09-25T18:37:24.100435Z",
"cancel_initiated_at": null,
"results_url": null
}
Polling for Message Batch completion
To poll a Message Batch, you’ll need its `id`, which is provided in the response when [creating](/_sites/docs.anthropic.com/en/api/messages-batch-examples#creating-a-message-batch) request or by [listing](/_sites/docs.anthropic.com/en/api/messages-batch-examples#listing-all-message-batches-in-a-workspace) batches. Example `id`: `msgbatch_013Zva2CMHLNnXjNJJKqJ2EF`.
import anthropic
client = anthropic.Anthropic()
message_batch = None
while True:
message_batch = client.messages.batches.retrieve(
MESSAGE_BATCH_ID
)
if message_batch.processing_status == "ended":
break
print(f"Batch {MESSAGE_BATCH_ID} is still processing...")
time.sleep(60)
print(message_batch)
Listing all Message Batches in a Workspace
import anthropic
client = anthropic.Anthropic()
# Automatically fetches more pages as needed.
for message_batch in client.messages.batches.list(
limit=20
):
print(message_batch)
{
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"type": "message_batch",
...
}
{
"id": "msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d",
"type": "message_batch",
...
}
Retrieving Message Batch Results
Once your Message Batch status is `ended`, you will be able to view the `results_url` of the batch and retrieve results in the form of a `.jsonl` file.
import anthropic
client = anthropic.Anthropic()
# Stream results file in memory-efficient chunks, processing one at a time
for result in client.messages.batches.results(
MESSAGE_BATCH_ID,
):
print(result)
{
"id": "my-second-request",
"result": {
"type": "succeeded",
"message": {
"id": "msg_018gCsTGsXkYJVqYPxTgDHBU",
"type": "message",
...
}
}
}
{
"custom_id": "my-first-request",
"result": {
"type": "succeeded",
"message": {
"id": "msg_01XFDUDYJgAACzvnptvVoYEL",
"type": "message",
...
}
}
}
Canceling a Message Batch
Immediately after cancellation, a batch’s `processing_status` will be `canceling`. You can use the same [polling for batch completion](/_sites/docs.anthropic.com/en/api/messages-batch-examples#polling-for-message-batch-completion) technique to poll for when cancellation is finalized as canceled batches also end up `ended` and may contain results.
import anthropic
client = anthropic.Anthropic()
message_batch = client.messages.batches.cancel(
MESSAGE_BATCH_ID,
)
print(message_batch)
JSON
{
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"type": "message_batch",
"processing_status": "canceling",
"request_counts": {
"processing": 2,
"succeeded": 0,
"errored": 0,
"canceled": 0,
"expired": 0
},
"ended_at": null,
"created_at": "2024-09-24T18:37:24.100435Z",
"expires_at": "2024-09-25T18:37:24.100435Z",
"cancel_initiated_at": "2024-09-24T18:39:03.114875Z",
"results_url": null
}
[Messages examples](/en/api/messages-examples)[Amazon Bedrock API](/en/api/claude-on-amazon-bedrock)

## Count Message tokens

*Source: https://docs.anthropic.com/en/api/messages-count-tokens*

Count Message tokens
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
messages
/
count_tokens
curl https://api.anthropic.com/v1/messages/count_tokens \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-3-7-sonnet-20250219",
"messages": [
{"role": "user", "content": "Hello, world"}
]
}'
{
"input_tokens": 2095
}
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Body
application/json
messages
object[]
required
Input messages.
Our models are trained to operate on alternating `user` and `assistant` conversational turns. When creating a new `Message`, you specify the prior conversational turns with the `messages` parameter, and the model then generates the next `Message` in the conversation. Consecutive `user` or `assistant` turns in your request will be combined into a single turn.
Each input message must be an object with a `role` and `content`. You can specify a single `user`-role message, or you can include multiple `user` and `assistant` messages.
If the final message uses the `assistant` role, the response content will continue immediately from the content in that message. This can be used to constrain part of the model's response.
Example with a single `user` message:
[{"role": "user", "content": "Hello, Claude"}]
Example with multiple conversational turns:
Example with a partially-filled response from Claude:
[
{"role": "user", "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"},
{"role": "assistant", "content": "The best answer is ("},
]
Each input message `content` may be either a single `string` or an array of content blocks, where each block has a specific `type`. Using a `string` for `content` is shorthand for an array of one content block of type `"text"`. The following input messages are equivalent:
{"role": "user", "content": "Hello, Claude"}
{"role": "user", "content": [{"type": "text", "text": "Hello, Claude"}]}
Starting with Claude 3 models, you can also send image content blocks:
{"role": "user", "content": [
{
"type": "image",
"source": {
"type": "base64",
"media_type": "image/jpeg",
"data": "/9j/4AAQSkZJRg...",
}
},
{"type": "text", "text": "What is in this image?"}
]}
See [examples](https://docs.anthropic.com/en/api/messages-examples#vision) for more input examples.
Note that if you want to include a [system prompt](https://docs.anthropic.com/en/docs/system-prompts), you can use the top-level `system` parameter — there is no `"system"` role for input messages in the Messages API.
There is a limit of 100,000 messages in a single request.
Show child attributes
messages.content
required
messages.role
enum<string>
required
Available options:
`user`,
`assistant`
model
string
required
The model that will complete your prompt.
See [models](https://docs.anthropic.com/en/docs/models-overview) for additional details and options.
Required string length: `1 - 256`
Examples:
`"claude-sonnet-4-20250514"`
mcp_servers
object[]
MCP servers to be utilized in this request
Show child attributes
mcp_servers.name
string
required
mcp_servers.type
enum<string>
required
Available options:
`url`
mcp_servers.url
string
required
mcp_servers.authorization_token
string | null
mcp_servers.tool_configuration
object | null
Show child attributes
mcp_servers.tool_configuration.allowed_tools
string[] | null
mcp_servers.tool_configuration.enabled
boolean | null
system
System prompt.
A system prompt is a way of providing context and instructions to Claude, such as specifying a particular goal or role. See our [guide to system prompts](https://docs.anthropic.com/en/docs/system-prompts).
Examples:
[
{
"text": "Today's date is 2024-06-01.",
"type": "text"
}
]
`"Today's date is 2023-01-01."`
thinking
object
Configuration for enabling Claude's extended thinking.
When enabled, responses include `thinking` content blocks showing Claude's thinking process before the final answer. Requires a minimum budget of 1,024 tokens and counts towards your `max_tokens` limit.
See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.
* Enabled
* Disabled
Show child attributes
thinking.budget_tokens
integer
required
Determines how many tokens Claude can use for its internal reasoning process. Larger budgets can enable more thorough analysis for complex problems, improving response quality.
Must be ≥1024 and less than `max_tokens`.
See [extended thinking](https://docs.anthropic.com/en/docs/build-with-claude/extended-thinking) for details.
Required range: `x >= 1024`
thinking.type
enum<string>
required
Available options:
`enabled`
tool_choice
object
How the model should use the provided tools. The model can use a specific tool, any available tool, decide by itself, or not use tools at all.
* Auto
* Any
* Tool
* None
Show child attributes
tool_choice.type
enum<string>
required
Available options:
`auto`
tool_choice.disable_parallel_tool_use
boolean
Whether to disable parallel tool use.
Defaults to `false`. If set to `true`, the model will output at most one tool use.
tools
object[]
Definitions of tools that the model may use.
If you include `tools` in your API request, the model may return `tool_use` content blocks that represent the model's use of those tools. You can then run those tools using the tool input generated by the model and then optionally return results back to the model using `tool_result` content blocks.
Each tool definition includes:
* `name`: Name of the tool.
* `description`: Optional, but strongly-recommended description of the tool.
* `input_schema`: for the tool `input` shape that the model will produce in `tool_use` output content blocks.
For example, if you defined `tools` as:
[
{
"name": "get_stock_price",
"description": "Get the current stock price for a given ticker symbol.",
"input_schema": {
"type": "object",
"properties": {
"ticker": {
"type": "string",
"description": "The stock ticker symbol, e.g. AAPL for Apple Inc."
}
},
"required": ["ticker"]
}
}
]
And then asked the model "What's the S&P 500 at today?", the model might produce `tool_use` content blocks in the response like this:
[
{
"type": "tool_use",
"id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
"name": "get_stock_price",
"input": { "ticker": "^GSPC" }
}
]
You might then run your `get_stock_price` tool with `{"ticker": "^GSPC"}` as an input, and return the following back to the model in a subsequent `user` message:
[
{
"type": "tool_result",
"tool_use_id": "toolu_01D7FLrfh4GYq7yT1ULFeyMV",
"content": "259.75 USD"
}
]
Tools can be used for workflows that include running client-side tools and functions, or more generally whenever you want the model to produce a particular JSON structure of output.
See our [guide](https://docs.anthropic.com/en/docs/tool-use) for more details.
* Custom tool
* Bash tool (2024-10-22)
* Bash tool (2025-01-24)
* Code execution tool (2025-05-22)
* Computer use tool (2024-01-22)
* Computer use tool (2025-01-24)
* Text editor tool (2024-10-22)
* Text editor tool (2025-01-24)
* Text editor tool (2025-04-29)
* Web search tool (2025-03-05)
Show child attributes
tools.name
string
required
Name of the tool.
This is how the tool will be called by the model and in `tool_use` blocks.
Required string length: `1 - 128`
tools.input_schema
object
required
for this tool's input.
This defines the shape of the `input` that your tool accepts and that the model will produce.
Show child attributes
tools.input_schema.type
enum<string>
required
Available options:
`object`
tools.input_schema.properties
object | null
tools.input_schema.required
string[] | null
tools.type
enum<string> | null
Available options:
`custom`
tools.description
string
Description of what this tool does.
Tool descriptions should be as detailed as possible. The more information that the model has about what the tool is and how to use it, the better it will perform. You can use natural language descriptions to reinforce important aspects of the tool input JSON schema.
Examples:
`"Get the current weather in a given location"`
tools.cache_control
object | null
Create a cache control breakpoint at this content block.
Show child attributes
tools.cache_control.type
enum<string>
required
Available options:
`ephemeral`
tools.cache_control.ttl
enum<string>
The time-to-live for the cache control breakpoint.
This may be one the following values:
* `5m`: 5 minutes
* `1h`: 1 hour
Defaults to `5m`.
Available options:
`5m`,
`1h`
Examples:
{
"description": "Get the current weather in a given location",
"input_schema": {
"properties": {
"location": {
"description": "The city and state, e.g. San Francisco, CA",
"type": "string"
},
"unit": {
"description": "Unit for the output - one of (celsius, fahrenheit)",
"type": "string"
}
},
"required": ["location"],
"type": "object"
},
"name": "get_weather"
}
#### Response
200
2004XX
application/json
Successful Response
input_tokens
integer
required
The total number of tokens across the provided list of messages, system prompt, and tools.
Examples:
`2095`
[Messages](/en/api/messages)[List Models](/en/api/models-list)
curl https://api.anthropic.com/v1/messages/count_tokens \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-3-7-sonnet-20250219",
"messages": [
{"role": "user", "content": "Hello, world"}
]
}'
{
"input_tokens": 2095
}

## Messages examples

*Source: https://docs.anthropic.com/en/api/messages-examples*

Messages examples
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
Basic request and response
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, Claude"}
]
}'
JSON
{
"id": "msg_01XFDUDYJgAACzvnptvVoYEL",
"type": "message",
"role": "assistant",
"content": [
{
"type": "text",
"text": "Hello!"
}
],
"model": "claude-opus-4-20250514",
"stop_reason": "end_turn",
"stop_sequence": null,
"usage": {
"input_tokens": 12,
"output_tokens": 6
}
}
Multiple conversational turns
The Messages API is stateless, which means that you always send the full conversational history to the API. You can use this pattern to build up a conversation over time. Earlier conversational turns don’t necessarily need to actually originate from Claude — you can use synthetic `assistant` messages.
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": "Hello, Claude"},
{"role": "assistant", "content": "Hello!"},
{"role": "user", "content": "Can you describe LLMs to me?"}
]
}'
JSON
{
"id": "msg_018gCsTGsXkYJVqYPxTgDHBU",
"type": "message",
"role": "assistant",
"content": [
{
"type": "text",
"text": "Sure, I'd be happy to provide..."
}
],
"stop_reason": "end_turn",
"stop_sequence": null,
"usage": {
"input_tokens": 30,
"output_tokens": 309
}
}
Putting words in Claude’s mouth
You can pre-fill part of Claude’s response in the last position of the input messages list. This can be used to shape Claude’s response. The example below uses `"max_tokens": 1` to get a single multiple choice answer from Claude.
#!/bin/sh
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1,
"messages": [
{"role": "user", "content": "What is latin for Ant? (A) Apoidea, (B) Rhopalocera, (C) Formicidae"},
{"role": "assistant", "content": "The answer is ("}
]
}'
JSON
{
"id": "msg_01Q8Faay6S7QPTvEUUQARt7h",
"type": "message",
"role": "assistant",
"content": [
{
"type": "text",
"text": "C"
}
],
"model": "claude-opus-4-20250514",
"stop_reason": "max_tokens",
"stop_sequence": null,
"usage": {
"input_tokens": 42,
"output_tokens": 1
}
}
#!/bin/sh
# Option 1: Base64-encoded image
IMAGE_URL="https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
IMAGE_MEDIA_TYPE="image/jpeg"
IMAGE_BASE64=$(curl "$IMAGE_URL" | base64)
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": [
{"type": "image", "source": {
"type": "base64",
"media_type": "'$IMAGE_MEDIA_TYPE'",
"data": "'$IMAGE_BASE64'"
}},
{"type": "text", "text": "What is in the above image?"}
]}
]
}'
# Option 2: URL-referenced image
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"messages": [
{"role": "user", "content": [
{"type": "image", "source": {
"type": "url",
"url": "https://upload.wikimedia.org/wikipedia/commons/a/a7/Camponotus_flavomarginatus_ant.jpg"
}},
{"type": "text", "text": "What is in the above image?"}
]}
]
}'
JSON
{
"id": "msg_01EcyWo6m4hyW8KHs2y2pei5",
"type": "message",
"role": "assistant",
"content": [
{
"type": "text",
"text": "This image shows an ant, specifically a close-up view of an ant. The ant is shown in detail, with its distinct head, antennae, and legs clearly visible. The image is focused on capturing the intricate details and features of the ant, likely taken with a macro lens to get an extreme close-up perspective."
}
],
"model": "claude-opus-4-20250514",
"stop_reason": "end_turn",
"stop_sequence": null,
"usage": {
"input_tokens": 1551,
"output_tokens": 71
}
}
Tool use, JSON mode, and computer use
See our [guide](/en/docs/agents-and-tools/tool-use/overview) for examples for how to use tools with the Messages API. See our [computer use guide](/en/docs/agents-and-tools/tool-use/computer-use-tool) for examples of how to control desktop computer environments with the Messages API.
[OpenAI SDK compatibility](/en/api/openai-sdk)[Message Batches examples](/en/api/messages-batch-examples)

## Streaming Messages

*Source: https://docs.anthropic.com/en/api/messages-streaming*

Streaming Messages
* *
##### Models & pricing
##### Learn about Claude
##### Capabilities
##### Tools
* *
##### Use cases
##### Prompt engineering
##### Test & evaluate
##### Strengthen guardrails
##### Legal center
* *
When creating a Message, you can set `"stream": true` to incrementally stream the response using (SSE).
Streaming with SDKs
import anthropic
client = anthropic.Anthropic()
with client.messages.stream(
max_tokens=1024,
messages=[{"role": "user", "content": "Hello"}],
model="claude-opus-4-20250514",
) as stream:
for text in stream.text_stream:
print(text, end="", flush=True)
Event types
Each server-sent event includes a named event type and associated JSON data. Each event will use an SSE event name (e.g. `event: message_stop`), and include the matching event `type` in its data.
Each stream uses the following event flow:
1. `message_start`: contains a `Message` object with empty `content`.
2. A series of content blocks, each of which have a `content_block_start`, one or more `content_block_delta` events, and a `content_block_stop` event. Each content block will have an `index` that corresponds to its index in the final Message `content` array.
3. One or more `message_delta` events, indicating top-level changes to the final `Message` object.
4. A final `message_stop` event.
The token counts shown in the `usage` field of the `message_delta` event are _cumulative_.
###
Ping events
Event streams may also include any number of `ping` events.
###
Error events
We may occasionally send [errors](/en/api/errors) in the event stream. For example, during periods of high usage, you may receive an `overloaded_error`, which would normally correspond to an HTTP 529 in a non-streaming context:
Example error
event: error
data: {"type": "error", "error": {"type": "overloaded_error", "message": "Overloaded"}}
###
Other events
In accordance with our [versioning policy](/en/api/versioning), we may add new event types, and your code should handle unknown event types gracefully.
Content block delta types
Each `content_block_delta` event contains a `delta` of a type that updates the `content` block at a given `index`.
###
Text delta
A `text` content block delta looks like:
Text delta
event: content_block_delta
data: {"type": "content_block_delta","index": 0,"delta": {"type": "text_delta", "text": "ello frien"}}
###
Input JSON delta
You can accumulate the string deltas and parse the JSON once you receive a `content_block_stop` event, by using a library like to do partial JSON parsing, or by using our [SDKs](https://docs.anthropic.com/en/api/client-sdks), which provide helpers to access parsed incremental values.
A `tool_use` content block delta looks like:
Input JSON delta
event: content_block_delta
data: {"type": "content_block_delta","index": 1,"delta": {"type": "input_json_delta","partial_json": "{\"location\": \"San Fra"}}}
###
Thinking delta
When using [extended thinking](/en/docs/build-with-claude/extended-thinking#streaming-thinking) with streaming enabled, you’ll receive thinking content via `thinking_delta` events. These deltas correspond to the `thinking` field of the `thinking` content blocks.
For thinking content, a special `signature_delta` event is sent just before the `content_block_stop` event. This signature is used to verify the integrity of the thinking block.
A typical thinking delta looks like:
Thinking delta
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "Let me solve this step by step:\n\n1. First break down 27 * 453"}}
The signature delta looks like:
Signature delta
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "EqQBCgIYAhIM1gbcDa9GJwZA2b3hGgxBdjrkzLoky3dl1pkiMOYds..."}}
Full HTTP Stream response
We strongly recommend that you use our [client SDKs](/en/api/client-sdks) when using streaming mode. However, if you are building a direct API integration, you will need to handle these events yourself.
A stream response is comprised of:
1. A `message_start` event
2. Potentially multiple content blocks, each of which contains:
* A `content_block_start` event
* Potentially multiple `content_block_delta` events
* A `content_block_stop` event
3. A `message_delta` event
4. A `message_stop` event
There may be `ping` events dispersed throughout the response as well. See [Event types](/_sites/docs.anthropic.com/en/docs/build-with-claude/streaming#event-types) for more details on the format.
###
Basic streaming request
curl https://api.anthropic.com/v1/messages \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--data \
'{
"model": "claude-opus-4-20250514",
"messages": [{"role": "user", "content": "Hello"}],
"max_tokens": 256,
"stream": true
}'
event: message_start
data: {"type": "message_start", "message": {"id": "msg_1nZdL29xx5MUA1yADyHTEsnR8uuvGzszyY", "type": "message", "role": "assistant", "content": [], "model": "claude-opus-4-20250514", "stop_reason": null, "stop_sequence": null, "usage": {"input_tokens": 25, "output_tokens": 1}}}
event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "text", "text": ""}}
event: ping
data: {"type": "ping"}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "Hello"}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": "!"}}
event: content_block_stop
data: {"type": "content_block_stop", "index": 0}
event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence":null}, "usage": {"output_tokens": 15}}
event: message_stop
data: {"type": "message_stop"}
###
Streaming request with tool use
In this request, we ask Claude to use a tool to tell us the weather.
curl https://api.anthropic.com/v1/messages \
-H "content-type: application/json" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-d '{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"tools": [
{
"name": "get_weather",
"description": "Get the current weather in a given location",
"input_schema": {
"type": "object",
"properties": {
"location": {
"type": "string",
"description": "The city and state, e.g. San Francisco, CA"
}
},
"required": ["location"]
}
}
],
"tool_choice": {"type": "any"},
"messages": [
{
"role": "user",
"content": "What is the weather like in San Francisco?"
}
],
"stream": true
}'
event: message_start
data: {"type":"message_start","message":{"id":"msg_014p7gG3wDgGV9EUtLvnow3U","type":"message","role":"assistant","model":"claude-opus-4-20250514","stop_sequence":null,"usage":{"input_tokens":472,"output_tokens":2},"content":[],"stop_reason":null}}
event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
event: ping
data: {"type": "ping"}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"Okay"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":","}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" let"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"'s"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" check"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" the"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" weather"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" for"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" San"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" Francisco"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":","}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" CA"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":":"}}
event: content_block_stop
data: {"type":"content_block_stop","index":0}
event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"tool_use","id":"toolu_01T1x1fJ34qAmk2tNTrN7Up6","name":"get_weather","input":{}}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":""}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"location\":"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" \"San"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" Francisc"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"o,"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" CA\""}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":", "}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"\"unit\": \"fah"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"renheit\"}"}}
event: content_block_stop
data: {"type":"content_block_stop","index":1}
event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"tool_use","stop_sequence":null},"usage":{"output_tokens":89}}
event: message_stop
data: {"type":"message_stop"}
###
Streaming request with extended thinking
In this request, we enable extended thinking with streaming to see Claude’s step-by-step reasoning.
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 20000,
"stream": true,
"thinking": {
"type": "enabled",
"budget_tokens": 16000
},
"messages": [
{
"role": "user",
"content": "What is 27 * 453?"
}
]
}'
event: message_start
data: {"type": "message_start", "message": {"id": "msg_01...", "type": "message", "role": "assistant", "content": [], "model": "claude-opus-4-20250514", "stop_reason": null, "stop_sequence": null}}
event: content_block_start
data: {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking", "thinking": ""}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "Let me solve this step by step:\n\n1. First break down 27 * 453"}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "\n2. 453 = 400 + 50 + 3"}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "\n3. 27 * 400 = 10,800"}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "\n4. 27 * 50 = 1,350"}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "\n5. 27 * 3 = 81"}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "thinking_delta", "thinking": "\n6. 10,800 + 1,350 + 81 = 12,231"}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 0, "delta": {"type": "signature_delta", "signature": "EqQBCgIYAhIM1gbcDa9GJwZA2b3hGgxBdjrkzLoky3dl1pkiMOYds..."}}
event: content_block_stop
data: {"type": "content_block_stop", "index": 0}
event: content_block_start
data: {"type": "content_block_start", "index": 1, "content_block": {"type": "text", "text": ""}}
event: content_block_delta
data: {"type": "content_block_delta", "index": 1, "delta": {"type": "text_delta", "text": "27 * 453 = 12,231"}}
event: content_block_stop
data: {"type": "content_block_stop", "index": 1}
event: message_delta
data: {"type": "message_delta", "delta": {"stop_reason": "end_turn", "stop_sequence": null}}
event: message_stop
data: {"type": "message_stop"}
###
Streaming request with web search tool use
In this request, we ask Claude to search the web for current weather information.
curl https://api.anthropic.com/v1/messages \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--data \
'{
"model": "claude-opus-4-20250514",
"max_tokens": 1024,
"stream": true,
"messages": [
{
"role": "user",
"content": "What is the weather like in New York City today?"
}
]
}'
event: message_start
data: {"type":"message_start","message":{"id":"msg_01G...","type":"message","role":"assistant","model":"claude-opus-4-20250514","content":[],"stop_reason":null,"stop_sequence":null,"usage":{"input_tokens":2679,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":3}}}
event: content_block_start
data: {"type":"content_block_start","index":0,"content_block":{"type":"text","text":""}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"I'll check"}}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":" the current weather in New York City for you"}}
event: ping
data: {"type": "ping"}
event: content_block_delta
data: {"type":"content_block_delta","index":0,"delta":{"type":"text_delta","text":"."}}
event: content_block_stop
data: {"type":"content_block_stop","index":0}
event: content_block_start
data: {"type":"content_block_start","index":1,"content_block":{"type":"server_tool_use","id":"srvtoolu_014hJH82Qum7Td6UV8gDXThB","name":"web_search","input":{}}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":""}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"{\"query"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"\":"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" \"weather"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":" NY"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"C to"}}
event: content_block_delta
data: {"type":"content_block_delta","index":1,"delta":{"type":"input_json_delta","partial_json":"day\"}"}}
event: content_block_stop
data: {"type":"content_block_stop","index":1 }
event: content_block_start
data: {"type":"content_block_start","index":2,"content_block":{"type":"web_search_tool_result","tool_use_id":"srvtoolu_014hJH82Qum7Td6UV8gDXThB","content":[{"type":"web_search_result","title":"Weather in New York City in May 2025 (New York) - detailed Weather Forecast for a month","url":"https://world-weather.info/forecast/usa/new_york/may-2025/","encrypted_content":"Ev0DCioIAxgCIiQ3NmU4ZmI4OC1k...","page_age":null},...]}}
event: content_block_stop
data: {"type":"content_block_stop","index":2}
event: content_block_start
data: {"type":"content_block_start","index":3,"content_block":{"type":"text","text":""}}
event: content_block_delta
data: {"type":"content_block_delta","index":3,"delta":{"type":"text_delta","text":"Here's the current weather information for New York"}}
event: content_block_delta
data: {"type":"content_block_delta","index":3,"delta":{"type":"text_delta","text":" City:\n\n# Weather"}}
event: content_block_delta
data: {"type":"content_block_delta","index":3,"delta":{"type":"text_delta","text":" in New York City"}}
event: content_block_delta
data: {"type":"content_block_delta","index":3,"delta":{"type":"text_delta","text":"\n\n"}}
...
event: content_block_stop
data: {"type":"content_block_stop","index":17}
event: message_delta
data: {"type":"message_delta","delta":{"stop_reason":"end_turn","stop_sequence":null},"usage":{"input_tokens":10682,"cache_creation_input_tokens":0,"cache_read_input_tokens":0,"output_tokens":510,"server_tool_use":{"web_search_requests":1}}}
event: message_stop
data: {"type":"message_stop"}
[Extended thinking](/en/docs/build-with-claude/extended-thinking)[Batch processing](/en/docs/build-with-claude/batch-processing)

## Migrating from Text Completions

*Source: https://docs.anthropic.com/en/api/migrating-from-text-completions-to-messages*

Text Completions (Legacy)
Migrating from Text Completions
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
When migrating from [Text Completions](/en/api/complete) to [Messages](/en/api/messages), consider the following changes.
###
Inputs and outputs
The largest change between Text Completions and the Messages is the way in which you specify model inputs and receive outputs from the model.
With Text Completions, inputs are raw strings:
prompt = "\n\nHuman: Hello there\n\nAssistant: Hi, I'm Claude. How can I help?\n\nHuman: Can you explain Glycolysis to me?\n\nAssistant:"
With Messages, you specify a list of input messages instead of a raw prompt:
messages = [
{"role": "user", "content": "Hello there."},
{"role": "assistant", "content": "Hi, I'm Claude. How can I help?"},
{"role": "user", "content": "Can you explain Glycolysis to me?"},
]
Each input message has a `role` and `content`.
**Role names**
With Text Completions, the model’s generated text is returned in the `completion` values of the response:
>>> response = anthropic.completions.create(...)
>>> response.completion
" Hi, I'm Claude"
With Messages, the response is the `content` value, which is a list of content blocks:
>>> response = anthropic.messages.create(...)
>>> response.content
[{"type": "text", "text": "Hi, I'm Claude"}]
###
Putting words in Claude’s mouth
With Text Completions, you can pre-fill part of Claude’s response:
prompt = "\n\nHuman: Hello\n\nAssistant: Hello, my name is"
With Messages, you can achieve the same result by making the last input message have the `assistant` role:
messages = [
{"role": "human", "content": "Hello"},
{"role": "assistant", "content": "Hello, my name is"},
]
When doing so, response `content` will continue from the last input message `content`:
JSON
{
"role": "assistant",
"content": [{"type": "text", "text": " Claude. How can I assist you today?" }],
...
}
###
System prompt
With Text Completions, the [system prompt](/en/docs/build-with-claude/prompt-engineering/system-prompts) is specified by adding text before the first `\n\nHuman:` turn:
prompt = "Today is January 1, 2024.\n\nHuman: Hello, Claude\n\nAssistant:"
With Messages, you specify the system prompt with the `system` parameter:
anthropic.Anthropic().messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
system="Today is January 1, 2024.", # <-- system prompt
messages=[
{"role": "user", "content": "Hello, Claude"}
]
)
###
Model names
The Messages API requires that you specify the full model version (e.g. `claude-sonnet-4-20250514`).
###
Stop reason
Text Completions always have a `stop_reason` of either:
* `"stop_sequence"`: The model either ended its turn naturally, or one of your custom stop sequences was generated.
* `"max_tokens"`: Either the model generated your specified `max_tokens` of content, or it reached its [absolute maximum](/en/docs/about-claude/models/overview#model-comparison-table).
Messages have a `stop_reason` of one of the following values:
* `"end_turn"`: The conversational turn ended naturally.
* `"stop_sequence"`: One of your specified custom stop sequences was generated.
* `"max_tokens"`: (unchanged)
###
Specifying max tokens
* Text Completions: `max_tokens_to_sample` parameter. No validation, but capped values per-model.
###
Streaming format
When using `"stream": true` in with Text Completions, the response included any of `completion`, `ping`, and `error` server-sent-events. See [Text Completions streaming](/en/api/streaming) for details.
Messages can contain multiple content blocks of varying types, and so its streaming format is somewhat more complex. See [Messages streaming](/en/docs/build-with-claude/streaming) for details.
[Templatize a prompt](/en/api/prompt-tools-templatize)[Create a Text Completion](/en/api/complete)

## Retrieve Message Batch Results

*Source: https://docs.anthropic.com/en/api/retrieving-message-batch-results*

Message Batches
Retrieve Message Batch Results
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
messages
/
batches
/
{message_batch_id}
/
results
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d/results \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{"custom_id":"my-second-request","result":{"type":"succeeded","message":{"id":"msg_014VwiXbi91y3JMjcpyGBHX5","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello again! It's nice to see you. How can I assist you today? Is there anything specific you'd like to chat about or any questions you have?"}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":11,"output_tokens":36}}}}
{"custom_id":"my-first-request","result":{"type":"succeeded","message":{"id":"msg_01FqfsLoHwgeFbguDgpz48m7","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello! How can I assist you today? Feel free to ask me any questions or let me know if there's anything you'd like to chat about."}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":10,"output_tokens":34}}}}
The path for retrieving Message Batch results should be pulled from the batch’s `results_url`. This path should not be assumed and may change.
{"custom_id":"my-second-request","result":{"type":"succeeded","message":{"id":"msg_014VwiXbi91y3JMjcpyGBHX5","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello again! It's nice to see you. How can I assist you today? Is there anything specific you'd like to chat about or any questions you have?"}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":11,"output_tokens":36}}}}
{"custom_id":"my-first-request","result":{"type":"succeeded","message":{"id":"msg_01FqfsLoHwgeFbguDgpz48m7","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello! How can I assist you today? Feel free to ask me any questions or let me know if there's anything you'd like to chat about."}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":10,"output_tokens":34}}}}
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Path Parameters
message_batch_id
string
required
ID of the Message Batch.
#### Response
200
2004XX
application/x-jsonl
Successful Response
This is a single line in the response `.jsonl` file and does not represent the response as a whole.
custom_id
string
required
Developer-provided ID created for each request in a Message Batch. Useful for matching results to requests, as results may be given out of request order.
Must be unique for each request within the Message Batch.
Examples:
`"my-custom-id-1"`
result
object
required
Processing result for this request.
Contains a Message output if processing was successful, an error response if processing failed, or the reason why processing was not attempted, such as cancellation or expiration.
* SucceededResult
* ErroredResult
* CanceledResult
* ExpiredResult
Show child attributes
result.message
object
required
Show child attributes
result.message.id
string
required
Unique object identifier.
The format and length of IDs may change over time.
Examples:
`"msg_013Zva2CMHLNnXjNJJKqJ2EF"`
result.message.type
enum<string>
default:message
required
Object type.
For Messages, this is always `"message"`.
Available options:
`message`
result.message.role
enum<string>
default:assistant
required
Conversational role of the generated message.
This will always be `"assistant"`.
Available options:
`assistant`
result.message.content
object[]
required
Content generated by the model.
This is an array of content blocks, each of which has a `type` that determines its shape.
Example:
[{"type": "text", "text": "Hi, I'm Claude."}]
If the request input `messages` ended with an `assistant` turn, then the response `content` will continue directly from that last turn. You can use this to constrain the model's output.
For example, if the input `messages` were:
[
{"role": "user", "content": "What's the Greek name for Sun? (A) Sol (B) Helios (C) Sun"},
{"role": "assistant", "content": "The best answer is ("}
]
Then the response `content` might be:
[{"type": "text", "text": "B)"}]
* Thinking
* Redacted thinking
* Tool use
* Server tool use
* Web search tool result
* Code execution tool result
* MCP tool use
* MCP tool result
* Container upload
Show child attributes
result.message.content.signature
string
required
result.message.content.thinking
string
required
result.message.content.type
enum<string>
default:thinking
required
Available options:
`thinking`
Examples:
[
{
"text": "Hi! My name is Claude.",
"type": "text"
}
]
result.message.model
string
required
The model that handled the request.
Required string length: `1 - 256`
Examples:
`"claude-sonnet-4-20250514"`
result.message.stop_reason
enum<string> | null
required
The reason that we stopped.
This may be one the following values:
* `"end_turn"`: the model reached a natural stopping point
* `"max_tokens"`: we exceeded the requested `max_tokens` or the model's maximum
* `"stop_sequence"`: one of your provided custom `stop_sequences` was generated
* `"tool_use"`: the model invoked one or more tools
* `"pause_turn"`: we paused a long-running turn. You may provide the response back as-is in a subsequent request to let the model continue.
* `"refusal"`: when streaming classifiers intervene to handle potential policy violations
In non-streaming mode this value is always non-null. In streaming mode, it is null in the `message_start` event and non-null otherwise.
Available options:
`end_turn`,
`max_tokens`,
`stop_sequence`,
`tool_use`,
`pause_turn`,
`refusal`
result.message.stop_sequence
string | null
required
Which custom stop sequence was generated, if any.
This value will be a non-null string if one of your custom stop sequences was generated.
result.message.usage
object
required
Billing and rate-limit usage.
Anthropic's API bills and rate-limits by token counts, as tokens represent the underlying cost to our systems.
Under the hood, the API transforms requests into a format suitable for the model. The model's output then goes through a parsing stage before becoming an API response. As a result, the token counts in `usage` will not match one-to-one with the exact visible content of an API request or response.
For example, `output_tokens` will be non-zero, even for an empty string response from Claude.
Total input tokens in a request is the summation of `input_tokens`, `cache_creation_input_tokens`, and `cache_read_input_tokens`.
Show child attributes
result.message.usage.cache_creation
object | null
required
Breakdown of cached tokens by TTL
Show child attributes
result.message.usage.cache_creation.ephemeral_1h_input_tokens
integer
default:0
required
The number of input tokens used to create the 1 hour cache entry.
Required range: `x >= 0`
result.message.usage.cache_creation.ephemeral_5m_input_tokens
integer
default:0
required
The number of input tokens used to create the 5 minute cache entry.
Required range: `x >= 0`
result.message.usage.cache_creation_input_tokens
integer | null
required
The number of input tokens used to create the cache entry.
Required range: `x >= 0`
Examples:
`2051`
result.message.usage.cache_read_input_tokens
integer | null
required
The number of input tokens read from the cache.
Required range: `x >= 0`
Examples:
`2051`
result.message.usage.input_tokens
integer
required
The number of input tokens which were used.
Required range: `x >= 0`
Examples:
`2095`
result.message.usage.output_tokens
integer
required
The number of output tokens which were used.
Required range: `x >= 0`
Examples:
`503`
result.message.usage.server_tool_use
object | null
required
The number of server tool requests.
Show child attributes
result.message.usage.server_tool_use.web_search_requests
integer
default:0
required
The number of web search tool requests.
Required range: `x >= 0`
Examples:
`0`
result.message.usage.service_tier
enum<string> | null
required
If the request used the priority, standard, or batch tier.
Available options:
`standard`,
`priority`,
`batch`
result.message.container
object | null
required
Information about the container used in this request.
This will be non-null if a container tool (e.g. code execution) was used.
Show child attributes
result.message.container.expires_at
string
required
The time at which the container will expire.
result.message.container.id
string
required
Identifier for the container used in this request
Examples:
{
"content": [
{
"text": "Hi! My name is Claude.",
"type": "text"
}
],
"id": "msg_013Zva2CMHLNnXjNJJKqJ2EF",
"model": "claude-sonnet-4-20250514",
"role": "assistant",
"stop_reason": "end_turn",
"stop_sequence": null,
"type": "message",
"usage": {
"input_tokens": 2095,
"output_tokens": 503
}
}
result.type
enum<string>
default:succeeded
required
Available options:
`succeeded`
[Retrieve a Message Batch](/en/api/retrieving-message-batches)[List Message Batches](/en/api/listing-message-batches)
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d/results \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{"custom_id":"my-second-request","result":{"type":"succeeded","message":{"id":"msg_014VwiXbi91y3JMjcpyGBHX5","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello again! It's nice to see you. How can I assist you today? Is there anything specific you'd like to chat about or any questions you have?"}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":11,"output_tokens":36}}}}
{"custom_id":"my-first-request","result":{"type":"succeeded","message":{"id":"msg_01FqfsLoHwgeFbguDgpz48m7","type":"message","role":"assistant","model":"claude-3-5-sonnet-20240620","content":[{"type":"text","text":"Hello! How can I assist you today? Feel free to ask me any questions or let me know if there's anything you'd like to chat about."}],"stop_reason":"end_turn","stop_sequence":null,"usage":{"input_tokens":10,"output_tokens":34}}}}

## Retrieve a Message Batch

*Source: https://docs.anthropic.com/en/api/retrieving-message-batches*

Message Batches
Retrieve a Message Batch
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
messages
/
batches
/
{message_batch_id}
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Path Parameters
message_batch_id
string
required
ID of the Message Batch.
#### Response
200
2004XX
application/json
Successful Response
archived_at
string | null
required
RFC 3339 datetime string representing the time at which the Message Batch was archived and its results became unavailable.
Examples:
`"2024-08-20T18:37:24.100435Z"`
cancel_initiated_at
string | null
required
RFC 3339 datetime string representing the time at which cancellation was initiated for the Message Batch. Specified only if cancellation was initiated.
Examples:
`"2024-08-20T18:37:24.100435Z"`
created_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch was created.
Examples:
`"2024-08-20T18:37:24.100435Z"`
ended_at
string | null
required
RFC 3339 datetime string representing the time at which processing for the Message Batch ended. Specified only once processing ends.
Processing ends when every request in a Message Batch has either succeeded, errored, canceled, or expired.
Examples:
`"2024-08-20T18:37:24.100435Z"`
expires_at
string
required
RFC 3339 datetime string representing the time at which the Message Batch will expire and end processing, which is 24 hours after creation.
Examples:
`"2024-08-20T18:37:24.100435Z"`
id
string
required
Unique object identifier.
The format and length of IDs may change over time.
Examples:
`"msgbatch_013Zva2CMHLNnXjNJJKqJ2EF"`
processing_status
enum<string>
required
Processing status of the Message Batch.
Available options:
`in_progress`,
`canceling`,
`ended`
request_counts
object
required
Tallies requests within the Message Batch, categorized by their status.
Requests start as `processing` and move to one of the other statuses only once processing of the entire batch ends. The sum of all values always matches the total number of requests in the batch.
Show child attributes
request_counts.canceled
integer
default:0
required
Number of requests in the Message Batch that have been canceled.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
request_counts.errored
integer
default:0
required
Number of requests in the Message Batch that encountered an error.
This is zero until processing of the entire Message Batch has ended.
Examples:
`30`
request_counts.expired
integer
default:0
required
Number of requests in the Message Batch that have expired.
This is zero until processing of the entire Message Batch has ended.
Examples:
`10`
request_counts.processing
integer
default:0
required
Number of requests in the Message Batch that are processing.
Examples:
`100`
request_counts.succeeded
integer
default:0
required
Number of requests in the Message Batch that have completed successfully.
This is zero until processing of the entire Message Batch has ended.
Examples:
`50`
results_url
string | null
required
URL to a `.jsonl` file containing the results of the Message Batch requests. Specified only once processing ends.
Results in the file are not guaranteed to be in the same order as requests. Use the `custom_id` field to match results to requests.
Examples:
`"https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results"`
type
enum<string>
default:message_batch
required
Object type.
For Message Batches, this is always `"message_batch"`.
Available options:
`message_batch`
[Create a Message Batch](/en/api/creating-message-batches)[Retrieve Message Batch Results](/en/api/retrieving-message-batch-results)
curl https://api.anthropic.com/v1/messages/batches/msgbatch_01HkcTjaV5uDC8jWR4ZsDV8d \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"archived_at": "2024-08-20T18:37:24.100435Z",
"cancel_initiated_at": "2024-08-20T18:37:24.100435Z",
"created_at": "2024-08-20T18:37:24.100435Z",
"ended_at": "2024-08-20T18:37:24.100435Z",
"expires_at": "2024-08-20T18:37:24.100435Z",
"id": "msgbatch_013Zva2CMHLNnXjNJJKqJ2EF",
"processing_status": "in_progress",
"request_counts": {
"canceled": 10,
"errored": 30,
"expired": 10,
"processing": 100,
"succeeded": 50
},
"results_url": "https://api.anthropic.com/v1/messages/batches/msgbatch_013Zva2CMHLNnXjNJJKqJ2EF/results",
"type": "message_batch"
}

## Streaming Text Completions

*Source: https://docs.anthropic.com/en/api/streaming*

Text Completions (Legacy)
Streaming Text Completions
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
**Legacy API**
The Text Completions API is a legacy API. Future models and features will require use of the [Messages API](/en/api/messages), and we recommend [migrating](/en/api/migrating-from-text-completions-to-messages) as soon as possible.
When creating a Text Completion, you can set `"stream": true` to incrementally stream the response using (SSE). If you are using our [client libraries](/en/api/client-sdks), parsing these events will be handled for you automatically. However, if you are building a direct API integration, you will need to handle these events yourself.
curl https://api.anthropic.com/v1/complete \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--data '
{
"model": "claude-2",
"prompt": "\n\nHuman: Hello, world!\n\nAssistant:",
"max_tokens_to_sample": 256,
"stream": true
}
'
event: completion
data: {"type": "completion", "completion": " Hello", "stop_reason": null, "model": "claude-2.0"}
event: completion
data: {"type": "completion", "completion": "!", "stop_reason": null, "model": "claude-2.0"}
event: ping
data: {"type": "ping"}
event: completion
data: {"type": "completion", "completion": " My", "stop_reason": null, "model": "claude-2.0"}
event: completion
data: {"type": "completion", "completion": " name", "stop_reason": null, "model": "claude-2.0"}
event: completion
data: {"type": "completion", "completion": " is", "stop_reason": null, "model": "claude-2.0"}
event: completion
data: {"type": "completion", "completion": " Claude", "stop_reason": null, "model": "claude-2.0"}
event: completion
data: {"type": "completion", "completion": ".", "stop_reason": null, "model": "claude-2.0"}
event: completion
data: {"type": "completion", "completion": "", "stop_reason": "stop_sequence", "model": "claude-2.0"}
Each event includes a named event type and associated JSON data.
Event types: `completion`, `ping`, `error`.
###
Error event types
We may occasionally send [errors](/en/api/errors) in the event stream. For example, during periods of high usage, you may receive an `overloaded_error`, which would normally correspond to an HTTP 529 in a non-streaming context:
Example error
event: completion
data: {"completion": " Hello", "stop_reason": null, "model": "claude-2.0"}
event: error
data: {"error": {"type": "overloaded_error", "message": "Overloaded"}}
Older API versions
If you are using an [API version](/en/api/versioning) prior to `2023-06-01`, the response shape will be different. See [versioning](/en/api/versioning) for details.
[Create a Text Completion](/en/api/complete)[Prompt validation](/en/api/prompt-validation)

---

# Models

## Get a Model

*Source: https://docs.anthropic.com/en/api/models*

Get a Model
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
models
/
{model_id}
curl https://api.anthropic.com/v1/models/claude-sonnet-4-20250514 \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"created_at": "2025-02-19T00:00:00Z",
"display_name": "Claude Sonnet 4",
"id": "claude-sonnet-4-20250514",
"type": "model"
}
#### Headers
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
#### Path Parameters
model_id
string
required
Model identifier or alias.
#### Response
200
2004XX
application/json
Successful Response
created_at
string
required
RFC 3339 datetime string representing the time at which the model was released. May be set to an epoch value if the release date is unknown.
Examples:
`"2025-02-19T00:00:00Z"`
display_name
string
required
A human-readable name for the model.
Examples:
`"Claude Sonnet 4"`
id
string
required
Unique model identifier.
Examples:
`"claude-sonnet-4-20250514"`
type
enum<string>
default:model
required
Object type.
For Models, this is always `"model"`.
Available options:
`model`
[List Models](/en/api/models-list)[Create a Message Batch](/en/api/creating-message-batches)
curl https://api.anthropic.com/v1/models/claude-sonnet-4-20250514 \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"created_at": "2025-02-19T00:00:00Z",
"display_name": "Claude Sonnet 4",
"id": "claude-sonnet-4-20250514",
"type": "model"
}

## List Models

*Source: https://docs.anthropic.com/en/api/models-list*

List Models
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
models
curl https://api.anthropic.com/v1/models \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"data": [
{
"created_at": "2025-02-19T00:00:00Z",
"display_name": "Claude Sonnet 4",
"id": "claude-sonnet-4-20250514",
"type": "model"
}
],
"first_id": "<string>",
"has_more": true,
"last_id": "<string>"
}
#### Headers
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
#### Query Parameters
before_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.
after_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.
limit
integer
default:20
Number of items to return per page.
Defaults to `20`. Ranges from `1` to `1000`.
Required range: `1 <= x <= 1000`
#### Response
200
2004XX
application/json
Successful Response
data
object[]
required
Show child attributes
data.created_at
string
required
RFC 3339 datetime string representing the time at which the model was released. May be set to an epoch value if the release date is unknown.
Examples:
`"2025-02-19T00:00:00Z"`
data.display_name
string
required
A human-readable name for the model.
Examples:
`"Claude Sonnet 4"`
data.id
string
required
Unique model identifier.
Examples:
`"claude-sonnet-4-20250514"`
data.type
enum<string>
default:model
required
Object type.
For Models, this is always `"model"`.
Available options:
`model`
first_id
string | null
required
First ID in the `data` list. Can be used as the `before_id` for the previous page.
has_more
boolean
required
Indicates if there are more results in the requested page direction.
last_id
string | null
required
Last ID in the `data` list. Can be used as the `after_id` for the next page.
[Count Message tokens](/en/api/messages-count-tokens)[Get a Model](/en/api/models)
curl https://api.anthropic.com/v1/models \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01"
{
"data": [
{
"created_at": "2025-02-19T00:00:00Z",
"display_name": "Claude Sonnet 4",
"id": "claude-sonnet-4-20250514",
"type": "model"
}
],
"first_id": "<string>",
"has_more": true,
"last_id": "<string>"
}

---

# Files

## Download a File

*Source: https://docs.anthropic.com/en/api/files-content*

Download a File
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
files
/
{file_id}
/
content
curl "https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w/content" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14" \
--output downloaded_file.pdf
"<string>"
The Files API allows you to upload and manage files to use with the Anthropic API without having to re-upload content with each request. For more information about the Files API, see the .
The Files API is currently in beta. To use the Files API, you’ll need to include the beta feature header: `anthropic-beta: files-api-2025-04-14`.
Please reach out through our to share your experience with the Files API.
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Path Parameters
file_id
string
required
ID of the File.
#### Response
200
2004XX
application/octet-stream
Successful Response
The response is of type `string`.
[Get File Metadata](/en/api/files-metadata)[Delete a File](/en/api/files-delete)
curl "https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w/content" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14" \
--output downloaded_file.pdf
"<string>"

## Create a File

*Source: https://docs.anthropic.com/en/api/files-create*

Create a File
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
files
curl -X POST "https://api.anthropic.com/v1/files" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14" \
-F "file=@/path/to/document.pdf"
{
"created_at": "2023-11-07T05:31:56Z",
"downloadable": false,
"filename": "<string>",
"id": "<string>",
"mime_type": "<string>",
"size_bytes": 1,
"type": "file"
}
The Files API allows you to upload and manage files to use with the Anthropic API without having to re-upload content with each request. For more information about the Files API, see the .
The Files API is currently in beta. To use the Files API, you’ll need to include the beta feature header: `anthropic-beta: files-api-2025-04-14`.
Please reach out through our to share your experience with the Files API.
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Body
multipart/form-data
file
file
required
The file to upload
#### Response
200
2004XX
application/json
Successful Response
created_at
string
required
RFC 3339 datetime string representing when the file was created.
filename
string
required
Original filename of the uploaded file.
Required string length: `1 - 500`
id
string
required
Unique object identifier.
The format and length of IDs may change over time.
mime_type
string
required
MIME type of the file.
Required string length: `1 - 255`
size_bytes
integer
required
Size of the file in bytes.
Required range: `x >= 0`
type
enum<string>
required
Object type.
For files, this is always `"file"`.
Available options:
`file`
downloadable
boolean
default:false
Whether the file can be downloaded.
[Delete a Message Batch](/en/api/deleting-message-batches)[List Files](/en/api/files-list)
curl -X POST "https://api.anthropic.com/v1/files" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14" \
-F "file=@/path/to/document.pdf"
{
"created_at": "2023-11-07T05:31:56Z",
"downloadable": false,
"filename": "<string>",
"id": "<string>",
"mime_type": "<string>",
"size_bytes": 1,
"type": "file"
}

## Delete a File

*Source: https://docs.anthropic.com/en/api/files-delete*

Delete a File
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
DELETE
/
v1
/
files
/
{file_id}
curl -X DELETE "https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14"
{
"id": "<string>",
"type": "file_deleted"
}
The Files API allows you to upload and manage files to use with the Anthropic API without having to re-upload content with each request. For more information about the Files API, see the .
The Files API is currently in beta. To use the Files API, you’ll need to include the beta feature header: `anthropic-beta: files-api-2025-04-14`.
Please reach out through our to share your experience with the Files API.
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Path Parameters
file_id
string
required
ID of the File.
#### Response
200
2004XX
application/json
Successful Response
id
string
required
ID of the deleted file.
type
enum<string>
default:file_deleted
Deleted object type.
For file deletion, this is always `"file_deleted"`.
Available options:
`file_deleted`
[Download a File](/en/api/files-content)[Get User](/en/api/admin-api/users/get-user)
curl -X DELETE "https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14"
{
"id": "<string>",
"type": "file_deleted"
}

## List Files

*Source: https://docs.anthropic.com/en/api/files-list*

List Files
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
files
curl "https://api.anthropic.com/v1/files" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14"
{
"data": [
{
"created_at": "2023-11-07T05:31:56Z",
"downloadable": false,
"filename": "<string>",
"id": "<string>",
"mime_type": "<string>",
"size_bytes": 1,
"type": "file"
}
],
"first_id": "<string>",
"has_more": false,
"last_id": "<string>"
}
The Files API allows you to upload and manage files to use with the Anthropic API without having to re-upload content with each request. For more information about the Files API, see the .
The Files API is currently in beta. To use the Files API, you’ll need to include the beta feature header: `anthropic-beta: files-api-2025-04-14`.
Please reach out through our to share your experience with the Files API.
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Query Parameters
before_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.
after_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.
limit
integer
default:20
Number of items to return per page.
Defaults to `20`. Ranges from `1` to `1000`.
Required range: `1 <= x <= 1000`
#### Response
200
2004XX
application/json
Successful Response
data
object[]
required
List of file metadata objects.
Show child attributes
data.created_at
string
required
RFC 3339 datetime string representing when the file was created.
data.filename
string
required
Original filename of the uploaded file.
Required string length: `1 - 500`
data.id
string
required
Unique object identifier.
The format and length of IDs may change over time.
data.mime_type
string
required
MIME type of the file.
Required string length: `1 - 255`
data.size_bytes
integer
required
Size of the file in bytes.
Required range: `x >= 0`
data.type
enum<string>
required
Object type.
For files, this is always `"file"`.
Available options:
`file`
data.downloadable
boolean
default:false
Whether the file can be downloaded.
first_id
string | null
ID of the first file in this page of results.
has_more
boolean
default:false
Whether there are more results available.
last_id
string | null
ID of the last file in this page of results.
[Create a File](/en/api/files-create)[Get File Metadata](/en/api/files-metadata)
curl "https://api.anthropic.com/v1/files" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14"
{
"data": [
{
"created_at": "2023-11-07T05:31:56Z",
"downloadable": false,
"filename": "<string>",
"id": "<string>",
"mime_type": "<string>",
"size_bytes": 1,
"type": "file"
}
],
"first_id": "<string>",
"has_more": false,
"last_id": "<string>"
}

## Get File Metadata

*Source: https://docs.anthropic.com/en/api/files-metadata*

Get File Metadata
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
files
/
{file_id}
curl "https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14"
{
"created_at": "2023-11-07T05:31:56Z",
"downloadable": false,
"filename": "<string>",
"id": "<string>",
"mime_type": "<string>",
"size_bytes": 1,
"type": "file"
}
The Files API allows you to upload and manage files to use with the Anthropic API without having to re-upload content with each request. For more information about the Files API, see the .
The Files API is currently in beta. To use the Files API, you’ll need to include the beta feature header: `anthropic-beta: files-api-2025-04-14`.
Please reach out through our to share your experience with the Files API.
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Path Parameters
file_id
string
required
ID of the File.
#### Response
200
2004XX
application/json
Successful Response
created_at
string
required
RFC 3339 datetime string representing when the file was created.
filename
string
required
Original filename of the uploaded file.
Required string length: `1 - 500`
id
string
required
Unique object identifier.
The format and length of IDs may change over time.
mime_type
string
required
MIME type of the file.
Required string length: `1 - 255`
size_bytes
integer
required
Size of the file in bytes.
Required range: `x >= 0`
type
enum<string>
required
Object type.
For files, this is always `"file"`.
Available options:
`file`
downloadable
boolean
default:false
Whether the file can be downloaded.
[List Files](/en/api/files-list)[Download a File](/en/api/files-content)
curl "https://api.anthropic.com/v1/files/file_011CNha8iCJcU1wXNR6q4V8w" \
-H "x-api-key: $ANTHROPIC_API_KEY" \
-H "anthropic-version: 2023-06-01" \
-H "anthropic-beta: files-api-2025-04-14"
{
"created_at": "2023-11-07T05:31:56Z",
"downloadable": false,
"filename": "<string>",
"id": "<string>",
"mime_type": "<string>",
"size_bytes": 1,
"type": "file"
}

---

# Administration

## Get User

*Source: https://docs.anthropic.com/en/api/admin-api*

Get User
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
organizations
/
users
/
{user_id}
curl "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user",
"email": "user@emaildomain.com",
"name": "Jane Doe",
"role": "user",
"added_at": "2024-10-30T23:58:27.427722Z"
}
#### Headers
x-api-key
string
required
Your unique Admin API key for authentication.
This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
#### Path Parameters
user_id
string
required
ID of the User.
#### Response
200
2004XX
application/json
Successful Response
id
string
required
ID of the User.
Examples:
`"user_01WCz1FkmYMm4gnmykNKUu3Q"`
type
enum<string>
default:user
required
Object type.
For Users, this is always `"user"`.
Available options:
`user`
email
string
required
Email of the User.
Examples:
`"user@emaildomain.com"`
name
string
required
Name of the User.
Examples:
`"Jane Doe"`
role
enum<string>
required
Organization role of the User.
Available options:
`user`,
`developer`,
`billing`,
`admin`
Examples:
`"user"`
`"developer"`
`"billing"`
`"admin"`
added_at
string
required
RFC 3339 datetime string indicating when the User joined the Organization.
Examples:
`"2024-10-30T23:58:27.427722Z"`
[Delete a File](/en/api/files-delete)[List Users](/en/api/admin-api/users/list-users)
curl "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user",
"email": "user@emaildomain.com",
"name": "Jane Doe",
"role": "user",
"added_at": "2024-10-30T23:58:27.427722Z"
}

## Get Invite

*Source: https://docs.anthropic.com/en/api/admin-api/invites/get-invite*

Organization Invites
Get Invite
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
organizations
/
invites
/
{invite_id}
curl "https://api.anthropic.com/v1/organizations/invites/invite_015gWxCN9Hfg2QhZwTK7Mdeu" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"id": "invite_015gWxCN9Hfg2QhZwTK7Mdeu",
"type": "invite",
"email": "user@emaildomain.com",
"role": "user",
"invited_at": "2024-10-30T23:58:27.427722Z",
"expires_at": "2024-11-20T23:58:27.427722Z",
"status": "pending"
}
**The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.
#### Headers
x-api-key
string
required
Your unique Admin API key for authentication.
This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
#### Path Parameters
invite_id
string
required
ID of the Invite.
#### Response
200
2004XX
application/json
Successful Response
id
string
required
ID of the Invite.
Examples:
`"invite_015gWxCN9Hfg2QhZwTK7Mdeu"`
type
enum<string>
default:invite
required
Object type.
For Invites, this is always `"invite"`.
Available options:
`invite`
email
string
required
Email of the User being invited.
Examples:
`"user@emaildomain.com"`
role
enum<string>
required
Organization role of the User.
Available options:
`user`,
`developer`,
`billing`,
`admin`
Examples:
`"user"`
`"developer"`
`"billing"`
`"admin"`
invited_at
string
required
RFC 3339 datetime string indicating when the Invite was created.
Examples:
`"2024-10-30T23:58:27.427722Z"`
expires_at
string
required
RFC 3339 datetime string indicating when the Invite expires.
Examples:
`"2024-11-20T23:58:27.427722Z"`
status
enum<string>
required
Status of the Invite.
Available options:
`accepted`,
`expired`,
`deleted`,
`pending`
Examples:
`"pending"`
[Remove User](/en/api/admin-api/users/remove-user)[List Invites](/en/api/admin-api/invites/list-invites)
curl "https://api.anthropic.com/v1/organizations/invites/invite_015gWxCN9Hfg2QhZwTK7Mdeu" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"id": "invite_015gWxCN9Hfg2QhZwTK7Mdeu",
"type": "invite",
"email": "user@emaildomain.com",
"role": "user",
"invited_at": "2024-10-30T23:58:27.427722Z",
"expires_at": "2024-11-20T23:58:27.427722Z",
"status": "pending"
}

## List Users

*Source: https://docs.anthropic.com/en/api/admin-api/users/list-users*

List Users
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
GET
/
v1
/
organizations
/
users
curl "https://api.anthropic.com/v1/organizations/users" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"data": [
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user",
"email": "user@emaildomain.com",
"name": "Jane Doe",
"role": "user",
"added_at": "2024-10-30T23:58:27.427722Z"
}
],
"has_more": true,
"first_id": "<string>",
"last_id": "<string>"
}
#### Headers
x-api-key
string
required
Your unique Admin API key for authentication.
This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
#### Query Parameters
before_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately before this object.
after_id
string
ID of the object to use as a cursor for pagination. When provided, returns the page of results immediately after this object.
limit
integer
default:20
Number of items to return per page.
Defaults to `20`. Ranges from `1` to `1000`.
Required range: `1 <= x <= 1000`
email
string
Filter by user email.
#### Response
200
2004XX
application/json
Successful Response
data
object[]
required
Show child attributes
data.id
string
required
ID of the User.
Examples:
`"user_01WCz1FkmYMm4gnmykNKUu3Q"`
data.type
enum<string>
default:user
required
Object type.
For Users, this is always `"user"`.
Available options:
`user`
data.email
string
required
Email of the User.
Examples:
`"user@emaildomain.com"`
data.name
string
required
Name of the User.
Examples:
`"Jane Doe"`
data.role
enum<string>
required
Organization role of the User.
Available options:
`user`,
`developer`,
`billing`,
`admin`
Examples:
`"user"`
`"developer"`
`"billing"`
`"admin"`
data.added_at
string
required
RFC 3339 datetime string indicating when the User joined the Organization.
Examples:
`"2024-10-30T23:58:27.427722Z"`
has_more
boolean
required
Indicates if there are more results in the requested page direction.
first_id
string | null
required
First ID in the `data` list. Can be used as the `before_id` for the previous page.
last_id
string | null
required
Last ID in the `data` list. Can be used as the `after_id` for the next page.
[Get User](/en/api/admin-api/users/get-user)[Update User](/en/api/admin-api/users/update-user)
curl "https://api.anthropic.com/v1/organizations/users" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"data": [
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user",
"email": "user@emaildomain.com",
"name": "Jane Doe",
"role": "user",
"added_at": "2024-10-30T23:58:27.427722Z"
}
],
"has_more": true,
"first_id": "<string>",
"last_id": "<string>"
}

## Remove User

*Source: https://docs.anthropic.com/en/api/admin-api/users/remove-user*

Remove User
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
DELETE
/
v1
/
organizations
/
users
/
{user_id}
curl --request DELETE "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user_deleted"
}
#### Headers
x-api-key
string
required
Your unique Admin API key for authentication.
This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
#### Path Parameters
user_id
string
required
ID of the User.
#### Response
200
2004XX
application/json
Successful Response
id
string
required
ID of the User.
Examples:
`"user_01WCz1FkmYMm4gnmykNKUu3Q"`
type
enum<string>
default:user_deleted
required
Deleted object type.
For Users, this is always `"user_deleted"`.
Available options:
`user_deleted`
[Update User](/en/api/admin-api/users/update-user)[Get Invite](/en/api/admin-api/invites/get-invite)
curl --request DELETE "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user_deleted"
}

## Update User

*Source: https://docs.anthropic.com/en/api/admin-api/users/update-user*

Update User
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
organizations
/
users
/
{user_id}
curl "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{
"role": "user"
}'
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user",
"email": "user@emaildomain.com",
"name": "Jane Doe",
"role": "user",
"added_at": "2024-10-30T23:58:27.427722Z"
}
#### Headers
x-api-key
string
required
Your unique Admin API key for authentication.
This key is required in the header of all Admin API requests, to authenticate your account and access Anthropic's services. Get your Admin API key through the [Console](https://console.anthropic.com/settings/admin-keys).
anthropic-version
string
required
The version of the Anthropic API you want to use.
Read more about versioning and our version history [here](https://docs.anthropic.com/en/api/versioning).
#### Path Parameters
user_id
string
required
ID of the User.
#### Body
application/json
role
enum<string>
required
New role for the User. Cannot be "admin".
Available options:
`user`,
`developer`,
`billing`
Examples:
`"user"`
`"developer"`
`"billing"`
#### Response
200
2004XX
application/json
Successful Response
id
string
required
ID of the User.
Examples:
`"user_01WCz1FkmYMm4gnmykNKUu3Q"`
type
enum<string>
default:user
required
Object type.
For Users, this is always `"user"`.
Available options:
`user`
email
string
required
Email of the User.
Examples:
`"user@emaildomain.com"`
name
string
required
Name of the User.
Examples:
`"Jane Doe"`
role
enum<string>
required
Organization role of the User.
Available options:
`user`,
`developer`,
`billing`,
`admin`
Examples:
`"user"`
`"developer"`
`"billing"`
`"admin"`
added_at
string
required
RFC 3339 datetime string indicating when the User joined the Organization.
Examples:
`"2024-10-30T23:58:27.427722Z"`
[List Users](/en/api/admin-api/users/list-users)[Remove User](/en/api/admin-api/users/remove-user)
curl "https://api.anthropic.com/v1/organizations/users/user_01WCz1FkmYMm4gnmykNKUu3Q" \
--header "anthropic-version: 2023-06-01" \
--header "content-type: application/json" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{
"role": "user"
}'
{
"id": "user_01WCz1FkmYMm4gnmykNKUu3Q",
"type": "user",
"email": "user@emaildomain.com",
"name": "Jane Doe",
"role": "user",
"added_at": "2024-10-30T23:58:27.427722Z"
}

## Using the Admin

*Source: https://docs.anthropic.com/en/api/administration-api*

Using the Admin API
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
**The Admin API is unavailable for individual accounts.** To collaborate with teammates and add members, set up your organization in **Console → Settings → Organization**.
**The Admin API requires special access**
The Admin API requires a special Admin API key (starting with `sk-ant-admin...`) that differs from standard API keys. Only organization members with the admin role can provision Admin API keys through the Anthropic Console.
How the Admin API works
When you use the Admin API:
1. You make requests using your Admin API key in the `x-api-key` header
2. The API allows you to manage:
* Organization members and their roles
* Organization member invites
* Workspaces and their members
* API keys
This is useful for:
* Automating user onboarding/offboarding
* Programmatically managing workspace access
* Monitoring and managing API key usage
Organization roles and permissions
There are five organization-level roles. See more details [here](https://support.anthropic.com/en/articles/10186004-api-console-roles-and-permissions).
Role| Permissions
---|---
user| Can use Workbench
claude_code_user| Can use Workbench and
developer| Can use Workbench and manage API keys
billing| Can use Workbench and manage billing details
admin| Can do all of the above, plus manage users
Key concepts
###
Organization Members
You can list organization members, update member roles, and remove members.
# List organization members
curl "https://api.anthropic.com/v1/organizations/users?limit=10" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
# Update member role
curl "https://api.anthropic.com/v1/organizations/users/{user_id}" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{"role": "developer"}'
# Remove member
curl --request DELETE "https://api.anthropic.com/v1/organizations/users/{user_id}" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
###
Organization Invites
You can invite users to organizations and manage those invites.
# Create invite
curl --request POST "https://api.anthropic.com/v1/organizations/invites" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{
"email": "newuser@domain.com",
"role": "developer"
}'
# List invites
curl "https://api.anthropic.com/v1/organizations/invites?limit=10" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
# Delete invite
curl --request DELETE "https://api.anthropic.com/v1/organizations/invites/{invite_id}" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
###
# Create workspace
curl --request POST "https://api.anthropic.com/v1/organizations/workspaces" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{"name": "Production"}'
# List workspaces
curl "https://api.anthropic.com/v1/organizations/workspaces?limit=10&include_archived=false" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
# Archive workspace
curl --request POST "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/archive" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
###
Workspace Members
Manage user access to specific workspaces:
# Add member to workspace
curl --request POST "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{
"user_id": "user_xxx",
"workspace_role": "workspace_developer"
}'
# List workspace members
curl "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members?limit=10" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
# Update member role
curl --request POST "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members/{user_id}" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{
"workspace_role": "workspace_admin"
}'
# Remove member from workspace
curl --request DELETE "https://api.anthropic.com/v1/organizations/workspaces/{workspace_id}/members/{user_id}" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
###
API Keys
Monitor and manage API keys:
# List API keys
curl "https://api.anthropic.com/v1/organizations/api_keys?limit=10&status=active&workspace_id=wrkspc_xxx" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY"
# Update API key
curl --request POST "https://api.anthropic.com/v1/organizations/api_keys/{api_key_id}" \
--header "anthropic-version: 2023-06-01" \
--header "x-api-key: $ANTHROPIC_ADMIN_KEY" \
--data '{
"status": "inactive",
"name": "New Key Name"
}'
Best practices
To effectively use the Admin API:
* Use meaningful names and descriptions for workspaces and API keys
* Implement proper error handling for failed operations
* Regularly audit member roles and permissions
* Clean up unused workspaces and expired invites
* Monitor API key usage and rotate keys periodically
FAQ
What permissions are needed to use the Admin API?
Only organization members with the admin role can use the Admin API. They must also have a special Admin API key (starting with `sk-ant-admin`).
Can I create new API keys through the Admin API?
No, new API keys can only be created through the Anthropic Console for security reasons. The Admin API can only manage existing API keys.
What happens to API keys when removing a user?
API keys persist in their current state as they are scoped to the Organization, not to individual users.
Can organization admins be removed via the API?
No, organization members with the admin role cannot be removed via the API for security reasons.
How long do organization invites last?
Organization invites expire after 21 days. There is currently no way to modify this expiration period.
Are there limits on workspaces?
Yes, you can have a maximum of 100 workspaces per Organization. Archived workspaces do not count towards this limit.
What's the Default Workspace?
Every Organization has a “Default Workspace” that cannot be edited or removed, and has no ID. This Workspace does not appear in workspace list endpoints.
How do organization roles affect Workspace access?
Organization admins automatically get the `workspace_admin` role to all workspaces. Organization billing members automatically get the `workspace_billing` role. Organization users and developers must be manually added to each workspace.
Which roles can be assigned in workspaces?
Organization users and developers can be assigned `workspace_admin`, `workspace_developer`, or `workspace_user` roles. The `workspace_billing` role can’t be manually assigned - it’s inherited from having the organization `billing` role.
Can organization admin or billing members' workspace roles be changed?
Only organization billing members can have their workspace role upgraded to an admin role. Otherwise, organization admins and billing members can’t have their workspace roles changed or be removed from workspaces while they hold those organization roles. Their workspace access must be modified by changing their organization role first.
What happens to workspace access when organization roles change?
If an organization admin or billing member is demoted to user or developer, they lose access to all workspaces except ones where they were manually assigned roles. When users are promoted to admin or billing roles, they gain automatic access to all workspaces.
[](/en/api/supported-regions)[Getting help](/en/api/getting-help)

---

# Advanced Features

## Beta headers

*Source: https://docs.anthropic.com/en/api/beta-headers*

Beta headers
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
Beta headers allow you to access experimental features and new model capabilities before they become part of the standard API.
These features are subject to change and may be modified or removed in future releases.
Beta headers are often used in conjunction with the [beta namespace in the client SDKs](/en/api/client-sdks#beta-namespace-in-client-sdks)
How to use beta headers
To access beta features, include the `anthropic-beta` header in your API requests:
POST /v1/messages
When using the SDK, you can specify beta headers in the request options:
from anthropic import Anthropic
client = Anthropic()
response = client.beta.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
messages=[
{"role": "user", "content": "Hello, Claude"}
],
betas=["beta-feature-name"]
)
Beta features are experimental and may:
* Have breaking changes without notice
* Be deprecated or removed
* Have different rate limits or pricing
* Not be available in all regions
###
Multiple beta features
To use multiple beta features in a single request, include all feature names in the header separated by commas:
###
Version naming conventions
Beta feature names typically follow the pattern: `feature-name-YYYY-MM-DD`, where the date indicates when the beta version was released. Always use the exact beta feature name as documented.
Error handling
If you use an invalid or unavailable beta header, you’ll receive an error response:
{
"type": "error",
"error": {
"type": "invalid_request_error",
"message":
}
}
Getting help
For questions about beta features:
1. Review the [API changelog](/en/api/versioning) for updates
Remember that beta features are provided “as-is” and may not have the same SLA guarantees as stable API features.
[Handling stop reasons](/en/api/handling-stop-reasons)[Messages](/en/api/messages)

## Generate a prompt

*Source: https://docs.anthropic.com/en/api/prompt-tools-generate*

Prompt tools
Generate a prompt
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
experimental
/
generate_prompt
curl -X POST https://api.anthropic.com/v1/experimental/generate_prompt \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "anthropic-beta: prompt-tools-2025-04-02" \
--header "content-type: application/json" \
--data \
'{
"task": "a chef for a meal prep planning service",
"target_model": "claude-3-7-sonnet-20250219"
}'
{
"messages": [
{
"content": [
{
"text": "<generated prompt>",
"type": "text"
}
],
"role": "user"
}
],
"system": "",
"usage": [
{
"input_tokens": 490,
"output_tokens": 661
}
]
}
The prompt tools APIs are in a closed research preview. .
Before you begin
These APIs are similar to what’s available in the [Anthropic Workbench](https://console.anthropic.com/workbench), and are intended for use by other prompt engineering platforms and playgrounds.
Getting started with the prompt generator
To use the prompt generation API, you’ll need to:
1. Have joined the closed research preview for the prompt tools APIs
2. Use the API directly, rather than the SDK
3. Add the beta header `prompt-tools-2025-04-02`
This API is not available in the SDK
Generate a prompt
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Body
application/json
task
string
required
Description of the prompt's purpose.
The `task` parameter tells Claude what the prompt should do or what kind of role or functionality you want to create. This helps guide the prompt generation process toward your intended use case.
Example:
{"task": "a chef for a meal prep planning service"}
Examples:
`"a chef for a meal prep planning service"`
target_model
string | null
default:
The model this prompt will be used for. This optional parameter helps us understand which models our prompt tools are being used with, but it doesn't currently affect functionality.
Example:
"claude-3-7-sonnet-20250219"
Required string length: `1 - 256`
Examples:
`"claude-3-7-sonnet-20250219"`
#### Response
200
2004XX
application/json
Successful Response
messages
object[]
required
The response contains a list of message objects in the same format used by the Messages API. Typically includes a user message with the complete generated prompt text, and may include an assistant message with a prefill to guide the model's initial response.
These messages can be used directly in a Messages API request to start a conversation with the generated prompt.
Example:
{
"messages": [
{
"role": "user",
"content": [
{
"type": "text",
"text": "You are a chef for a meal prep planning service..."
}
]
},
{
"role": "assistant",
"content": [
{
"type": "text",
"text": "<recipe_planning>"
}
]
}
]
}
Show child attributes
messages.content
required
messages.role
enum<string>
required
Available options:
`user`,
`assistant`
Examples:
[
{
"content": [
{
"text": "<generated prompt>",
"type": "text"
}
],
"role": "user"
}
]
system
string
default:
required
Currently, the `system` field is always returned as an empty string (""). In future iterations, this field may contain generated system prompts.
Directions similar to what would normally be included in a system prompt are included in `messages` when generating a prompt.
Examples:
`""`
usage
object
required
Usage information
Show child attributes
usage.cache_creation
object | null
required
Breakdown of cached tokens by TTL
Show child attributes
usage.cache_creation.ephemeral_1h_input_tokens
integer
default:0
required
The number of input tokens used to create the 1 hour cache entry.
Required range: `x >= 0`
usage.cache_creation.ephemeral_5m_input_tokens
integer
default:0
required
The number of input tokens used to create the 5 minute cache entry.
Required range: `x >= 0`
usage.cache_creation_input_tokens
integer | null
required
The number of input tokens used to create the cache entry.
Required range: `x >= 0`
Examples:
`2051`
usage.cache_read_input_tokens
integer | null
required
The number of input tokens read from the cache.
Required range: `x >= 0`
Examples:
`2051`
usage.input_tokens
integer
required
The number of input tokens which were used.
Required range: `x >= 0`
Examples:
`2095`
usage.output_tokens
integer
required
The number of output tokens which were used.
Required range: `x >= 0`
Examples:
`503`
usage.server_tool_use
object | null
required
The number of server tool requests.
Show child attributes
usage.server_tool_use.web_search_requests
integer
default:0
required
The number of web search tool requests.
Required range: `x >= 0`
Examples:
`0`
usage.service_tier
enum<string> | null
required
If the request used the priority, standard, or batch tier.
Available options:
`standard`,
`priority`,
`batch`
[Update API Keys](/en/api/admin-api/apikeys/update-api-key)[Improve a prompt](/en/api/prompt-tools-improve)
curl -X POST https://api.anthropic.com/v1/experimental/generate_prompt \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "anthropic-beta: prompt-tools-2025-04-02" \
--header "content-type: application/json" \
--data \
'{
"task": "a chef for a meal prep planning service",
"target_model": "claude-3-7-sonnet-20250219"
}'
{
"messages": [
{
"content": [
{
"text": "<generated prompt>",
"type": "text"
}
],
"role": "user"
}
],
"system": "",
"usage": [
{
"input_tokens": 490,
"output_tokens": 661
}
]
}

## Improve a prompt

*Source: https://docs.anthropic.com/en/api/prompt-tools-improve*

Prompt tools
Improve a prompt
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
experimental
/
improve_prompt
curl -X POST https://api.anthropic.com/v1/experimental/improve_prompt \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "anthropic-beta: prompt-tools-2025-04-02" \
--header "content-type: application/json" \
--data \
'{
"messages": [{"role": "user", "content": [{"type": "text", "text": "Create a recipe for {{food}}"}]}],
"system": "You are a professional chef",
"feedback": "Make it more detailed and include cooking times",
"target_model": "claude-3-7-sonnet-20250219"
}'
{
"messages": [
{
"content": [
{
"text": "<improved prompt>",
"type": "text"
}
],
"role": "user"
},
{
"content": [
{
"text": "<assistant prefill>",
"type": "text"
}
],
"role": "assistant"
}
],
"system": "",
"usage": [
{
"input_tokens": 490,
"output_tokens": 661
}
]
}
The prompt tools APIs are in a closed research preview. .
Before you begin
These APIs are similar to what’s available in the [Anthropic Workbench](https://console.anthropic.com/workbench), and are intended for use by other prompt engineering platforms and playgrounds.
Getting started with the prompt improver
To use the prompt generation API, you’ll need to:
1. Have joined the closed research preview for the prompt tools APIs
2. Use the API directly, rather than the SDK
3. Add the beta header `prompt-tools-2025-04-02`
This API is not available in the SDK
Improve a prompt
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Body
application/json
messages
object[]
required
The prompt to improve, structured as a list of `message` objects.
Each message in the `messages` array must:
* Contain only text-only content blocks
* Not include tool calls, images, or prompt caching blocks
As a simple text prompt:
[
{
"role": "user",
"content": [
{
"type": "text",
"text": "Concise recipe for {{food}}"
}
]
}
]
With example interactions to guide improvement:
[
{
"role": "user",
"content": [
{
"type": "text",
"text": "Concise for {{food}}.\n\nexample\mandu: Put the mandu in the air fryer at 380F for 7 minutes."
}
]
}
]
Note that only contiguous user messages with text content are allowed. Assistant prefill is permitted, but other content types will cause validation errors.
Show child attributes
messages.content
required
messages.role
enum<string>
required
Available options:
`user`,
`assistant`
Examples:
[
{
"content": [
{
"text": "<generated prompt>",
"type": "text"
}
],
"role": "user"
}
]
feedback
string | null
Feedback for improving the prompt.
Use this parameter to share specific guidance on what aspects of the prompt should be enhanced or modified.
Example:
{
"messages": [...],
"feedback": "Make the recipes shorter"
}
When not set, the API will improve the prompt using general prompt engineering best practices.
Examples:
`"Make it more detailed and include cooking times"`
system
string | null
The existing system prompt to incorporate, if any.
{
"system": "You are a professional meal prep chef",
[...]
}
Note that while system prompts typically appear as separate parameters in standard API calls, in the `improve_prompt` response, the system content will be incorporated directly into the returned user message.
Examples:
`"You are a professional chef"`
target_model
string | null
default:
The model this prompt will be used for. This optional parameter helps us understand which models our prompt tools are being used with, but it doesn't currently affect functionality.
Example:
"claude-3-7-sonnet-20250219"
Required string length: `1 - 256`
Examples:
`"claude-3-7-sonnet-20250219"`
#### Response
200
2004XX
application/json
Successful Response
messages
object[]
required
Contains the result of the prompt improvement process in a list of `message` objects.
Includes a `user`-role message with the improved prompt text and may optionally include an `assistant`-role message with a prefill. These messages follow the standard Messages API format and can be used directly in subsequent API calls.
Show child attributes
messages.content
required
messages.role
enum<string>
required
Available options:
`user`,
`assistant`
Examples:
[
{
"content": [
{
"text": "<improved prompt>",
"type": "text"
}
],
"role": "user"
},
{
"content": [
{
"text": "<assistant prefill>",
"type": "text"
}
],
"role": "assistant"
}
]
system
string
required
Currently, the `system` field is always returned as an empty string (""). In future iterations, this field may contain generated system prompts.
Directions similar to what would normally be included in a system prompt are included in `messages` when improving a prompt.
Examples:
`""`
usage
object
required
Usage information
Show child attributes
usage.cache_creation
object | null
required
Breakdown of cached tokens by TTL
Show child attributes
usage.cache_creation.ephemeral_1h_input_tokens
integer
default:0
required
The number of input tokens used to create the 1 hour cache entry.
Required range: `x >= 0`
usage.cache_creation.ephemeral_5m_input_tokens
integer
default:0
required
The number of input tokens used to create the 5 minute cache entry.
Required range: `x >= 0`
usage.cache_creation_input_tokens
integer | null
required
The number of input tokens used to create the cache entry.
Required range: `x >= 0`
Examples:
`2051`
usage.cache_read_input_tokens
integer | null
required
The number of input tokens read from the cache.
Required range: `x >= 0`
Examples:
`2051`
usage.input_tokens
integer
required
The number of input tokens which were used.
Required range: `x >= 0`
Examples:
`2095`
usage.output_tokens
integer
required
The number of output tokens which were used.
Required range: `x >= 0`
Examples:
`503`
usage.server_tool_use
object | null
required
The number of server tool requests.
Show child attributes
usage.server_tool_use.web_search_requests
integer
default:0
required
The number of web search tool requests.
Required range: `x >= 0`
Examples:
`0`
usage.service_tier
enum<string> | null
required
If the request used the priority, standard, or batch tier.
Available options:
`standard`,
`priority`,
`batch`
[Generate a prompt](/en/api/prompt-tools-generate)[Templatize a prompt](/en/api/prompt-tools-templatize)
curl -X POST https://api.anthropic.com/v1/experimental/improve_prompt \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "anthropic-beta: prompt-tools-2025-04-02" \
--header "content-type: application/json" \
--data \
'{
"messages": [{"role": "user", "content": [{"type": "text", "text": "Create a recipe for {{food}}"}]}],
"system": "You are a professional chef",
"feedback": "Make it more detailed and include cooking times",
"target_model": "claude-3-7-sonnet-20250219"
}'
{
"messages": [
{
"content": [
{
"text": "<improved prompt>",
"type": "text"
}
],
"role": "user"
},
{
"content": [
{
"text": "<assistant prefill>",
"type": "text"
}
],
"role": "assistant"
}
],
"system": "",
"usage": [
{
"input_tokens": 490,
"output_tokens": 661
}
]
}

## Templatize a prompt

*Source: https://docs.anthropic.com/en/api/prompt-tools-templatize*

Prompt tools
Templatize a prompt
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
POST
/
v1
/
experimental
/
templatize_prompt
curl -X POST https://api.anthropic.com/v1/experimental/templatize_prompt \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "anthropic-beta: prompt-tools-2025-04-02" \
--header "content-type: application/json" \
--data \
{
"messages": [
{
"content": [
{
"text": "Translate {{WORD_TO_TRANSLATE}} to {{TARGET_LANGUAGE}}",
"type": "text"
}
],
"role": "user"
}
],
"system": ,
"usage": [
{
"input_tokens": 490,
"output_tokens": 661
}
],
"variable_values": {
"TARGET_LANGUAGE": "German",
"WORD_TO_TRANSLATE": "hello"
}
}
The prompt tools APIs are in a closed research preview. .
Before you begin
These APIs are similar to what’s available in the [Anthropic Workbench](https://console.anthropic.com/workbench), and are intented for use by other prompt engineering platforms and playgrounds.
Getting started with the prompt improver
To use the prompt generation API, you’ll need to:
1. Have joined the closed research preview for the prompt tools APIs
2. Use the API directly, rather than the SDK
3. Add the beta header `prompt-tools-2025-04-02`
This API is not available in the SDK
Templatize a prompt
#### Headers
anthropic-beta
string[]
Optional header to specify the beta version(s) you want to use.
To use multiple betas, use a comma separated list like `beta1,beta2` or specify the header multiple times for each beta.
x-api-key
string
required
Your unique API key for authentication.
This key is required in the header of all API requests, to authenticate your account and access Anthropic's services. Get your API key through the [Console](https://console.anthropic.com/settings/keys). Each key is scoped to a Workspace.
#### Body
application/json
messages
object[]
required
The prompt to templatize, structured as a list of `message` objects.
Each message in the `messages` array must:
* Contain only text-only content blocks
* Not include tool calls, images, or prompt caching blocks
Example of a simple text prompt:
[
{
"role": "user",
"content": [
{
"type": "text",
"text": "Translate hello to German"
}
]
}
]
Note that only contiguous user messages with text content are allowed. Assistant prefill is permitted, but other content types will cause validation errors.
Show child attributes
messages.content
required
messages.role
enum<string>
required
Available options:
`user`,
`assistant`
Examples:
[
{
"content": [
{
"text": "Translate hello to German",
"type": "text"
}
],
"role": "user"
}
]
system
string | null
The existing system prompt to templatize.
Note that this differs from the Messages API; it is strictly a string.
Examples:
#### Response
200
2004XX
application/json
Successful Response
messages
object[]
required
The templatized prompt with variable placeholders.
The response includes the input messages with specific values replaced by variable placeholders. These messages maintain the original message structure but contain uppercase variable names in place of concrete values.
For example, an input message content like `"Translate hello to German"` would be transformed to `"Translate {{WORD_TO_TRANSLATE}} to {{TARGET_LANGUAGE}}"`.
{
"messages": [
{
"role": "user",
"content": [
{
"type": "text",
"text": "Translate {{WORD_TO_TRANSLATE}} to {{TARGET_LANGUAGE}}"
}
]
}
]
}
Show child attributes
messages.content
required
messages.role
enum<string>
required
Available options:
`user`,
`assistant`
Examples:
[
{
"content": [
{
"text": "Translate {{WORD_TO_TRANSLATE}} to {{TARGET_LANGUAGE}}",
"type": "text"
}
],
"role": "user"
}
]
system
string
required
The input system prompt with variables identified and replaced.
If no system prompt was provided in the original request, this field will be an empty string.
Examples:
usage
object
required
Usage information
Show child attributes
usage.cache_creation
object | null
required
Breakdown of cached tokens by TTL
Show child attributes
usage.cache_creation.ephemeral_1h_input_tokens
integer
default:0
required
The number of input tokens used to create the 1 hour cache entry.
Required range: `x >= 0`
usage.cache_creation.ephemeral_5m_input_tokens
integer
default:0
required
The number of input tokens used to create the 5 minute cache entry.
Required range: `x >= 0`
usage.cache_creation_input_tokens
integer | null
required
The number of input tokens used to create the cache entry.
Required range: `x >= 0`
Examples:
`2051`
usage.cache_read_input_tokens
integer | null
required
The number of input tokens read from the cache.
Required range: `x >= 0`
Examples:
`2051`
usage.input_tokens
integer
required
The number of input tokens which were used.
Required range: `x >= 0`
Examples:
`2095`
usage.output_tokens
integer
required
The number of output tokens which were used.
Required range: `x >= 0`
Examples:
`503`
usage.server_tool_use
object | null
required
The number of server tool requests.
Show child attributes
usage.server_tool_use.web_search_requests
integer
default:0
required
The number of web search tool requests.
Required range: `x >= 0`
Examples:
`0`
usage.service_tier
enum<string> | null
required
If the request used the priority, standard, or batch tier.
Available options:
`standard`,
`priority`,
`batch`
variable_values
object
required
A mapping of template variable names to their original values, as extracted from the input prompt during templatization. Each key represents a variable name identified in the templatized prompt, and each value contains the corresponding content from the original prompt that was replaced by that variable.
Example:
"variable_values": {
"WORD_TO_TRANSLATE": "hello",
"TARGET_LANGUAGE": "German"
}
In this example response, the original prompt – `Translate hello to German` – was templatized to `Translate WORD_TO_TRANSLATE to TARGET_LANGUAGE`, with the variable values extracted as shown.
Show child attributes
variable_values.{key}
string
Examples:
{
"TARGET_LANGUAGE": "German",
"WORD_TO_TRANSLATE": "hello"
}
[Improve a prompt](/en/api/prompt-tools-improve)[Migrating from Text Completions](/en/api/migrating-from-text-completions-to-messages)
curl -X POST https://api.anthropic.com/v1/experimental/templatize_prompt \
--header "x-api-key: $ANTHROPIC_API_KEY" \
--header "anthropic-version: 2023-06-01" \
--header "anthropic-beta: prompt-tools-2025-04-02" \
--header "content-type: application/json" \
--data \
{
"messages": [
{
"content": [
{
"text": "Translate {{WORD_TO_TRANSLATE}} to {{TARGET_LANGUAGE}}",
"type": "text"
}
],
"role": "user"
}
],
"system": ,
"usage": [
{
"input_tokens": 490,
"output_tokens": 661
}
],
"variable_values": {
"TARGET_LANGUAGE": "German",
"WORD_TO_TRANSLATE": "hello"
}
}

## Prompt validation

*Source: https://docs.anthropic.com/en/api/prompt-validation*

Text Completions (Legacy)
Prompt validation
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
**Legacy API**
The Text Completions API is a legacy API. Future models and features will require use of the [Messages API](/en/api/messages), and we recommend [migrating](/en/api/migrating-from-text-completions-to-messages) as soon as possible.
The Anthropic API performs basic prompt sanitization and validation to help ensure that your prompts are well-formatted for Claude.
When creating Text Completions, if your prompt is not in the specified format, the API will first attempt to lightly sanitize it (for example, by removing trailing spaces). This exact behavior is subject to change, and we strongly recommend that you format your prompts with the [recommended](/en/docs/build-with-claude/prompt-engineering/overview) alternating `\n\nHuman:` and `\n\nAssistant:` turns.
Then, the API will validate your prompt under the following conditions:
* The first conversational turn in the prompt must be a `\n\nHuman:` turn
* The last conversational turn in the prompt be an `\n\nAssistant:` turn
* The prompt must be less than `100,000 - 1` tokens in length.
The following prompts will results in [API errors](/en/api/errors):
# Missing "\n\nHuman:" and "\n\nAssistant:" turns
prompt = "Hello, world"
# Missing "\n\nHuman:" turn
prompt = "Hello, world\n\nAssistant:"
# Missing "\n\nAssistant:" turn
prompt = "\n\nHuman: Hello, Claude"
# "\n\nHuman:" turn is not first
prompt = "\n\nAssistant: Hello, world\n\nHuman: Hello, Claude\n\nAssistant:"
# "\n\nAssistant:" turn is not last
prompt = "\n\nHuman: Hello, Claude\n\nAssistant: Hello, world\n\nHuman: How many toes do dogs have?"
# "\n\nAssistant:" only has one "\n"
prompt = "\n\nHuman: Hello, Claude \nAssistant:"
The following are currently accepted and automatically sanitized by the API, but you should not rely on this behavior, as it may change in the future:
# No leading "\n\n" for "\n\nHuman:"
prompt = "Human: Hello, Claude\n\nAssistant:"
# Trailing space after "\n\nAssistant:"
prompt = "\n\nHuman: Hello, Claude:\n\nAssistant: "
[Streaming Text Completions](/en/api/streaming)[Client SDKs](/en/api/client-sdks)

## Versions

*Source: https://docs.anthropic.com/en/api/versioning*

##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
For any given API version, we will preserve:
* Existing input parameters
* Existing output parameters
However, we may do the following:
* Add additional optional inputs
* Add additional values to the output
* Change conditions for specific error types
* Add new variants to enum-like output values (for example, streaming event types)
Generally, if you are using the API as documented in this reference, we will not break your usage.
Version history
We always recommend using the latest API version whenever possible. Previous versions are considered deprecated and may be unavailable for new users.
* `2023-06-01`
* New format for [streaming](/en/api/streaming) server-sent events (SSE):
* Completions are incremental. For example, `" Hello"`, `" my"`, `" name"`, `" is"`, `" Claude." ` instead of `" Hello"`, `" Hello my"`, `" Hello my name"`, `" Hello my name is"`, `" Hello my name is Claude."`.
* All events are , rather than .
* Removed unnecessary `data: [DONE]` event.
* Removed legacy `exception` and `truncated` values in responses.
* `2023-01-01`: Initial release.
[Vertex AI API](/en/api/claude-on-vertex-ai)[IP addresses](/en/api/ip-addresses)

---

# Integration Guides

## Amazon Bedrock

*Source: https://docs.anthropic.com/en/api/claude-on-amazon-bedrock*

Amazon Bedrock API
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
Calling Claude through Bedrock slightly differs from how you would call Claude when using Anthropic’s client SDK’s. This guide will walk you through the process of completing an API call to Claude on Bedrock in either Python or TypeScript.
Note that this guide assumes you have already signed up for an and configured programmatic access.
Install and configure the AWS CLI
1. at or newer than version `2.13.23`
2. Configure your AWS credentials using the AWS configure command (see ) or find your credentials by navigating to “Command line or programmatic access” within your AWS dashboard and following the directions in the popup modal.
3. Verify that your credentials are working:
aws sts get-caller-identity
Install an SDK for accessing Bedrock
pip install -U "anthropic[bedrock]"
Accessing Bedrock
###
Subscribe to Anthropic models
Go to the and request access to Anthropic models. Note that Anthropic model availability varies by region. See for latest information.
####
API model names
Model| Bedrock API model name
---|---
Claude Opus 4| anthropic.claude-opus-4-20250514-v1:0
Claude Sonnet 4| anthropic.claude-sonnet-4-20250514-v1:0
Claude Sonnet 3.7| anthropic.claude-3-7-sonnet-20250219-v1:0
Claude Haiku 3.5| anthropic.claude-3-5-haiku-20241022-v1:0
Claude Sonnet 3.5| anthropic.claude-3-5-sonnet-20241022-v2:0
Claude Opus 3 ⚠️| anthropic.claude-3-opus-20240229-v1:0
Claude Sonnet 3 ⚠️| anthropic.claude-3-sonnet-20240229-v1:0
Claude Haiku 3| anthropic.claude-3-haiku-20240307-v1:0
###
List available models
The following examples show how to print a list of all the Claude models available through Bedrock:
aws bedrock list-foundation-models --region=us-west-2 --by-provider anthropic --query "modelSummaries[*].modelId"
###
Making requests
The following examples shows how to generate text from Claude on Bedrock:
from anthropic import AnthropicBedrock
client = AnthropicBedrock(
# Authenticate by either providing the keys below or use the default AWS credential providers, such as
# using ~/.aws/credentials or the "AWS_SECRET_ACCESS_KEY" and "AWS_ACCESS_KEY_ID" environment variables.
aws_access_key="<access key>",
aws_secret_key="<secret key>",
# Temporary credentials can be used with aws_session_token.
# Read more at https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html.
aws_session_token="<session_token>",
# aws_region changes the aws region to which the request is made. By default, we read AWS_REGION,
# and if that's not present, we default to us-east-1. Note that we do not read ~/.aws/config for the region.
aws_region="us-west-2",
)
message = client.messages.create(
model="anthropic.claude-opus-4-20250514-v1:0",
max_tokens=256,
messages=[{"role": "user", "content": "Hello, world"}]
)
print(message.content)
See our [client SDKs](/en/api/client-sdks) for more details, and the official Bedrock docs .
Activity logging
Bedrock provides an that allows customers to log the prompts and completions associated with your usage.
Anthropic recommends that you log your activity on at least a 30-day rolling basis in order to understand your activity and investigate any potential misuse.
Turning on this service does not give AWS or Anthropic any access to your content.
[Message Batches examples](/en/api/messages-batch-examples)[Vertex AI API](/en/api/claude-on-vertex-ai)

## Vertex AI

*Source: https://docs.anthropic.com/en/api/claude-on-vertex-ai*

Vertex AI API
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
* In Vertex, `model` is not passed in the request body. Instead, it is specified in the Google Cloud endpoint URL.
* In Vertex, `anthropic_version` is passed in the request body (rather than as a header), and must be set to the value `vertex-2023-10-16`.
Note that this guide assumes you have already have a GCP project that is able to use Vertex AI. See for more information on the setup required, as well as a full walkthrough.
Install an SDK for accessing Vertex AI
First, install Anthropic’s [client SDK](/en/api/client-sdks) for your language of choice.
pip install -U google-cloud-aiplatform "anthropic[vertex]"
Accessing Vertex AI
###
Model Availability
Note that Anthropic model availability varies by region. Search for “Claude” in the or go to for the latest information.
####
API model names
Model| Vertex AI API model name
---|---
Claude Opus 4| claude-opus-4@20250514
Claude Sonnet 4| claude-sonnet-4@20250514
Claude Sonnet 3.7| claude-3-7-sonnet@20250219
Claude Haiku 3.5| claude-3-5-haiku@20241022
Claude Sonnet 3.5| claude-3-5-sonnet-v2@20241022
Claude Opus 3 (Public Preview)| claude-3-opus@20240229
Claude Sonnet 3| claude-3-sonnet@20240229
Claude Haiku 3| claude-3-haiku@20240307
###
Making requests
Before running requests you may need to run `gcloud auth application-default login` to authenticate with GCP.
The following examples shows how to generate text from Claude on Vertex AI:
from anthropic import AnthropicVertex
project_id = "MY_PROJECT_ID"
# Where the model is running
region = "us-east5"
client = AnthropicVertex(project_id=project_id, region=region)
message = client.messages.create(
model="claude-opus-4@20250514",
max_tokens=100,
messages=[
{
"role": "user",
"content": "Hey Claude!",
}
],
)
print(message)
See our [client SDKs](/en/api/client-sdks) and the official for more details.
Activity logging
Vertex provides a that allows customers to log the prompts and completions associated with your usage.
Anthropic recommends that you log your activity on at least a 30-day rolling basis in order to understand your activity and investigate any potential misuse.
Turning on this service does not give Google or Anthropic any access to your content.
[Amazon Bedrock API](/en/api/claude-on-amazon-bedrock)[Versions](/en/api/versioning)

---

# Reference

## Errors

*Source: https://docs.anthropic.com/en/api/errors*

##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
HTTP errors
Our API follows a predictable HTTP error code format:
* 400 - `invalid_request_error`: There was an issue with the format or content of your request. We may also use this error type for other 4XX status codes not listed below.
* 401 - `authentication_error`: There’s an issue with your API key.
* 403 - `permission_error`: Your API key does not have permission to use the specified resource.
* 404 - `not_found_error`: The requested resource was not found.
* 413 - `request_too_large`: Request exceeds the maximum allowed number of bytes.
* 429 - `rate_limit_error`: Your account has hit a rate limit.
* 500 - `api_error`: An unexpected error has occurred internal to Anthropic’s systems.
* 529 - `overloaded_error`: Anthropic’s API is temporarily overloaded.
529 errors can occur when Anthropic APIs experience high traffic across all users. In rare cases, if your organization has a sharp increase in usage, you might see this type of error. To avoid 529 errors, ramp up your traffic gradually and maintain consistent usage patterns.
When receiving a [streaming](/en/api/streaming) response via SSE, it’s possible that an error can occur after returning a 200 response, in which case error handling wouldn’t follow these standard mechanisms.
Error shapes
Errors are always returned as JSON, with a top-level `error` object that always includes a `type` and `message` value. For example:
JSON
{
"type": "error",
"error": {
"type": "not_found_error",
"message": "The requested resource could not be found."
}
}
In accordance with our [versioning](/en/api/versioning) policy, we may expand the values within these objects, and it is possible that the `type` values will grow over time.
Request id
Our official SDKs provide this value as a property on top-level response objects, containing the value of the `request-id` header:
import anthropic
client = anthropic.Anthropic()
message = client.messages.create(
model="claude-opus-4-20250514",
max_tokens=1024,
messages=[
{"role": "user", "content": "Hello, Claude"}
]
)
print(f"Request ID: {message._request_id}")
Long requests
We highly encourage using the [streaming Messages API](/en/api/streaming) or [Message Batches API](/en/api/creating-message-batches) for long running requests, especially those over 10 minutes.
We do not recommend setting a large `max_tokens` values without using our [streaming Messages API](/en/api/streaming) or [Message Batches API](/en/api/creating-message-batches):
* Some networks may drop idle connections after a variable period of time, which can cause the request to fail or timeout without receiving a response from Anthropic.
* Networks differ in reliability; our [Message Batches API](/en/api/creating-message-batches) can help you manage the risk of network issues by allowing you to poll for results rather than requiring an uninterrupted network connection.
If you are building a direct API integration, you should be aware that setting a can reduce the impact of idle connection timeouts on some networks.
Our [SDKs](/en/api/client-sdks) will validate that your non-streaming Messages API requests are not expected to exceed a 10 minute timeout and also will set a socket option for TCP keep-alive.
[Service tiers](/en/api/service-tiers)[Handling stop reasons](/en/api/handling-stop-reasons)

## Handling stop reasons

*Source: https://docs.anthropic.com/en/api/handling-stop-reasons*

Handling stop reasons
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
When you make a request to the Messages API, Claude’s response includes a `stop_reason` field that indicates why the model stopped generating its response. Understanding these values is crucial for building robust applications that handle different response types appropriately.
For details about `stop_reason` in the API response, see the [Messages API reference](/en/api/messages).
What is stop_reason?
The `stop_reason` field is part of every successful Messages API response. Unlike errors, which indicate failures in processing your request, `stop_reason` tells you why Claude successfully completed its response generation.
Example response
{
"id": "msg_01234",
"type": "message",
"role": "assistant",
"content": [
{
"type": "text",
"text": "Here's the answer to your question..."
}
],
"stop_reason": "end_turn",
"stop_sequence": null,
"usage": {
"input_tokens": 100,
"output_tokens": 50
}
}
Stop reason values
###
end_turn
The most common stop reason. Indicates Claude finished its response naturally.
if response.stop_reason == "end_turn":
# Process the complete response
print(response.content[0].text)
###
max_tokens
Claude stopped because it reached the `max_tokens` limit specified in your request.
# Request with limited tokens
response = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=10,
messages=[{"role": "user", "content": "Explain quantum physics"}]
)
if response.stop_reason == "max_tokens":
# Response was truncated
print("Response was cut off at token limit")
# Consider making another request to continue
###
stop_sequence
Claude encountered one of your custom stop sequences.
response = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
stop_sequences=["END", "STOP"],
messages=[{"role": "user", "content": "Generate text until you say END"}]
)
if response.stop_reason == "stop_sequence":
print(f"Stopped at sequence: {response.stop_sequence}")
###
tool_use
Claude is calling a tool and expects you to execute it.
response = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
tools=[weather_tool],
messages=[{"role": "user", "content": "What's the weather?"}]
)
if response.stop_reason == "tool_use":
# Extract and execute the tool
for content in response.content:
if content.type == "tool_use":
result = execute_tool(content.name, content.input)
# Return result to Claude for final response
###
pause_turn
Used with server tools like web search when Claude needs to pause a long-running operation.
response = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
tools=[{"type": "web_search_20250305", "name": "web_search"}],
messages=[{"role": "user", "content": "Search for latest AI news"}]
)
if response.stop_reason == "pause_turn":
# Continue the conversation
messages = [
{"role": "user", "content": original_query},
{"role": "assistant", "content": response.content}
]
continuation = client.messages.create(
model="claude-sonnet-4-20250514",
messages=messages,
tools=[{"type": "web_search_20250305", "name": "web_search"}]
)
###
refusal
Claude refused to generate a response due to safety concerns.
response = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
messages=[{"role": "user", "content": "[Unsafe request]"}]
)
if response.stop_reason == "refusal":
# Claude declined to respond
print("Claude was unable to process this request")
# Consider rephrasing or modifying the request
Best practices for handling stop reasons
###
1\. Always check stop_reason
Make it a habit to check the `stop_reason` in your response handling logic:
def handle_response(response):
if response.stop_reason == "tool_use":
return handle_tool_use(response)
elif response.stop_reason == "max_tokens":
return handle_truncation(response)
elif response.stop_reason == "pause_turn":
return handle_pause(response)
elif response.stop_reason == "refusal":
return handle_refusal(response)
else:
# Handle end_turn and other cases
return response.content[0].text
###
2\. Handle max_tokens gracefully
When a response is truncated due to token limits:
def handle_truncated_response(response):
if response.stop_reason == "max_tokens":
# Option 1: Warn the user
return f"{response.content[0].text}\n\n[Response truncated due to length]"
# Option 2: Continue generation
messages = [
{"role": "user", "content": original_prompt},
{"role": "assistant", "content": response.content[0].text}
]
continuation = client.messages.create(
model="claude-sonnet-4-20250514",
max_tokens=1024,
messages=messages + [{"role": "user", "content": "Please continue"}]
)
return response.content[0].text + continuation.content[0].text
###
3\. Implement retry logic for pause_turn
For server tools that may pause:
def handle_paused_conversation(initial_response, max_retries=3):
response = initial_response
messages = [{"role": "user", "content": original_query}]
for attempt in range(max_retries):
if response.stop_reason != "pause_turn":
break
messages.append({"role": "assistant", "content": response.content})
response = client.messages.create(
model="claude-sonnet-4-20250514",
messages=messages,
tools=original_tools
)
return response
Stop reasons vs. errors
It’s important to distinguish between `stop_reason` values and actual errors:
###
Stop reasons (successful responses)
* Part of the response body
* Indicate why generation stopped normally
* Response contains valid content
###
Errors (failed requests)
* HTTP status codes 4xx or 5xx
* Indicate request processing failures
* Response contains error details
try:
response = client.messages.create(...)
# Handle successful response with stop_reason
if response.stop_reason == "max_tokens":
print("Response was truncated")
except anthropic.APIError as e:
# Handle actual errors
if e.status_code == 429:
print("Rate limit exceeded")
elif e.status_code == 500:
print("Server error")
Streaming considerations
When using streaming, `stop_reason` is:
* `null` in the initial `message_start` event
* Provided in the `message_delta` event
* Non-null in all other events
with client.messages.stream(...) as stream:
for event in stream:
if event.type == "message_delta":
stop_reason = event.delta.stop_reason
if stop_reason:
print(f"Stream ended with: {stop_reason}")
Common patterns
###
Handling tool use workflows
def complete_tool_workflow(client, user_query, tools):
messages = [{"role": "user", "content": user_query}]
while True:
response = client.messages.create(
model="claude-sonnet-4-20250514",
messages=messages,
tools=tools
)
if response.stop_reason == "tool_use":
# Execute tools and continue
tool_results = execute_tools(response.content)
messages.append({"role": "assistant", "content": response.content})
messages.append({"role": "user", "content": tool_results})
else:
# Final response
return response
###
Ensuring complete responses
def get_complete_response(client, prompt, max_attempts=3):
messages = [{"role": "user", "content": prompt}]
full_response = ""
for _ in range(max_attempts):
response = client.messages.create(
model="claude-sonnet-4-20250514",
messages=messages,
max_tokens=4096
)
full_response += response.content[0].text
if response.stop_reason != "max_tokens":
break
# Continue from where it left off
messages = [
{"role": "user", "content": prompt},
{"role": "assistant", "content": full_response},
{"role": "user", "content": "Please continue from where you left off."}
]
return full_response
By properly handling `stop_reason` values, you can build more robust applications that gracefully handle different response scenarios and provide better user experiences.
[Errors](/en/api/errors)[Beta headers](/en/api/beta-headers)

## IP addresses

*Source: https://docs.anthropic.com/en/api/ip-addresses*

IP addresses
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
####
IPv4
`160.79.104.0/23`
####
IPv6
`2607:6bc0::/48`
[Versions](/en/api/versioning)[](/en/api/supported-regions)

## Rate limits

*Source: https://docs.anthropic.com/en/api/rate-limits*

Rate limits
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
We have two types of limits:
1. **Spend limits** set a maximum monthly cost an organization can incur for API usage.
2. **Rate limits** set the maximum number of API requests an organization can make over a defined period of time.
We enforce service-configured limits at the organization level, but you may also set user-configurable limits for your organization’s workspaces.
These limits apply to both Standard and Priority Tier usage. For more information about Priority Tier, which offers enhanced service levels in exchange for committed spend, see [Service Tiers](/en/api/service-tiers).
About our limits
* Limits are designed to prevent API abuse, while minimizing impact on common customer usage patterns.
* Limits are defined by usage tier, where each tier is associated with a different set of spend and rate limits.
* Your organization will increase tiers automatically as you reach certain thresholds while using the API. Limits are set at the organization level. You can see your organization’s limits in the [Limits page](https://console.anthropic.com/settings/limits) in the [Anthropic Console](https://console.anthropic.com/).
* You may hit rate limits over shorter time intervals. For instance, a rate of 60 requests per minute (RPM) may be enforced as 1 request per second. Short bursts of requests at a high volume can surpass the rate limit and result in rate limit errors.
* The limits outlined below are our standard tier limits. If you’re seeking higher, custom limits or Priority Tier for enhanced service levels, contact sales through the [Anthropic Console](https://console.anthropic.com/settings/limits).
* We use the to do rate limiting. This means that your capacity is continuously replenished up to your maximum limit, rather than being reset at fixed intervals.
Spend limits
Each usage tier has a limit on how much you can spend on the API each calendar month. Once you reach the spend limit of your tier, until you qualify for the next tier, you will have to wait until the next month to be able to use the API again.
To qualify for the next tier, you must meet a deposit requirement. To minimize the risk of overfunding your account, you cannot deposit more than your monthly spend limit.
###
Requirements to advance tier
Usage Tier| Credit Purchase| Max Usage per Month
---|---|---
Tier 1| $5| $100
Tier 2| $40| $500
Tier 3| $200| $1,000
Tier 4| $400| $5,000
Monthly Invoicing| N/A| N/A
Rate limits
Our rate limits for the Messages API are measured in requests per minute (RPM), input tokens per minute (ITPM), and output tokens per minute (OTPM) for each model class. If you exceed any of the rate limits you will get a [429 error](/en/api/errors) describing which rate limit was exceeded, along with a `retry-after` header indicating how long to wait.
ITPM rate limits are estimated at the beginning of each request, and the estimate is adjusted during the request to reflect the actual number of input tokens used. The final adjustment counts `input_tokens` and `cache_creation_input_tokens` towards ITPM rate limits, while `cache_read_input_tokens` are not (though they are still billed). In some instances, `cache_read_input_tokens` are counted towards ITPM rate limits.
OTPM rate limits are estimated based on `max_tokens` at the beginning of each request, and the estimate is adjusted at the end of the request to reflect the actual number of output tokens used. If you’re hitting OTPM limits earlier than expected, try reducing `max_tokens` to better approximate the size of your completions.
Rate limits are applied separately for each model; therefore you can use different models up to their respective limits simultaneously. You can check your current rate limits and behavior in the [Anthropic Console](https://console.anthropic.com/settings/limits).
* Tier 1
* Tier 2
* Tier 3
* Tier 4
* Custom
Model| Maximum requests per minute (RPM)| Maximum input tokens per minute (ITPM)| Maximum output tokens per minute (OTPM)
---|---|---|---
Claude Opus 4| 50| 20,000| 8,000
Claude Sonnet 4| 50| 20,000| 8,000
Claude Sonnet 3.7| 50| 20,000| 8,000
Claude Sonnet 3.5
2024-10-22| 50| 40,000*| 8,000
Claude Sonnet 3.5
2024-06-20| 50| 40,000*| 8,000
Claude Haiku 3.5| 50| 50,000*| 10,000
Claude Opus 3| 50| 20,000*| 4,000
Claude Sonnet 3| 50| 40,000*| 8,000
Claude Haiku 3| 50| 50,000*| 10,000
Limits marked with asterisks (*) count `cache_read_input_tokens` towards ITPM usage.
Model| Maximum requests per minute (RPM)| Maximum input tokens per minute (ITPM)| Maximum output tokens per minute (OTPM)
---|---|---|---
Claude Opus 4| 50| 20,000| 8,000
Claude Sonnet 4| 50| 20,000| 8,000
Claude Sonnet 3.7| 50| 20,000| 8,000
Claude Sonnet 3.5
2024-10-22| 50| 40,000*| 8,000
Claude Sonnet 3.5
2024-06-20| 50| 40,000*| 8,000
Claude Haiku 3.5| 50| 50,000*| 10,000
Claude Opus 3| 50| 20,000*| 4,000
Claude Sonnet 3| 50| 40,000*| 8,000
Claude Haiku 3| 50| 50,000*| 10,000
Limits marked with asterisks (*) count `cache_read_input_tokens` towards ITPM usage.
Model| Maximum requests per minute (RPM)| Maximum input tokens per minute (ITPM)| Maximum output tokens per minute (OTPM)
---|---|---|---
Claude Opus 4| 1,000| 40,000| 16,000
Claude Sonnet 4| 1,000| 40,000| 16,000
Claude Sonnet 3.7| 1,000| 40,000| 16,000
Claude Sonnet 3.5
2024-10-22| 1,000| 80,000*| 16,000
Claude Sonnet 3.5
2024-06-20| 1,000| 80,000*| 16,000
Claude Haiku 3.5| 1,000| 100,000*| 20,000
Claude Opus 3| 1,000| 40,000*| 8,000
Claude Sonnet 3| 1,000| 80,000*| 16,000
Claude Haiku 3| 1,000| 100,000*| 20,000
Limits marked with asterisks (*) count `cache_read_input_tokens` towards ITPM usage.
Model| Maximum requests per minute (RPM)| Maximum input tokens per minute (ITPM)| Maximum output tokens per minute (OTPM)
---|---|---|---
Claude Opus 4| 2,000| 80,000| 32,000
Claude Sonnet 4| 2,000| 80,000| 32,000
Claude Sonnet 3.7| 2,000| 80,000| 32,000
Claude Sonnet 3.5
2024-10-22| 2,000| 160,000*| 32,000
Claude Sonnet 3.5
2024-06-20| 2,000| 160,000*| 32,000
Claude Haiku 3.5| 2,000| 200,000*| 40,000
Claude Opus 3| 2,000| 80,000*| 16,000
Claude Sonnet 3| 2,000| 160,000*| 32,000
Claude Haiku 3| 2,000| 200,000*| 40,000
Limits marked with asterisks (*) count `cache_read_input_tokens` towards ITPM usage.
Model| Maximum requests per minute (RPM)| Maximum input tokens per minute (ITPM)| Maximum output tokens per minute (OTPM)
---|---|---|---
Claude Opus 4| 4,000| 200,000| 80,000
Claude Sonnet 4| 4,000| 200,000| 80,000
Claude Sonnet 3.7| 4,000| 200,000| 80,000
Claude Sonnet 3.5
2024-10-22| 4,000| 400,000*| 80,000
Claude Sonnet 3.5
2024-06-20| 4,000| 400,000*| 80,000
Claude Haiku 3.5| 4,000| 400,000*| 80,000
Claude Opus 3| 4,000| 400,000*| 80,000
Claude Sonnet 3| 4,000| 400,000*| 80,000
Claude Haiku 3| 4,000| 400,000*| 80,000
Limits marked with asterisks (*) count `cache_read_input_tokens` towards ITPM usage.
If you’re seeking higher limits for an Enterprise use case, contact sales through the [Anthropic Console](https://console.anthropic.com/settings/limits).
###
Message Batches API
The Message Batches API has its own set of rate limits which are shared across all models. These include a requests per minute (RPM) limit to all API endpoints and a limit on the number of batch requests that can be in the processing queue at the same time. A “batch request” here refers to part of a Message Batch. You may create a Message Batch containing thousands of batch requests, each of which count towards this limit. A batch request is considered part of the processing queue when it has yet to be successfully processed by the model.
* Tier 1
* Tier 2
* Tier 3
* Tier 4
* Custom
Maximum requests per minute (RPM)| Maximum batch requests in processing queue| Maximum batch requests per batch
---|---|---
50| 100,000| 100,000
Maximum requests per minute (RPM)| Maximum batch requests in processing queue| Maximum batch requests per batch
---|---|---
50| 100,000| 100,000
Maximum requests per minute (RPM)| Maximum batch requests in processing queue| Maximum batch requests per batch
---|---|---
1,000| 200,000| 100,000
Maximum requests per minute (RPM)| Maximum batch requests in processing queue| Maximum batch requests per batch
---|---|---
2,000| 300,000| 100,000
Maximum requests per minute (RPM)| Maximum batch requests in processing queue| Maximum batch requests per batch
---|---|---
4,000| 500,000| 100,000
If you’re seeking higher limits for an Enterprise use case, contact sales through the [Anthropic Console](https://console.anthropic.com/settings/limits).
Setting lower limits for Workspaces
In order to protect Workspaces in your Organization from potential overuse, you can set custom spend and rate limits per Workspace.
Note:
* You can’t set limits on the default Workspace.
* If not set, Workspace limits match the Organization’s limit.
* Organization-wide limits always apply, even if Workspace limits add up to more.
Response headers
The API response includes headers that show you the rate limit enforced, current usage, and when the limit will be reset.
The following headers are returned:
Header| Description
---|---
`retry-after`| The number of seconds to wait until you can retry the request. Earlier retries will fail.
`anthropic-ratelimit-requests-limit`| The maximum number of requests allowed within any rate limit period.
`anthropic-ratelimit-requests-remaining`| The number of requests remaining before being rate limited.
`anthropic-ratelimit-requests-reset`| The time when the request rate limit will be fully replenished, provided in RFC 3339 format.
`anthropic-ratelimit-tokens-limit`| The maximum number of tokens allowed within any rate limit period.
`anthropic-ratelimit-tokens-remaining`| The number of tokens remaining (rounded to the nearest thousand) before being rate limited.
`anthropic-ratelimit-tokens-reset`| The time when the token rate limit will be fully replenished, provided in RFC 3339 format.
`anthropic-ratelimit-input-tokens-limit`| The maximum number of input tokens allowed within any rate limit period.
`anthropic-ratelimit-input-tokens-remaining`| The number of input tokens remaining (rounded to the nearest thousand) before being rate limited.
`anthropic-ratelimit-input-tokens-reset`| The time when the input token rate limit will be fully replenished, provided in RFC 3339 format.
`anthropic-ratelimit-output-tokens-limit`| The maximum number of output tokens allowed within any rate limit period.
`anthropic-ratelimit-output-tokens-remaining`| The number of output tokens remaining (rounded to the nearest thousand) before being rate limited.
`anthropic-ratelimit-output-tokens-reset`| The time when the output token rate limit will be fully replenished, provided in RFC 3339 format.
`anthropic-priority-input-tokens-limit`| The maximum number of Priority Tier input tokens allowed within any rate limit period. (Priority Tier only)
`anthropic-priority-input-tokens-remaining`| The number of Priority Tier input tokens remaining (rounded to the nearest thousand) before being rate limited. (Priority Tier only)
`anthropic-priority-input-tokens-reset`| The time when the Priority Tier input token rate limit will be fully replenished, provided in RFC 3339 format. (Priority Tier only)
`anthropic-priority-output-tokens-limit`| The maximum number of Priority Tier output tokens allowed within any rate limit period. (Priority Tier only)
`anthropic-priority-output-tokens-remaining`| The number of Priority Tier output tokens remaining (rounded to the nearest thousand) before being rate limited. (Priority Tier only)
`anthropic-priority-output-tokens-reset`| The time when the Priority Tier output token rate limit will be fully replenished, provided in RFC 3339 format. (Priority Tier only)
The `anthropic-ratelimit-tokens-*` headers display the values for the most restrictive limit currently in effect. For instance, if you have exceeded the Workspace per-minute token limit, the headers will contain the Workspace per-minute token rate limit values. If Workspace limits do not apply, the headers will return the total tokens remaining, where total is the sum of input and output tokens. This approach ensures that you have visibility into the most relevant constraint on your current API usage.
[Overview](/en/api/overview)[Service tiers](/en/api/service-tiers)

## Service tiers

*Source: https://docs.anthropic.com/en/api/service-tiers*

Service tiers
##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
We offer three service tiers:
* **Priority Tier:** Best for workflows deployed in production where time, availability, and predictable pricing are important
* **Standard:** Default tier for both piloting and scaling everyday use cases
* **Batch:** Best for asynchronous workflows which can wait or benefit from being outside your normal capacity
Standard Tier
The standard tier is the default service tier for all API requests. Requests in this tier are prioritized alongside all other requests and observe best-effort availability.
Priority Tier
Requests in this tier are prioritized over all other requests to Anthropic. This prioritization helps minimize [“server overloaded” errors](/en/api/errors#http-errors), even during peak times.
For more information, see [Get started with Priority Tier](/_sites/docs.anthropic.com/en/api/service-tiers#get-started-with-priority-tier)
How requests get assigned tiers
When handling a request, Anthropic decides to assign a request to Priority Tier in the following scenarios:
* Your organization has sufficient priority tier capacity **input** tokens per minute
* Your organization has sufficient priority tier capacity **output** tokens per minute
Anthropic counts usage against Priority Tier capacity as follows:
**Input Tokens**
* Cache reads as 0.1 tokens per token read from the cache
* Cache writes as 1.25 tokens per token written to the cache with a 5 minute TTL
* Cache writes as 2.00 tokens per token written to the cache with a 1 hour TTL
* All other input tokens are 1 token per token
**Output Tokens**
* 1 token per token
Otherwise, requests proceed at standard tier.
Requests assigned Priority Tier pull from both the Priority Tier capacity and the regular rate limits. If servicing the request would exceed the rate limits, the request is declined.
Using service tiers
You can control which service tiers can be used for a request by setting the `service_tier` parameter:
message = client.messages.create(
model="claude-opus-4-20250514",
max_tokens=1024,
messages=[{"role": "user", "content": "Hello, Claude!"}],
service_tier="auto" # Automatically use Priority Tier when available, fallback to standard
)
The `service_tier` parameter accepts the following values:
* `"auto"` (default) - Uses the Priority Tier capacity if available, falling back to your other capacity if not
* `"standard_only"` \- Only use standard tier capacity, useful if you don’t want to use your Priority Tier capacity
The response `usage` object also includes the service tier assigned to the request:
{
"usage": {
"input_tokens": 410,
"cache_creation_input_tokens": 0,
"cache_read_input_tokens": 0,
"output_tokens": 585,
"service_tier": "priority"
}
}
This allows you to determine which service tier was assigned to the request.
When requesting `service_tier="auto"` with a model with a Priority Tier commitment, these response headers provide insights:
anthropic-priority-input-tokens-limit: 10000
anthropic-priority-input-tokens-remaining: 9618
anthropic-priority-input-tokens-reset: 2025-01-12T23:11:59Z
anthropic-priority-output-tokens-limit: 10000
anthropic-priority-output-tokens-remaining: 6000
anthropic-priority-output-tokens-reset: 2025-01-12T23:12:21Z
You can use the presence of these headers to detect if your request was eligible for Priority Tier, even if it was over the limit.
Get started with Priority Tier
You may want to commit to Priority Tier capacity if you are interested in:
* **Cost Control** : Predictable spend and discounts for longer commitments
* **Flexible overflow** : Automatically falls back to standard tier when you exceed your committed capacity
Committing to Priority Tier will involve deciding:
* A number of input tokens per minute
* A number of output tokens per minute
* A commitment duration (1, 3, 6, or 12 months)
* A specific model version
The ratio of input to output tokens you purchase matters. Sizing your Priority Tier capacity to align with your actual traffic patterns helps you maximize utilization of your purchased tokens.
###
* Claude Opus 4
* Claude Sonnet 4
* Claude Sonnet 3.7
* Claude Sonnet 3.5 (both versions)
* Claude Haiku 3.5
Check the [model overview page](/en/docs/about-claude/models/overview) for more details on our models.
###
How to access Priority Tier
To begin using Priority Tier:
1. [Contact sales](https://www.anthropic.com/contact-sales/priority-tier) to complete provisioning
2. (Optional) Update your API requests to optionally set the `service_tier` parameter to `auto`
3. Monitor your usage through response headers and the Anthropic Console
[Rate limits](/en/api/rate-limits)[Errors](/en/api/errors)

## Supported Regions

*Source: https://docs.anthropic.com/en/api/supported-regions*

##### API reference
##### SDKs
* *
##### Examples
* *
##### 3rd-party APIs
* *
* Albania
* Algeria
* Andorra
* Angola
* Antigua and Barbuda
* Argentina
* Armenia
* Australia
* Austria
* Azerbaijan
* Bahamas
* Bahrain
* Bangladesh
* Barbados
* Belgium
* Belize
* Benin
* Bhutan
* Bolivia
* Bosnia and Herzegovina
* Botswana
* Brazil
* Brunei
* Bulgaria
* Burkina Faso
* Burundi
* Cabo Verde
* Cambodia
* Cameroon
* Canada
* Chad
* Chile
* Colombia
* Comoros
* Congo, Republic of the
* Costa Rica
* Côte d’Ivoire
* Croatia
* Cyprus
* Czechia (Czech Republic)
* Denmark
* Djibouti
* Dominica
* Dominican Republic
* Ecuador
* Egypt
* El Salvador
* Equatorial Guinea
* Estonia
* Eswatini
* Fiji
* Finland
* France
* Gabon
* Gambia
* Georgia
* Germany
* Ghana
* Greece
* Grenada
* Guatemala
* Guinea
* Guinea-Bissau
* Guyana
* Haiti
* Holy See (Vatican City)
* Honduras
* Hungary
* Iceland
* India
* Indonesia
* Iraq
* Ireland
* Israel
* Italy
* Jamaica
* Japan
* Jordan
* Kazakhstan
* Kenya
* Kiribati
* Kuwait
* Kyrgyzstan
* Laos
* Latvia
* Lebanon
* Lesotho
* Liberia
* Liechtenstein
* Lithuania
* Luxembourg
* Madagascar
* Malawi
* Malaysia
* Maldives
* Malta
* Marshall Islands
* Mauritania
* Mauritius
* Mexico
* Micronesia
* Moldova
* Monaco
* Mongolia
* Montenegro
* Morocco
* Mozambique
* Namibia
* Nauru
* Nepal
* Netherlands
* New Zealand
* Niger
* Nigeria
* North Macedonia
* Norway
* Oman
* Pakistan
* Palau
* Palestine
* Panama
* Papua New Guinea
* Paraguay
* Peru
* Philippines
* Poland
* Portugal
* Qatar
* Romania
* Rwanda
* Saint Kitts and Nevis
* Saint Lucia
* Saint Vincent and the Grenadines
* Samoa
* San Marino
* Sao Tome and Principe
* Saudi Arabia
* Senegal
* Serbia
* Seychelles
* Sierra Leone
* Singapore
* Slovakia
* Slovenia
* Solomon Islands
* South Africa
* South Korea
* Spain
* Sri Lanka
* Suriname
* Sweden
* Switzerland
* Taiwan
* Tajikistan
* Tanzania
* Thailand
* Timor-Leste, Democratic Republic of
* Togo
* Tonga
* Trinidad and Tobago
* Tunisia
* Turkey
* Turkmenistan
* Tuvalu
* Uganda
* Ukraine (except Crimea, Donetsk, and Luhansk regions)
* United Arab Emirates
* United Kingdom
* United States of America
* Uruguay
* Uzbekistan
* Vanuatu
* Vietnam
* Zambia
* Zimbabwe
[IP addresses](/en/api/ip-addresses)[Using the Admin API](/en/api/administration-api)

---

