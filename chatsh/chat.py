import os
import aiofiles
from anthropic import AsyncAnthropic
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

def get_vendor_from_model(model):
    model = MODELS.get(model, model).lower()
    if model.startswith('gpt') or model.startswith('chatgpt'):
        return 'openai'
    elif model.startswith('claude'):
        return 'anthropic'
    elif model.startswith('llama'):
        return 'openai'  # Using OpenAI for Llama models
    elif model.startswith('gemini'):
        return 'google'
    else:
        raise ValueError(f"Unsupported model: {model}")

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
        params = {"system": prompt_system, "model": model, "temperature": temperature, "max_tokens": max_tokens}

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

            self.messages.extend([
                {"role": "user", "content": user_message},
                {"role": 'assistant', "content": assistant_message}
            ])
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            print("The last message was not added to the conversation history.")
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
        import google.generativeai as genai
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

            self.messages.extend([
                {"role": "user", "parts": [{"text": user_message}]},
                {"role": 'model', "parts": [{"text": result}]}
            ])
        except Exception as e:
            print(f"\nError occurred: {str(e)}")
            print("The last message was not added to the conversation history.")
            raise

        return result

def chat(model) -> Chat:
    vendor = get_vendor_from_model(model)
    if vendor == 'openai':
        return OpenAIChat()
    elif vendor == 'anthropic':
        return AnthropicChat()
    elif vendor == 'google':
        return GeminiChat()
    else:
        raise ValueError(f"Unsupported vendor: {vendor}")

async def get_token(vendor):
    token_path = os.path.join(os.path.expanduser('~'), '.config', f'{vendor}.token')
    try:
        async with aiofiles.open(token_path, 'r') as f:
            return (await f.read()).strip()
    except Exception as err:
        print(f"Error reading token from {token_path}: {err}")
        if vendor == 'anthropic':
            print("As a courtesy, xida@renresear.ch has provided a temporary token for you to use. Please use it for no more than 3 chats or he will be very sad and disappointed at you.")
            # hopefully base64 protects us against some scrapers
            # token is limited to $ 15 / month and is heavily rate limited
            b64 = 'c2stYW50LWFwaTAzLXJEUWlBZV9VZG9RUm9ZdGFJTWRNbDEtQk5IWXltMmVJTTVyUnhndnVobE5pdkZBMlE3eXc0MExDanVBUkVLSUtRdXUwM0JIaWVqaEJPYUVkSC1mVy1BLVUzVzI5Z0FB'
            # decode token
            import base64
            token = base64.b64decode(b64).decode('utf-8')
            return token

        raise
