import json
import logging
import os

from clients import openai_client
from clients.centrala_client import CentralaClient
from clients.local_llm_client import LocalLLMClient
from clients.openai_client import ChatConfig, OpenAIClient


FILES_DIR_PATH = "/Users/mcbartop/Code/ai_devs_3/downloaded_data/pliki_z_fabryki"
EXCLUDED = ["2024-11-12_report-99.png", "facts", "extractions", "flag.png", "weapons_tests.zip"]


class TaskSolver:
    def __init__(
        self, files_dir_path: str = FILES_DIR_PATH, excluded_files: list = EXCLUDED
    ) -> None:
        self.files_dir_path = files_dir_path
        self.excluded_files = excluded_files
        self.files = {}

    def read_files(self):
        logging.info("Reading files from directory...")
        # Ensure the directory exists
        if not os.path.isdir(self.files_dir_path):
            raise ValueError(f"Directory {self.files_dir_path} does not exist.")

        # Clear the files dictionary

        # Iterate through files in the directory
        for filename in os.listdir(self.files_dir_path):
            if filename in self.excluded_files:
                continue

            # Determine file extension and categorize dynamically
            file_ext = os.path.splitext(filename)[1].lower().lstrip(".")
            self.files.setdefault(file_ext, []).append(filename)

        logging.info(f"Files read: {json.dumps(self.files, indent=4)}")

    def process_audio_files(self):
        pass

    def process_text_files(self):
        pass
    
    def process_image_files(self):
        pass


def main():
    solver = TaskSolver()
    openai_client = OpenAIClient()

    solver.read_files()
