import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class LLMService:
    def __init__(self):
        self.api_key = os.getenv("DEEPSEEK_API_KEY")
        if not self.api_key:
            raise ValueError("DEEPSEEK_API_KEY environment variable is not set")

        self.client = OpenAI(
            api_key=self.api_key,
            base_url="https://api.deepseek.com",
        )
        self.model = "deepseek-chat"

    def generate_content(
        self, system_prompt: str, user_prompt: str, temperature: float = 1.3
    ) -> str:
        """
        Generate content using DeepSeek API.

        Args:
            system_prompt: The system instruction context.
            user_prompt: The specific request.
            temperature: Creativity parameter.

        Returns:
            Generated text content.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"DeepSeek API call failed: {e}")
