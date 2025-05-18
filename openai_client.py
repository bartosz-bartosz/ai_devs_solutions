import logging
import os
from openai import OpenAI

# This module provides a client for interacting with the OpenAI API.
# It includes methods for sending messages to the API and managing system prompts.

class OpenAIClient:
    """
    A client for interacting with the OpenAI API.

    Attributes:
        model (str): The model to use for generating responses.
        temperature (float): The temperature setting for response generation.
        system_prompt (str): The system prompt to guide the model's behavior.
    """

    def __init__(self, model: str = "gpt-4.1-nano", temperature: float = 0.1, system_prompt: str = ""):
        """
        Initializes the OpenAIClient with the specified model, temperature, and system prompt.

        Args:
            model (str): The model to use for generating responses.
            temperature (float): The temperature setting for response generation.
            system_prompt (str): The system prompt to guide the model's behavior.
        """
        self.logger = logging.getLogger("OpenAIClient")
        self.model = model
        self.client = OpenAI(api_key=self._get_api_key())
        self.system_prompt = system_prompt
        self.temperature = temperature

    def send_message(self, message: str) -> str:
        """
        Sends a message to the OpenAI API and retrieves the response.

        Args:
            message (str): The user message to send to the API.

        Returns:
            str: The response from the API.

        Raises:
            Exception: If an error occurs while communicating with the API.
        """
        # Ensure the message is properly encoded
        message.encode("utf-8")

        try:
            # Send the message to the OpenAI API and retrieve the response
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=self.temperature,
            )
            answer = response.choices[0].message.content.strip()

            # Log the received answer
            self.logger.info(f"Received answer: {answer}")

            return answer

        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error communicating with OpenAI API: {e}")
            raise

    def _get_api_key(self):
        """
        Retrieves the OpenAI API key from the environment variables.

        Returns:
            str: The API key.

        Raises:
            ValueError: If the API key is not found in the environment variables.
        """
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            # Log an error if the API key is missing
            self.logger.error("Error reading OpenAI API key from environment variable")
            raise ValueError("No OpenAI API key found in environment variable. Set OPENAI_API_KEY.")
        return api_key

    def _set_system_prompt(self, prompt: str):
        """
        Updates the system prompt for the OpenAI API.

        Args:
            prompt (str): The new system prompt.
        """
        # Log the update of the system prompt
        self.logger.info("Setting system prompt")
        self.system_prompt = prompt

