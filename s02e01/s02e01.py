import json
import logging
import os

from clients.centrala_client import CentralaClient
from clients.local_llm_client import LocalLLMClient
from clients.openai_client import ChatConfig, OpenAIClient

from s02e01.prompt import SYSTEM_PROMPT


class TaskSolver:
    def __init__(
        self,
        audio_files_path: str = "task06/audio_files",
        transcriptions_files_path: str = "task06/transcriptions",
    ) -> None:
        self.audio_files_path = audio_files_path
        self.transcriptions_files_path = transcriptions_files_path
        self.openai_client = OpenAIClient()

    def transcribe_audio_files(self):
        """
        Transcribes audio files using the OpenAI API and saves the transcriptions to files.
        """
        # Get the list of audio files
        audio_files = os.listdir(self.audio_files_path)
        logging.info(f"Found {len(audio_files)} audio files to transcribe.")

        for audio_file in audio_files:
            logging.info(f"Transcribing {audio_file}...")

            transcription_filename = f"{audio_file}.txt"

            if transcription_filename in os.listdir(self.transcriptions_files_path):
                logging.info(f"Transcription for {audio_file} already exists. Skipping...")
                continue

            audio_file_path = os.path.join(self.audio_files_path, audio_file)
            transcription = self.openai_client.audio_to_text(audio_file_path)

            logging.info(f"Transcription for {audio_file}: \n{transcription}")
            logging.info(f"Saving transcription to {transcription_filename}...")
            # Save the transcription to a file
            transcription_file_path = os.path.join(
                self.transcriptions_files_path, transcription_filename
            )
            with open(transcription_file_path, "w") as f:
                f.write(transcription)

        logging.info("All files have been transcribed.")

    def read_transcriptions_content(self) -> str:
        """
        Reads the content of all transcription files and returns them as a list of strings.
        """
        logging.info("Reading transcriptions...")
        transcriptions = []
        for filename in os.listdir(self.transcriptions_files_path):
            logging.info(f"Reading {filename}...")
            with open(os.path.join(self.transcriptions_files_path, filename), "r") as f:
                transcriptions.append(f.read())

        transcriptions_content = "\n\n".join(transcriptions)
        logging.info("All transcriptions have been read.")
        logging.info(f"Transcriptions content: \n{transcriptions_content}")
        return transcriptions_content


def main():
    open_ai_client = OpenAIClient()
    centrala_client = CentralaClient(task_identifier="mp3")
    task_solver = TaskSolver()

    task_solver.transcribe_audio_files()
    llm_response = open_ai_client.send_message(
        config=ChatConfig(system_prompt=SYSTEM_PROMPT),
        message=task_solver.read_transcriptions_content(),
    )

    # The LLM response should be a JSON string, let's parse it to dict
    response_dict = json.loads(llm_response)
    ulica = response_dict.get("ulica")

    # Send the response back to Centrala
    centrala_client.send_answer(answer=ulica)

