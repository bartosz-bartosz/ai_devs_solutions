import base64
import logging
import os
from openai import OpenAI
from clients.llm_configs import ChatConfig, AudioConfig, ImageConfig

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
                    file=audio_file, model=config.model
                )
                transcription = response.text.strip()

                # Log the transcription result
                self.logger.info(f"Transcription result: {transcription}")

                return transcription

        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error during audio transcription: {e}")
            raise

    def generate_image(self, prompt: str, config: ImageConfig = ImageConfig(), n: int = 1) -> str:
        self.logger.info("Sending request to create image...")
        try:
            img_response = self.client.images.generate(
                model=config.model, prompt=prompt, n=1, size="1024x1024"
            )
            image_url = img_response.data[0].url

            if not image_url:
                raise Exception("No URL found in response.")
            self.logger.info(f"Image URL received: {image_url}")

            return image_url

        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error communicating with OpenAI API: {e}")
            raise

    def image_to_text(self, image_file_path: str, config: ChatConfig = ChatConfig()) -> str:
        """
        Analyzes an image file using the OpenAI API and returns a description.

        Args:
            image_file_path (str): The path to the image file to analyze.
            config (ChatConfig, optional): Configuration for the chat request.

        Returns:
            str: The description of the image.

        Raises:
            Exception: If an error occurs during image analysis.
        """
        self.logger.info(f"Sending request to analyze image: {image_file_path}")
        try:
            # Read and encode the image file
            with open(image_file_path, "rb") as image_file:

                image_data = base64.b64encode(image_file.read()).decode("utf-8")

            # Determine the image format from file extension
            file_extension = os.path.splitext(image_file_path)[1].lower()
            if file_extension in [".jpg", ".jpeg"]:
                image_format = "jpeg"
            elif file_extension == ".png":
                image_format = "png"
            elif file_extension == ".gif":
                image_format = "gif"
            elif file_extension == ".webp":
                image_format = "webp"
            else:
                image_format = "jpeg"  # Default fallback

            # Send the image to the OpenAI API
            response = self.client.chat.completions.create(
                model=config.model,
                messages=[
                    {"role": "system", "content": config.system_prompt},
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/{image_format};base64,{image_data}"
                                },
                            }
                        ],
                    },
                ],
                temperature=config.temperature,
            )

            description = response.choices[0].message.content.strip()

            # Log the received description
            self.logger.info(f"Received image transcription: {description}")

            return description

        except Exception as e:
            # Log the error and re-raise the exception
            self.logger.error(f"Error during image analysis: {e}")
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
