import logging
import json
import requests


class LocalLLMClient:
    """
    A client for interacting with a local LLM server through LM Studio.

    Attributes:
        model (str): The model to use for generating responses.
        temperature (float): The temperature setting for response generation.
        system_prompt (str): The system prompt to guide the model's behavior.
        base_url (str): The base URL for the local LLM API.
    """

    def __init__(
        self,
        model: str = "deepseek-r1-distill-qwen-7b:2",
        temperature: float = 0.1,
        system_prompt: str = "",
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
        self.model = model
        self.system_prompt = system_prompt
        self.temperature = temperature
        self.base_url = base_url

    def send_message(self, message: str, max_tokens: int = 1000, stream: bool = False) -> str:
        """
        Sends a message to the local LLM API and retrieves the response.

        Args:
            message (str): The user message to send to the API.
            max_tokens (int): Maximum number of tokens to generate.
            stream (bool): Whether to stream the response.

        Returns:
            str: The response from the API.

        Raises:
            Exception: If an error occurs while communicating with the API.
        """
        # Ensure the message is properly encoded
        message.encode("utf-8")

        try:
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": message},
                ],
                "temperature": self.temperature,
                "max_tokens": max_tokens,
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
            answer = response_data["choices"][0]["message"]["content"].strip()

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
        # Ensure the message is properly encoded
        message.encode("utf-8")

        try:
            # Prepare the request payload
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": message},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {"name": schema_name, "strict": "true", "schema": schema},
                },
                "temperature": self.temperature,
                "max_tokens": max_tokens,
                "stream": False,
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
            json_content = response_data["choices"][0]["message"]["content"]
            answer = json.loads(json_content)

            # Log the received answer (summarized for large responses)
            self.logger.info(f"Received JSON response: {str(answer)[:100]}...")

            return answer

        except requests.exceptions.RequestException as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error communicating with local LLM API: {e}")
            raise
        except json.JSONDecodeError as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error parsing JSON response: {e}")
            raise
        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Unexpected error: {e}")
            raise

    def _set_system_prompt(self, prompt: str):
        """
        Updates the system prompt for the local LLM.

        Args:
            prompt (str): The new system prompt.
        """
        # Log the update of the system prompt
        self.logger.info("Setting system prompt")
        self.system_prompt = prompt
