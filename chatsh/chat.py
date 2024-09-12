import os
import aiofiles
from anthropic import AsyncAnthropic
import tiktoken
from abc import ABC, abstractmethod

# Map of model shortcodes to full model names
MODELS = {
    'g': 'gpt-4o-2024-08-06',
    'G': 'gpt-4-32k-0314',
    'h': 'claude-3-haiku-20240307',
    's': 'claude-3-5-sonnet-20240620',
    'o': 'claude-3-opus-20240229',
    'l': 'llama-3.1-8b-instant',
    'L': 'llama-3.1-70b-versatile',
    'i': 'gemini-1.5-flash-latest',
    'I': 'gemini-1.5-pro-exp-0801'
}
class Chat(ABC):
    def __init__(self):
        self.messages = []

    @abstractmethod
    async def ask(self, user_message, system, model, temperature=0.0, max_tokens=4096, stream=True, system_cacheable=False):
        pass

    def back(self, steps):
        removed_messages = self.messages[-2*steps:]
        del self.messages[-2*steps:]
        return removed_messages

class AnthropicChat(Chat):
    async def ask(self, user_message, system, model, temperature=0.0, max_tokens=4096, stream=True, system_cacheable=False):
        model = MODELS.get(model, model)
        client = AsyncAnthropic(
            api_key=await get_token('anthropic'),
            default_headers={
                "anthropic-beta": "prompt-caching-2024-07-31"  # Enable prompt caching
            }
        )

        cached_system = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]

        prompt_system = cached_system if system_cacheable else system
        params = {"system": prompt_system, "model": model, "temperature": temperature, "max_tokens": max_tokens,}

        try:
            assistant_message = ""
            if stream:
                async with client.messages.stream(**params, messages=self.messages + [{"role": "user", "content": user_message}]) as stream:
                    async for text in stream.text_stream:
                        assistant_message += text
                        yield text
            else:
                response = await client.messages.create(**params, messages=self.messages + [{"role": "user", "content": user_message}])
                assistant_message = response.content
                yield response.content

            self.messages.append({"role": "user", "content": user_message})
            self.messages.append({"role": 'assistant', "content": assistant_message})
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            print("The last message was not added to the conversation history.")
            raise

async def get_token(vendor):
    token_path = os.path.join(os.path.expanduser('~'), '.config', f'{vendor}.token')
    try:
        async with aiofiles.open(token_path, 'r') as f:
            return (await f.read()).strip()
    except Exception as err:
        print(f"Error reading {vendor}.token file: {err}")
        raise



class OpenAIChat(Chat):
    async def ask(self, user_message, system, model, temperature=0.0, max_tokens=4096, stream=True, system_cacheable=False):
        from openai import AsyncOpenAI
        model = MODELS.get(model, model)
        client = AsyncOpenAI(api_key=await get_token('openai'))

        if not self.messages:
            self.messages.append({"role": "system", "content": system})

        self.messages.append({"role": "user", "content": user_message})

        params = {"messages": self.messages, "model": model, "temperature": temperature, "max_tokens": max_tokens, "stream": stream}

        result = ""
        try:
            async for chunk in await client.chat.completions.create(**params):
                text = chunk.choices[0].delta.content or ""
                print(text, end='', flush=True)
                result += text

            self.messages.append({"role": 'assistant', "content": result})
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            print("The last message was not added to the conversation history.")
            self.messages.pop()  # Remove the last user message
            raise

        return result

class GeminiChat(Chat):
    async def ask(self, user_message, system, model, temperature=0.0, max_tokens=4096, stream=True, system_cacheable=False):
        model = MODELS.get(model, model)
        genai.configure(api_key=await get_token('google'))

        model = genai.GenerativeModel(model)
        chat = model.start_chat(history=self.messages)

        generation_config = genai.types.GenerationConfig(
            max_output_tokens=max_tokens,
            temperature=temperature
        )

        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        result = ""
        try:
            response = chat.send_message(user_message, generation_config=generation_config, safety_settings=safety_settings, stream=stream)

            if stream:
                for chunk in response:
                    text = chunk.text
                    print(text, end='', flush=True)
                    result += text
            else:
                result = response.text

            self.messages.append({"role": "user", "parts": [{"text": user_message}]})
            self.messages.append({"role": 'model', "parts": [{"text": result}]})
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            print("The last message was not added to the conversation history.")
            raise

        return result

def chat(model) -> Chat:
    model = MODELS.get(model, model)
    if model.startswith('gpt') or model.startswith('chatgpt'):
        return OpenAIChat()
    elif model.startswith('claude'):
        return AnthropicChat()
    elif model.startswith('llama'):
        return OpenAIChat()  # Using OpenAI for Llama models
    elif model.startswith('gemini'):
        return GeminiChat()
    else:
        raise ValueError(f"Unsupported model: {model}")

async def get_token(vendor):
    token_path = os.path.join(os.path.expanduser('~'), '.config', f'{vendor}.token')
    try:
        async with aiofiles.open(token_path, 'r') as f:
            return (await f.read()).strip()
    except Exception as err:
        print(f"Error reading {vendor}.token file: {err}")
        raise

def token_count(input_text):
    # Use GPT-4 tokenizer
    encoding = tiktoken.encoding_for_model("gpt-4")
    return len(encoding.encode(input_text))
