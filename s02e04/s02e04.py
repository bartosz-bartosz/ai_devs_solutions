import json
import logging
import os
from typing import Callable

from clients.centrala_client import CentralaClient
from clients.local_llm_client import LocalLLMClient
from clients.openai_client import AudioConfig, ChatConfig, ImageConfig, OpenAIClient

from s02e04.prompts import CATEGORIZE_PROMPT, IMAGE_PROMPT


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
        logging.info(f"Scanning directory: {self.files_dir_path}")

        if not os.path.isdir(self.files_dir_path):
            raise ValueError(f"Directory {self.files_dir_path} does not exist.")

        # Add count logging:
        total_files = len(os.listdir(self.files_dir_path))
        logging.info(f"Found {total_files} total files in directory")

        self.files.clear()

        excluded_count = 0
        for filename in os.listdir(self.files_dir_path):
            if filename in self.excluded_files:
                excluded_count += 1
                logging.debug(f"Excluding file: {filename}") 
                continue

            file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
            self.files.setdefault(file_ext, []).append(filename)

        # Add summary logging:
        logging.info(f"Excluded {excluded_count} files")
        logging.info(f"Files by extension: {dict((k, len(v)) for k, v in self.files.items())}")

    def process_text_files(self):
        text_files = self.files.get("txt", [])
        logging.info(f"Processing {len(text_files)} text files")

        for text_file in text_files:
            logging.info(f"Processing text file: {text_file}")
            try:
                with open(os.path.join(self.files_dir_path, text_file), "r") as file:
                    content = file.read()
                    logging.info(f"Read {len(content)} characters from {text_file}")

                    category = self.categorize_content(content)

                    if category:
                        self.results[category].append(text_file)
                        logging.info(f"Added {text_file} to category: {category}")
                    else:
                        logging.warning(f"No category assigned to {text_file}")

            except Exception as e:
                logging.error(f"Error processing {text_file}: {e}")

    def process_media_files(self, file_extensions: list[str], openai_method_name: str, config):
        # Add this at the start:
        os.makedirs(self.transcriptions_path, exist_ok=True)
        logging.info(f"Ensured transcriptions directory exists: {self.transcriptions_path}")

        total_files = sum(len(self.files.get(ext, [])) for ext in file_extensions)
        logging.info(f"Processing {total_files} media files with extensions: {file_extensions}")

        for ext in file_extensions:
            files_for_ext = self.files.get(ext, [])
            logging.info(f"Processing {len(files_for_ext)} {ext} files")

            for media_file in files_for_ext:
                logging.info(f"Processing {ext} file: {media_file}")

                try:
                    if transcription_file_path := self.check_if_transcription_exists(media_file):
                        logging.info(f"Using existing transcription: {transcription_file_path}")
                        with open(transcription_file_path, "r") as file:
                            content = file.read()
                            logging.info(f"Loaded existing transcription ({len(content)} chars)")
                    else:
                        logging.info("No existing transcription, calling OpenAI API...")

                        openai_method: Callable = getattr(self.openai_client, openai_method_name)
                        content = openai_method(
                            os.path.join(self.files_dir_path, media_file), config
                        )

                        logging.info(f"Received transcription ({len(content)} chars), saving...")
                        transcription_path = os.path.join(
                            self.transcriptions_path, f"{media_file}.txt"
                        )
                        with open(transcription_path, "w") as file:
                            file.write(content)
                        logging.info(f"Saved transcription to: {transcription_path}")

                    category = self.categorize_content(content)

                    if category:
                        self.results[category].append(media_file)
                        logging.info(f"Added {media_file} to category: {category}")
                    else:
                        logging.warning(f"No category assigned to {media_file}")

                except Exception as e:
                    logging.error(f"Error processing {media_file}: {e}")

    def process_image_files(self):
        image_config = ChatConfig(model="gpt-4.1-mini", system_prompt=IMAGE_PROMPT)
        self.process_media_files(["png"], "image_to_text", image_config)

    def process_audio_files(self, audio_config: AudioConfig = AudioConfig(model="whisper-1")):
        self.process_media_files(["mp3"], "audio_to_text", audio_config)

    def categorize_content(self, content: str):
        logging.info(f"Categorizing content ({len(content)} characters)...")

        try:
            response = self.openai_client.send_message(
                content,
                config=ChatConfig(
                    model="gpt-4o-mini", system_prompt=CATEGORIZE_PROMPT
                ),  # Fix model name
            )
            logging.debug(f"OpenAI response: {response}")  # Add this for debugging

            response_dict = json.loads(response)
            content_category = response_dict.get("category", "unknown")

            logging.info(f"Content categorized as: {content_category}")

            if content_category not in self.results:
                logging.warning(
                    f"Unknown content category '{content_category}' for content preview: {content[:100]}..."
                )
                return None  # Make this explicit

            return content_category

        except json.JSONDecodeError as e:
            logging.error(f"Failed to parse OpenAI response as JSON: {e}")
            logging.error(f"Raw response: {response}")
            return None
        except Exception as e:
            logging.error(f"Error categorizing content: {e}")
            return None

    def check_if_transcription_exists(self, filename: str) -> str:
        transcription_file_path = os.path.join(self.transcriptions_path, f"{filename}.txt")
        if os.path.exists(transcription_file_path):
            logging.info(f"Transcription already exists for {filename}.")
            return transcription_file_path
        return ""

    def save_results_to_json(self):
        with open(os.path.join(self.files_dir_path, "results.json"), "w") as file:
            json.dump(self.results, file, indent=4)


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

    # 5. Save results to file
    solver.save_results_to_json()

    # 6. Send the final results
    centrala_client.send_answer(solver.results)
