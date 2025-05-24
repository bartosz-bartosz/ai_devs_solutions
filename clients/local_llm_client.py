import logging
import json
import requests
import re

from clients.llm_configs import ChatConfig, AudioConfig, ImageConfig


class LocalLLMClient:
    """
    A client for interacting with a local LLM server through LM Studio.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:1234",
    ):
        """
        Initializes the LocalLLMClient with the specified model, temperature, and system prompt.

        Args:
            model (str): The model to use for generating responses.
            temperature (float): The temperature setting for response generation.
            system_prompt (str): The system prompt to guide the model's behavior.
            base_url (str): The base URL for the local LLM API.
        """
        self.logger = logging.getLogger("LocalLLMClient")
        self.base_url = base_url

    def _clean_response(self, text: str) -> str:
        """
        Removes <think>thinking content</think> tags from the response.

        Args:
            text (str): The response text to clean.

        Returns:
            str: The cleaned response text.
        """
        # Use regular expression to remove <think>...</think> blocks
        cleaned_text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)

        # If we removed something, log it
        if text != cleaned_text:
            self.logger.debug(f"Original response: {text}")
            self.logger.info("Removed thinking section from response")

        return cleaned_text.strip()

    def send_message(
        self,
        message: str,
        stream: bool = False,
        config: ChatConfig = ChatConfig(),
    ) -> str:
        """
        Sends a message to the local LLM API and retrieves the response.

        Args:
            message (str): The user message to send to the API.
            max_tokens (int): Maximum number of tokens to generate.
            stream (bool): Whether to stream the response.

        Returns:
            str: The response from the API with any thinking sections removed.

        Raises:
            Exception: If an error occurs while communicating with the API.
        """
        # Ensure the message is properly encoded
        message.encode("utf-8")

        try:
            # Prepare the request payload
            payload = {
                "model": config.model,
                "messages": [
                    {"role": "system", "content": config.system_prompt},
                    {"role": "user", "content": message},
                ],
                "temperature": config.temperature,
                "max_tokens": config.max_tokens,
                "stream": stream,
            }

            # Send the message to the local LLM API and retrieve the response
            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                data=json.dumps(payload),
            )

            # Raise an exception if the request was unsuccessful
            response.raise_for_status()

            # Parse the response
            response_data = response.json()
            raw_answer = response_data["choices"][0]["message"]["content"]

            # Clean the response to remove thinking sections
            answer = self._clean_response(raw_answer)

            # Log the received answer
            self.logger.info(f"Received answer: {answer}")

            return answer

        except requests.exceptions.RequestException as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error communicating with local LLM API: {e}")
            raise
        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Unexpected error: {e}")
            raise

    def send_message_with_json_schema(
        self, message: str, schema_name: str, schema: dict, max_tokens: int = 1000
    ) -> dict:
        """
        Sends a message to the local LLM API with a JSON schema for structured responses.

        Args:
            message (str): The user message to send to the API.
            schema_name (str): The name for the JSON schema.
            schema (dict): The JSON schema definition.
            max_tokens (int): Maximum number of tokens to generate.

        Returns:
            dict: The structured JSON response from the API.

        Raises:
            Exception: If an error occurs while communicating with the API.
        """
        pass
