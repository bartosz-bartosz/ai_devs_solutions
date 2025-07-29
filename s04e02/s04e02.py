import logging
from clients.centrala_client import CentralaClient
from clients.openai_client import OpenAIClient
from clients.llm_configs import ChatConfig


class TaskSolver:
    """
    Solver for S04E02 task - using fine-tuned model to verify text lines.
    """

    def __init__(self):
        """Initialize the task solver with necessary clients."""
        self.logger = logging.getLogger("TaskSolver")
        self.openai_client = OpenAIClient()
        self.centrala_client = CentralaClient("research")

        # Configure the fine-tuned model
        self.config = ChatConfig(
            model="ft:gpt-4.1-nano-2025-04-14:personal:aidevs-s04e02:ByKtTyE8",  # Fine-tuned model with suffix
            system_prompt="",  # No system prompt needed for fine-tuned model
            temperature=0.0,  # Use deterministic output
        )

    def read_verify_file(self) -> list[tuple[str, str]]:
        """
        Read verify.txt file and parse lines into ID and content pairs.

        Returns:
            List of tuples containing (line_id, content)
        """
        self.logger.info("Reading verify.txt file")

        lines_data = []

        try:
            with open("s04e02/verify.txt", "r", encoding="utf-8") as file:
                for line in file:
                    line = line.strip()
                    if not line:
                        continue

                    # Split by '=' to get ID and content
                    parts = line.split("=", 1)
                    if len(parts) != 2:
                        self.logger.warning(f"Skipping malformed line: {line}")
                        continue

                    line_id = parts[0]
                    content = parts[1]
                    lines_data.append((line_id, content))

            self.logger.info(f"Successfully read {len(lines_data)} lines from verify.txt")
            return lines_data

        except FileNotFoundError:
            self.logger.error("verify.txt file not found in s04e02/ directory")
            raise
        except Exception as e:
            self.logger.error(f"Error reading file: {e}")
            raise

    def verify_line_with_model(self, content: str) -> bool:
        """
        Send line content to fine-tuned model for verification.

        Args:
            content: The text content to verify

        Returns:
            True if model returns "1" (correct), False if "0" (incorrect)
        """
        try:
            response = self.openai_client.send_message(content, self.config)
            response_clean = response.strip()

            if response_clean == "1":
                return True
            elif response_clean == "0":
                return False
            else:
                self.logger.warning(
                    f"Unexpected model response: '{response_clean}' for content: '{content}'"
                )
                # Default to incorrect if response is unexpected
                return False

        except Exception as e:
            self.logger.error(f"Error querying model for content '{content}': {e}")
            # Default to incorrect if there's an error
            return False

    def solve(self) -> list[str]:
        """
        Main solving logic to process all lines and find correct ones.

        Returns:
            List of correct line IDs as strings
        """
        self.logger.info("Starting S04E02 task - verifying text lines with fine-tuned model")

        # Step 1: Read and parse verify.txt
        lines_data = self.read_verify_file()

        # Step 2: Process each line with fine-tuned model
        correct_ids = []

        for line_id, content in lines_data:
            self.logger.info(f"Processing line {line_id}: {content}")

            is_correct = self.verify_line_with_model(content)

            if is_correct:
                correct_ids.append(line_id)
                self.logger.info(f"Line {line_id} marked as CORRECT")
            else:
                self.logger.info(f"Line {line_id} marked as INCORRECT")

        self.logger.info(f"Found {len(correct_ids)} correct lines: {correct_ids}")
        return correct_ids


def main():
    """Main function to execute the S04E02 task."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger("S04E02")
    logger.info("Starting S04E02 - Fine-tuned model verification task")

    try:
        # Initialize task solver
        solver = TaskSolver()

        # Solve the task
        correct_ids = solver.solve()

        # Send answer to Centrala
        logger.info(f"Sending answer to Centrala: {correct_ids}")
        solver.centrala_client.send_answer(correct_ids)

        logger.info("Task completed successfully!")

    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise


if __name__ == "__main__":
    main()

