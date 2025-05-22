import json
import logging
import os
from typing import Callable

from clients.centrala_client import CentralaClient
from clients.local_llm_client import LocalLLMClient
from clients.openai_client import AudioConfig, ChatConfig, ImageConfig, OpenAIClient


FILES_DIR_PATH = "/Users/mcbartop/Code/ai_devs_3/downloaded_data/pliki_z_fabryki"
EXCLUDED = ["2024-11-12_report-99.png", "facts", "extractions", "flag.png", "weapons_tests.zip"]


class TaskSolver:
    def __init__(
        self,
        openai_client: OpenAIClient,
        files_dir_path: str = FILES_DIR_PATH,
        excluded_files: list = EXCLUDED,
    ) -> None:
        self.files_dir_path = files_dir_path
        self.excluded_files = excluded_files
        self.transcriptions_path = os.path.join(self.files_dir_path, "transcriptions")
        self.files = {}
        self.results = {"people": [], "hardware": []}
        self.openai_client = openai_client

    def read_files(self):
        logging.info("Reading files from directory...")
        # Ensure the directory exists
        if not os.path.isdir(self.files_dir_path):
            raise ValueError(f"Directory {self.files_dir_path} does not exist.")

        # Clear the files dictionary
        logging.info("Clearing the files dictionary")
        # Iterate through files in the directory
        for filename in os.listdir(self.files_dir_path):
            if filename in self.excluded_files:
                continue

            # Determine file extension and categorize dynamically
            file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
            self.files.setdefault(file_ext, []).append(filename)

        logging.info(f"Files read: {json.dumps(self.files, indent=4)}")

    def process_text_files(self):
        for text_file in self.files.get("txt", []):
            logging.info(f"Processing text file: {text_file}")
            with open(os.path.join(self.files_dir_path, text_file), "r") as file:
                content = file.read()
                # Process the content as needed
                logging.info(content)

                # Process the content as needed
                category = self.categorize_content(content)

                if category:
                    self.results[category].append(text_file)

    def process_media_files(self, file_extensions: list[str], openai_method_name: str, config):
        """Process media files (images or audio) with transcription."""
        for ext in file_extensions:
            for media_file in self.files.get(ext, []):
                logging.info(f"Processing {ext} file: {media_file}")

                # Check if transcription already exists
                if transcription_file_path := self.check_if_transcription_exists(media_file):
                    # Process existing transcription
                    with open(transcription_file_path, "r") as file:
                        content = file.read()
                else:
                    logging.info(
                        "Transcription does not exist, sending to OpenAI for transcription."
                    )

                    # Get the appropriate OpenAI method and call it
                    openai_method: Callable = getattr(self.openai_client, openai_method_name)
                    content = openai_method(os.path.join(self.files_dir_path, media_file), config)

                    logging.info(f"Received transcription. Saving to file: {media_file}.txt")
                    with open(
                        os.path.join(self.transcriptions_path, f"{media_file}.txt"), "w"
                    ) as file:
                        file.write(content)

                # Process the content as needed
                category = self.categorize_content(content)

                if category:
                    self.results[category].append(media_file)

    def process_image_files(self):
        image_config = ChatConfig(model="gpt-4.1-mini", system_prompt=IMAGE_PROMPT)
        self.process_media_files(["png"], "image_to_text", image_config)

    def process_audio_files(self, audio_config: AudioConfig = AudioConfig(model="whisper-1")):
        self.process_media_files(["mp3"], "audio_to_text", audio_config)

    def categorize_content(self, content: str):
        logging.info("Categorizing content...")

        response = self.openai_client.send_message(
            content, config=ChatConfig(model="gpt-4.1-mini", system_prompt=CATEGORIZE_PROMPT)
        )
        response_dict = json.loads(response)
        content_category = response_dict.get("category", "unknown")

        logging.info(f"Content categorized as: {content_category}")

        if content_category not in self.results:
            logging.warning(f"Unknown content category '{content_category}' for content: {content}")
            return

        return content_category

    def check_if_transcription_exists(self, filename: str) -> str:
        transcription_file_path = os.path.join(self.transcriptions_path, f"{filename}.txt")
        if os.path.exists(transcription_file_path):
            logging.info(f"Transcription already exists for {filename}.")
            return transcription_file_path
        return ""


def main():
    openai_client = OpenAIClient()
    centrala_client = CentralaClient(task_identifier="kategorie")
    solver = TaskSolver(openai_client=openai_client)

    # 1. Read filenames and categorize them
    solver.read_files()

    # 2. Read text files
    solver.process_text_files()

    # 3. Transcribe audio files with OpenAI and save to text files
    solver.process_audio_files()

    # 4. Read image files with OpenAI and save to text files
    solver.process_image_files()

    # 5. Send the final results
    centrala_client.send_answer(solver.results)
