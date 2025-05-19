import logging
import os
from dataclasses import dataclass
from openai import OpenAI


@dataclass
class ChatConfig:
    """Configuration for chat completion requests."""
    model: str = "gpt-4.1-nano"
    temperature: float = 0.1
    system_prompt: str = ""


@dataclass
class AudioConfig:
    """Configuration for audio transcription requests."""
    model: str = "whisper-1"


class OpenAIClient:
    """
    A client for interacting with the OpenAI API.
    Supports multiple API features with configurable settings.
    """

    def __init__(self, api_key=None):
        """
        Initializes the OpenAIClient with the API key.

        Args:
            api_key (str, optional): The OpenAI API key. If None, retrieves from environment.
        """
        self.logger = logging.getLogger("OpenAIClient")
        self.client = OpenAI(api_key=api_key or self._get_api_key())

    def send_message(self, message: str, config: ChatConfig = ChatConfig()) -> str:
        """
        Sends a message to the OpenAI API and retrieves the response.

        Args:
            message (str): The user message to send to the API.
            config (ChatConfig, optional): Configuration for the chat request.

        Returns:
            str: The response from the API.

        Raises:
            Exception: If an error occurs while communicating with the API.
        """
        # Use provided config or default
        if config is None:
            config = ChatConfig()

        # Ensure the message is properly encoded
        message.encode("utf-8")

        try:
            # Send the message to the OpenAI API and retrieve the response
            response = self.client.chat.completions.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": config.system_prompt},
                    {"role": "user", "content": message},
                ],
                temperature=config.temperature,
            )
            answer = response.choices[0].message.content.strip()

            # Log the received answer
            self.logger.info(f"Received answer: {answer}")

            return answer

        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error communicating with OpenAI API: {e}")
            raise

    def audio_to_text(self, audio_file_path: str, config: AudioConfig = AudioConfig()) -> str:
        """
        Transcribes an audio file using the OpenAI API.

        Args:
            audio_file_path (str): The path to the audio file to transcribe.
            config (AudioConfig, optional): Configuration for the audio transcription.

        Returns:
            str: The transcribed text from the audio file.

        Raises:
            Exception: If an error occurs during transcription.
        """
        # Use provided config or default
        if config is None:
            config = AudioConfig()

        try:
            with open(audio_file_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    file=audio_file,
                    model=config.model
                )
                transcription = response.text.strip()

                # Log the transcription result
                self.logger.info(f"Transcription result: {transcription}")

                return transcription

        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error during audio transcription: {e}")
            raise

    def _get_api_key(self) -> str:
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
