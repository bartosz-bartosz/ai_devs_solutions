import logging
from itertools import combinations
from clients.centrala_client import CentralaClient


class TaskSolver:
    """
    Solver for s04e02 - brute force all combinations of IDs until success.
    """

    def __init__(self):
        """Initialize the task solver with necessary clients."""
        self.logger = logging.getLogger("TaskSolver")
        self.centrala_client = CentralaClient("research")
        
    def load_correct_strings(self) -> set[str]:
        """Load all correct strings from correct.txt file."""
        correct_strings = set()
        try:
            with open("s04e02/correct.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if line:  # Just add non-empty lines
                        correct_strings.add(line)
                        self.logger.debug(f"Added correct string: {line}")
            self.logger.info(f"Loaded {len(correct_strings)} correct strings") 
            return correct_strings
        except FileNotFoundError:
            self.logger.error("correct.txt file not found")
            return set()

    def verify_lines_against_correct(self) -> list[str]:
        """Check each line in verify.txt against correct strings."""
        correct_strings = self.load_correct_strings()
        correct_ids = []
        
        try:
            with open("s04e02/verify.txt", "r") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line:
                        # Split by '=' to get ID and content
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            id_part = parts[0]
                            content = parts[1]
                            
                            # Extract just the number part (01, 02, etc.)
                            id_num = id_part.split("→")[1] if "→" in id_part else id_part
                            id_num = id_num.strip()
                            
                            # Check if content is in correct strings
                            if content in correct_strings:
                                correct_ids.append(id_num)
                                self.logger.info(f"ID {id_num} is CORRECT: {content}")
                            else:
                                self.logger.info(f"ID {id_num} is INCORRECT: {content}")
            
            return correct_ids
        except FileNotFoundError:
            self.logger.error("verify.txt file not found")
            return []

    def solve(self) -> any:
        """
        Main solving logic for the task.
        
        Returns:
            List of correct IDs
        """
        correct_ids = self.verify_lines_against_correct()
        self.logger.info(f"Found {len(correct_ids)} correct IDs: {correct_ids}")
        return correct_ids


def main():
    """Main function to execute the task."""
    logging.basicConfig(
        level=logging.INFO, 
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    logger = logging.getLogger("s04e02")
    logger.info("Starting s04e02 - verify strings against correct list")
    
    try:
        solver = TaskSolver()
        answer = solver.solve()
        
        if answer:
            logger.info(f"Sending answer to Centrala: {answer}")
            solver.centrala_client.send_answer(answer)
            logger.info("Task completed successfully!")
        else:
            logger.error("Task failed - no correct IDs found")
            
    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise


if __name__ == "__main__":
    main()