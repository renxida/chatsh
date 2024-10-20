
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