import json
import logging
from pathlib import Path
from typing import Any

from clients.centrala_client import CentralaClient
from clients.llm_configs import ChatConfig
from clients.openai_client import OpenAIClient
from s03e01.system_prompt import SYSTEM_PROMPT

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
DEFAULT_FILES_DIR = Path("/Users/mcbartop/Code/ai_devs_3/downloaded_data/pliki_z_fabryki")
ENCODING = "utf-8"


class TaskSolver:
    """Handles reading files and facts from a directory structure."""

    def __init__(self, files_dir_path: Path | str = DEFAULT_FILES_DIR) -> None:
        """Initialize TaskSolver with directory path.

        Args:
            files_dir_path: Path to the directory containing files and facts
        """
        self.files_dir_path = Path(files_dir_path)
        self._validate_directory()

        self.files: dict[str, str] = {}
        self.facts: list[str] = []

    def _validate_directory(self) -> None:
        """Validate that the files directory exists and is readable."""
        if not self.files_dir_path.exists():
            raise Exception(f"Directory does not exist: {self.files_dir_path}")

        if not self.files_dir_path.is_dir():
            raise Exception(f"Path is not a directory: {self.files_dir_path}")

    def load_data(self) -> None:
        """Load all text files and facts from the directory."""
        self._load_text_files()
        self._load_facts()

        logger.info(f"Successfully loaded {len(self.files)} files and {len(self.facts)} facts")

    def _load_text_files(self) -> None:
        """Load all .txt files from the main directory."""
        try:
            txt_files = list(self.files_dir_path.glob("*.txt"))

            for file_path in txt_files:
                try:
                    content = file_path.read_text(encoding=ENCODING)
                    self.files[file_path.name] = content
                    logger.debug(f"Loaded file: {file_path.name}")
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to decode file {file_path.name}: {e}")
                except IOError as e:
                    logger.warning(f"Failed to read file {file_path.name}: {e}")

        except Exception as e:
            raise Exception(f"Error loading text files: {e}") from e

    def _load_facts(self) -> None:
        """Load all .txt files from the facts subdirectory."""
        facts_dir = self.files_dir_path / "facts"

        if not facts_dir.exists():
            logger.warning(f"Facts directory does not exist: {facts_dir}")
            return

        if not facts_dir.is_dir():
            logger.warning(f"Facts path is not a directory: {facts_dir}")
            return

        try:
            fact_files = list(facts_dir.glob("*.txt"))

            for file_path in fact_files:
                try:
                    content = file_path.read_text(encoding=ENCODING).strip()
                    if content:  # Only add non-empty facts
                        self.facts.append(content)
                        logger.debug(f"Loaded fact from: {file_path.name}")
                except UnicodeDecodeError as e:
                    logger.warning(f"Failed to decode fact file {file_path.name}: {e}")
                except IOError as e:
                    logger.warning(f"Failed to read fact file {file_path.name}: {e}")

        except Exception as e:
            raise Exception(f"Error loading facts: {e}") from e

    def build_prompt_message(self) -> str:
        """Construct the user message with facts and reports.

        Returns:
            Formatted message string with facts and reports
        """
        if not self.facts and not self.files:
            logger.warning("No facts or files loaded when building prompt message")

        facts_section = "\n".join(self.facts) if self.facts else "No facts available"
        reports_section = json.dumps(self.files, indent=2, ensure_ascii=False)

        return f"""<facts>
            {facts_section}
            </facts>

            <raporty>
            {reports_section}
            </raporty>"""

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of loaded data.

        Returns:
            Dictionary with counts and sample data
        """
        return {
            "files_count": len(self.files),
            "facts_count": len(self.facts),
            "file_names": list(self.files.keys()),
            "sample_fact": self.facts[0] if self.facts else None,
        }


def process_llm_response(response: str) -> dict[str, Any]:
    """Parse and validate LLM response.

    Args:
        response: Raw response string from LLM

    Returns:
        Parsed JSON response

    Raises:
        TaskSolverError: If response cannot be parsed or is invalid
    """
    try:
        parsed_response = json.loads(response)

        if not isinstance(parsed_response, dict):
            raise Exception("LLM response is not a valid JSON object")

        if "answer" not in parsed_response:
            logger.warning("LLM response does not contain 'answer' field. Returning full JSON.")
            return parsed_response

        return parsed_response.get("answer", {})

    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse LLM response as JSON: {e}") from e


def main() -> None:
    """Main execution function."""
    try:
        # Initialize clients
        centrala_client = CentralaClient(task_identifier="dokumenty")
        openai_client = OpenAIClient()

        # Initialize and load data
        solver = TaskSolver()
        solver.load_data()

        # Log summary of loaded data
        summary = solver.get_summary()
        logger.info(f"Data summary: {summary}")

        # Build prompt and get LLM response
        user_message = solver.build_prompt_message()
        logger.info("Sending message to LLM...")

        logging.info(SYSTEM_PROMPT + user_message)

        llm_response = openai_client.send_message(
            message=user_message,
            config=ChatConfig(model="gpt-4.1-mini", system_prompt=SYSTEM_PROMPT),
        )

        # Process response
        answer = process_llm_response(llm_response)

        logger.info(f"Processed LLM response, answer type: {type(answer)}")
        logger.info(f"Answer content: {answer}")

        # Send answer
        centrala_client.send_answer(answer=answer)
        logger.info("Answer sent successfully")

    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
