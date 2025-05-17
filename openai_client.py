import logging
import os
from openai import OpenAI


class OpenAIClient:
    def __init__(self, model: str = "gpt-4.1-nano", temperature: float = 0.1, system_prompt: str = ""):
        self.logger = logging.getLogger("OpenAIClient")
        self.model = model
        self.client = OpenAI(api_key=self._get_api_key())
        self.system_prompt = system_prompt
        self.temperature = temperature

    def send_message(self, message: str) -> str:

        message.encode("utf-8")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=self.temperature,
            )
            answer = response.choices[0].message.content.strip()

            self.logger.info(f"Received answer: {answer}")

            return answer

        except Exception as e:
            self.logger.error(f"Error communicating with OpenAI API: {e}")
            raise

    def _get_api_key(self):
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            self.logger.error("Error reading OpenAI API key from environment variable")
            raise ValueError("No OpenAI API key found in environment variable. Set OPENAI_API_KEY.")

    def _set_system_prompt(self, prompt: str):
        self.logger.info("Setting system prompt")
        self.system_prompt = prompt
