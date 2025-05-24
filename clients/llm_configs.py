from dataclasses import dataclass

@dataclass
class ChatConfig:
    """Configuration for chat completion requests."""

    model: str = "gpt-4.1-nano"
    temperature: float = 0.1
    system_prompt: str = ""
    max_tokens: int = 2000


@dataclass
class AudioConfig:
    """Configuration for audio transcription requests."""

    model: str = "whisper-1"


@dataclass
class ImageConfig:
    """Configuration for image generation requests."""

    model: str = "dall-e-3"
    system_prompt: str = ""
