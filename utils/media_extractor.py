import re
import os
import requests
import logging
from pathlib import Path
from dataclasses import dataclass
from typing import Callable


@dataclass
class MediaMatch:
    """Represents a found media link with its position and metadata"""

    start: int
    end: int
    full_match: str
    file_path: str
    alt_text: str = ""
    is_image: bool = True
    extension: str = ""


class MediaExtractor:
    def __init__(self, base_url: str = "", download_dir: str = "downloads"):
        self.base_url = base_url.rstrip("/")
        # Make download_dir relative to the script file location
        script_dir = Path(__file__).parent
        self.download_dir = script_dir / download_dir
        self.download_dir.mkdir(exist_ok=True)

        # Regex patterns for different media types
        self.image_pattern = r"!\[([^\]]*)\]\(([^)]+)\)"
        self.link_pattern = r"\[([^\]]+\.(mp3|mp4|wav|avi|mov|pdf|zip|rar|doc|docx))\]\(([^)]+)\)"

    def find_media_links(self, text: str) -> list[MediaMatch]:
        """Find all media links in the text and return their positions"""
        matches = []

        # Find image links: ![alt](path)
        for match in re.finditer(self.image_pattern, text):
            matches.append(
                MediaMatch(
                    start=match.start(),
                    end=match.end(),
                    full_match=match.group(0),
                    file_path=match.group(2),
                    alt_text=match.group(1),
                    is_image=True,
                    extension=match.group(2).split(".")[-1],
                )
            )

        # Find file links: [filename.ext](path)
        for match in re.finditer(self.link_pattern, text):
            matches.append(
                MediaMatch(
                    start=match.start(),
                    end=match.end(),
                    full_match=match.group(0),
                    file_path=match.group(3),
                    alt_text=match.group(1),
                    is_image=False,
                    extension=match.group(2).split(".")[-1],
                )
            )

        # Sort by position to maintain order
        return sorted(matches, key=lambda x: x.start)

    def download_media(self, media_match: MediaMatch) -> str | None:
        """Download media file if it doesn't exist, return local path"""
        file_path = media_match.file_path

        # Handle relative paths
        if not file_path.startswith(("http://", "https://")):
            if self.base_url:
                url = f"{self.base_url}/{file_path.lstrip('/')}"
            else:
                # If no base URL, assume it's already a local path
                return file_path if Path(file_path).exists() else None
        else:
            url = file_path

        # Extract filename
        filename = Path(file_path).name
        local_path = self.download_dir / filename

        # Skip if already downloaded
        if local_path.exists():
            logging.info(f"File already exists: {local_path}")
            return str(local_path)

        try:
            logging.info(f"Downloading: {url}")
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            with open(local_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logging.info(f"Downloaded: {local_path}")
            return str(local_path)

        except requests.RequestException as e:
            logging.info(f"Failed to download {url}: {e}")
            return None

    def process_text(self, text: str) -> tuple[list[MediaMatch], dict[str, str]]:
        """
        Process text to find media links and download files.
        Returns: (media_matches, download_mapping)
        """
        media_matches = self.find_media_links(text)
        download_mapping = {}

        for match in media_matches:
            local_path = self.download_media(match)
            if local_path:
                download_mapping[match.file_path] = local_path

        return media_matches, download_mapping

    def replace_media_links(
        self, text: str, media_matches: list[MediaMatch], replacement_func: Callable | None = None
    ) -> str:
        """
        Replace media links in text using a custom replacement function.
        replacement_func should take (MediaMatch, local_path) and return new text.
        """

        if not replacement_func:
            replacement_func = self.replace_with_local_path

        # Process matches in reverse order to maintain positions
        result = text
        for match in reversed(media_matches):
            new_text = replacement_func(match)
            result = result[: match.start] + new_text + result[match.end :]

        return result

    @classmethod
    def replace_with_local_path(cls, match: MediaMatch) -> str:
        local_file = f"{self.download_dir}/{Path(match.file_path).name}"
        if match.is_image:
            return f"![{match.alt_text}]({local_file})"
        else:
            return f"[{match.alt_text}]({local_file})"


# Example usage
if __name__ == "__main__":
    # Sample markdown text
    sample_text = """
Some text here.

![](i/strangefruit.png)

Fuzja kodu genetycznego dwóch transportowanych owoców

[rafal_dyktafon.mp3](i/rafal_dyktafon.mp3)

More text.

![Alt text](i/resztki.png)
"""

    # Initialize extractor
    extractor = MediaExtractor(base_url="https://example.com", download_dir="media")

    # Find and process media
    media_matches, downloads = extractor.process_text(sample_text)

    # Print found matches
    logging.info("Found media links:")
    for match in media_matches:
        logging.info(f"  Position {match.start}-{match.end}: {match.full_match}")
        logging.info(f"    File: {match.file_path}")
        logging.info(f"    Alt: '{match.alt_text}'")
        logging.info(f"    Is image: {match.is_image}")

    # Replace links with local paths
    updated_text = extractor.replace_media_links(
        sample_text, media_matches, extractor.replace_with_local_path
    )
    logging.info("\nUpdated text:")
    logging.info(updated_text)
