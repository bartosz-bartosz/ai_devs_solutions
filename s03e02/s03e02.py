import logging
import os
import re

from pathlib import Path
from clients.openai_client import OpenAIClient
from clients.qdrant_client import QdrantClient
from clients.centrala_client import CentralaClient

# Global configuration
FILES_DIRECTORY = Path(
    "/Users/mcbartop/Code/ai_devs_3/downloaded_data/pliki_z_fabryki/do-not-share/"
)
COLLECTION_NAME = "weapon_reports"
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1536
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
TASK_IDENTIFIER = "wektory"


class TaskSolver:
    """
    Solver for the vector database task involving weapon test reports.
    """

    def __init__(self):
        """Initialize the task solver with required clients."""
        self.openai_client = OpenAIClient()
        self.qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)
        self.centrala_client = CentralaClient(task_identifier=TASK_IDENTIFIER)
        logging.info("TaskSolver initialized successfully")

    def setup_vector_database(self) -> bool:
        """
        Set up the Qdrant vector database collection for weapon reports.

        Returns:
            True if collection was created/recreated, False if existing collection is being reused
        """
        logging.info(f"Setting up vector database collection: {COLLECTION_NAME}")

        # Check if collection already exists
        if self.qdrant_client.collection_exists(COLLECTION_NAME):
            logging.info(f"Collection {COLLECTION_NAME} already exists")

            # Get collection info to verify it's properly configured
            info = self.qdrant_client.get_collection_info(COLLECTION_NAME)
            if info and info["config"]["vector_size"] == EMBEDDING_DIMENSIONS:
                logging.info(f"Existing collection has correct vector size ({EMBEDDING_DIMENSIONS})")
                logging.info(f"Collection currently contains {info['points_count']} points")
                return False  # Collection exists and is properly configured
            else:
                logging.warning("Existing collection has incorrect configuration, recreating...")
                if not self.qdrant_client.delete_collection(COLLECTION_NAME):
                    logging.error(f"Failed to delete existing collection {COLLECTION_NAME}")
                    raise Exception(f"Failed to delete existing collection {COLLECTION_NAME}")

        # Create new collection
        if not self.qdrant_client.create_collection(
            collection_name=COLLECTION_NAME, vector_size=EMBEDDING_DIMENSIONS
        ):
            logging.error(f"Failed to create collection {COLLECTION_NAME}")
            raise Exception(f"Failed to create collection {COLLECTION_NAME}")

        logging.info(f"Vector database collection {COLLECTION_NAME} created successfully")
        return True  # Collection was created/recreated

    def extract_date_from_filename(self, filename: str) -> str:
        """
        Extract date from filename and convert to YYYY-MM-DD format.

        Args:
            filename: Name of the file (e.g., "2024_05_08.txt")

        Returns:
            Date string in YYYY-MM-DD format
        """
        # Extract date pattern from filename (YYYY_MM_DD format)
        date_pattern = r"^(\d{4})_(\d{2})_(\d{2})"
        match = re.match(date_pattern, filename)

        if not match:
            logging.error(f"Could not extract date from filename: {filename}")
            raise Exception(f"Invalid filename format: {filename}")

        year, month, day = match.groups()
        date_str = f"{year}-{month}-{day}"
        logging.info(f"Extracted date {date_str} from filename {filename}")
        return date_str

    def read_report_files(self) -> list[dict]:
        """
        Read all report files from the specified directory.

        Returns:
            List of dictionaries containing file data
        """
        logging.info(f"Reading report files from directory: {FILES_DIRECTORY}")

        if not os.path.exists(FILES_DIRECTORY):
            logging.error(f"Directory {FILES_DIRECTORY} does not exist")
            raise Exception(f"Directory {FILES_DIRECTORY} does not exist")

        reports = []
        txt_files = [f for f in os.listdir(FILES_DIRECTORY) if f.endswith(".txt")]

        if not txt_files:
            logging.error(f"No .txt files found in directory {FILES_DIRECTORY}")
            raise Exception(f"No .txt files found in directory {FILES_DIRECTORY}")

        logging.info(f"Found {len(txt_files)} report files")

        for filename in txt_files:
            try:
                # Extract date from filename
                report_date = self.extract_date_from_filename(filename)

                # Read file content
                file_path = os.path.join(FILES_DIRECTORY, filename)
                with open(file_path, "r", encoding="utf-8") as file:
                    content = file.read().strip()

                reports.append({"filename": filename, "date": report_date, "content": content})

                logging.info(f"Successfully read report: {filename}")

            except Exception as e:
                logging.error(f"Error reading file {filename}: {e}")
                raise Exception(f"Error reading file {filename}: {e}")

        return reports

    def check_existing_reports(self, reports: list[dict]) -> list[dict]:
        """
        Check which reports are already indexed and return only missing ones.

        Args:
            reports: List of all report dictionaries

        Returns:
            List of reports that need to be indexed
        """
        logging.info("Checking for existing reports in the database")

        # Get all existing points in the collection
        collection_info = self.qdrant_client.get_collection_info(COLLECTION_NAME)
        if not collection_info or collection_info["points_count"] == 0:
            logging.info("No existing reports found, will index all reports")
            return reports

        # Check which reports are already indexed by looking for their dates in metadata
        existing_dates = set()
        reports_to_process = []

        for report in reports:
            # Try to find if this report already exists by searching for exact date match
            try:
                # Create a simple filter for this specific date
                date_filter = self.qdrant_client.create_field_filter("date", report["date"])
                count = self.qdrant_client.count_points(COLLECTION_NAME, date_filter)

                if count > 0:
                    logging.info(f"Report for date {report['date']} already exists, skipping")
                    existing_dates.add(report["date"])
                else:
                    logging.info(f"Report for date {report['date']} not found, will index")
                    reports_to_process.append(report)

            except Exception as e:
                logging.warning(f"Error checking existing report for date {report['date']}: {e}")
                # If we can't check, include it to be safe
                reports_to_process.append(report)

        logging.info(
            f"Found {len(existing_dates)} existing reports, {len(reports_to_process)} reports to process"
        )
        return reports_to_process

    def generate_embeddings_and_index(self, reports: list[dict]) -> None:
        """
        Generate embeddings for reports and index them in the vector database.

        Args:
            reports: List of report dictionaries
        """
        if not reports:
            logging.info("No reports to process, skipping embedding generation")
            return

        logging.info(
            f"Starting embedding generation and indexing process for {len(reports)} reports"
        )

        # Get the current max point ID to avoid conflicts
        collection_info = self.qdrant_client.get_collection_info(COLLECTION_NAME)
        start_id = collection_info["points_count"] + 1 if collection_info else 1

        for i, report in enumerate(reports):
            try:
                logging.info(f"Processing report {i + 1}/{len(reports)}: {report['filename']}")

                # Generate embedding for report content
                embedding = self.openai_client.create_embedding(
                    input_text=report["content"], model=EMBEDDING_MODEL
                )

                # Prepare metadata
                metadata = {"date": report["date"], "filename": report["filename"]}

                # Add point to vector database with unique ID
                point_id = start_id + i
                success = self.qdrant_client.add_point(
                    collection_name=COLLECTION_NAME,
                    point_id=point_id,
                    vector=embedding,
                    payload=metadata,
                )

                if not success:
                    logging.error(f"Failed to index report: {report['filename']}")
                    raise Exception(f"Failed to index report: {report['filename']}")

                logging.info(f"Successfully indexed report: {report['filename']}")

            except Exception as e:
                logging.error(f"Error processing report {report['filename']}: {e}")
                raise Exception(f"Error processing report {report['filename']}: {e}")

        logging.info(f"Successfully indexed {len(reports)} new reports")

    def search_for_theft_mention(self) -> str:
        """
        Search for the report mentioning weapon prototype theft.

        Returns:
            Date string in YYYY-MM-DD format of the report mentioning theft
        """
        query = "W raporcie, z którego dnia znajduje się wzmianka o kradzieży prototypu broni?"
        logging.info(f"Searching for theft mention with query: {query}")

        try:
            # Generate embedding for the query
            query_embedding = self.openai_client.create_embedding(
                input_text=query, model=EMBEDDING_MODEL
            )

            # Search in vector database
            search_results = self.qdrant_client.search(
                collection_name=COLLECTION_NAME, query_vector=query_embedding, limit=1
            )

            if not search_results:
                logging.error("No search results found")
                raise Exception("No search results found")

            # Get the most similar result
            best_match = search_results[0]
            theft_date = best_match["payload"]["date"]
            filename = best_match["payload"]["filename"]
            score = best_match["score"]

            logging.info(f"Found theft mention in file: {filename}")
            logging.info(f"Report date: {theft_date}")
            logging.info(f"Similarity score: {score}")

            return theft_date

        except Exception as e:
            logging.error(f"Error during search: {e}")
            raise Exception(f"Error during search: {e}")

    def get_collection_info(self) -> None:
        """
        Log information about the created collection for verification.
        """
        info = self.qdrant_client.get_collection_info(COLLECTION_NAME)
        if info:
            logging.info(f"Collection info: {info}")
        else:
            logging.warning("Could not retrieve collection information")


def main():
    """
    Main function to execute the task solution.
    """
    logging.info("Starting S03E02 task - Vector Database for Weapon Reports")

    try:
        # Initialize task solver
        task_solver = TaskSolver()

        # Set up vector database
        collection_recreated = task_solver.setup_vector_database()

        # Read all report files
        reports = task_solver.read_report_files()
        logging.info(f"Successfully read {len(reports)} reports")

        # Check which reports need to be processed (skip if collection wasn't recreated)
        if collection_recreated:
            reports_to_process = reports
            logging.info("Collection was recreated, will process all reports")
        else:
            reports_to_process = task_solver.check_existing_reports(reports)

        # Generate embeddings and index reports
        task_solver.generate_embeddings_and_index(reports_to_process)

        # Log collection information
        task_solver.get_collection_info()

        # Search for theft mention
        answer = task_solver.search_for_theft_mention()
        logging.info(f"Found answer: {answer}")

        # Send answer
        centrala_client = CentralaClient(task_identifier=TASK_IDENTIFIER)
        centrala_client.send_answer(answer=answer)
        logging.info("Answer sent successfully")

    except Exception as e:
        logging.error(f"Task execution failed: {e}")
        raise

