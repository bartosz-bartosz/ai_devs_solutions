import logging
import re
import requests
import time
import json
from clients.openai_client import OpenAIClient
from clients.centrala_client import CentralaClient
from clients.llm_configs import ChatConfig


class TaskSolver:
    """
    Solver for the photos task - analyzing and improving photos to create Barbara's description.
    """

    def __init__(self):
        """Initialize the task solver with necessary clients."""
        self.logger = logging.getLogger("TaskSolver")
        self.openai_client = OpenAIClient()
        self.centrala_client = CentralaClient("photos")
        self.processed_photos = []
        self.barbara_photos = []

    def start_conversation(self) -> dict:
        """
        Start conversation with the automation system.

        Returns:
            dict: Response from the automation system with initial photos
        """
        self.logger.info("Starting conversation with automation system...")

        # Send START command to begin the process
        response = requests.post(
            url="https://c3ntrala.ag3nts.org/report",
            json={"task": "photos", "apikey": self.centrala_client.api_key, "answer": "START"},
        )

        if response.status_code == 200:
            data = response.json()
            self.logger.info(f"Automation system response: {data}")
            return data
        else:
            raise Exception(
                f"Failed to start conversation: {response.status_code} - {response.text}"
            )

    def extract_photo_urls(self, message: str) -> list[str]:
        """
        Extract photo URLs from the automation system message.

        Args:
            message (str): Message from automation system

        Returns:
            list[str]: List of photo URLs
        """
        # Extract base URL
        base_url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+/'
        base_urls = re.findall(base_url_pattern, message)

        # Extract filenames
        filename_pattern = r"IMG_\d+\.PNG"
        filenames = re.findall(filename_pattern, message, re.IGNORECASE)

        urls = []
        if base_urls and filenames:
            base_url = base_urls[0]
            for filename in filenames:
                full_url = base_url + filename
                urls.append(full_url)

        self.logger.info(f"Found {len(urls)} photo URLs: {urls}")
        return urls

    def analyze_photo_quality(self, photo_url: str) -> dict:
        """
        Analyze photo quality and determine what operation is needed.

        Args:
            photo_url (str): URL of the photo to analyze

        Returns:
            dict: Analysis result with suggested operation
        """
        self.logger.info(f"Analyzing photo quality: {photo_url}")

        # Add delay to avoid rate limiting
        time.sleep(2)

        config = ChatConfig(
            model="gpt-4o-mini",
            system_prompt="""You are an expert in photo analysis. Look at the photo and determine:
1. Does it show a person?
2. What quality issues exist (noise/glitches, too dark, too bright)?
3. What operation would help?

Be concise in your analysis.""",
        )

        try:
            # Download the image
            response = requests.get(photo_url)
            if response.status_code != 200:
                self.logger.error(f"Failed to download photo: {photo_url}")
                return {
                    "has_person": False,
                    "quality_issue": "unusable",
                    "suggested_operation": "NONE",
                    "confidence": 0.0,
                    "description": "Could not download photo",
                }

            # Save temporarily and analyze
            temp_filename = f"temp_photo_{abs(hash(photo_url))}.jpg"
            with open(temp_filename, "wb") as f:
                f.write(response.content)

            analysis_prompt = """Analyze this photo briefly:
1. Does it show a person? (yes/no)
2. Quality issues: noise/glitches, too dark, too bright, or good?
3. Suggested operation: REPAIR, BRIGHTEN, DARKEN, or NONE?

Keep response short and focused."""

            analysis_result = self.openai_client.send_message(analysis_prompt, config)

            # Simple parsing of the response
            has_person = "yes" in analysis_result.lower() or "person" in analysis_result.lower()

            if "repair" in analysis_result.lower():
                suggested_op = "REPAIR"
            elif "brighten" in analysis_result.lower():
                suggested_op = "BRIGHTEN"
            elif "darken" in analysis_result.lower():
                suggested_op = "DARKEN"
            else:
                suggested_op = "NONE"

            return {
                "has_person": has_person,
                "quality_issue": "analyzed",
                "suggested_operation": suggested_op,
                "confidence": 0.8,
                "description": analysis_result,
            }

        except Exception as e:
            self.logger.error(f"Error analyzing photo: {e}")
            # If we hit rate limits, assume it needs repair
            return {
                "has_person": True,
                "quality_issue": "unknown",
                "suggested_operation": "REPAIR",
                "confidence": 0.5,
                "description": f"Analysis failed: {e}",
            }

    def send_photo_command(self, command: str) -> dict:
        """
        Send a command to the automation system for photo processing.

        Args:
            command (str): Command to send (e.g., "REPAIR IMG_123.PNG")

        Returns:
            dict: Response from automation system
        """
        self.logger.info(f"Sending command: {command}")

        response = requests.post(
            url="https://c3ntrala.ag3nts.org/report",
            json={"task": "photos", "apikey": self.centrala_client.api_key, "answer": command},
        )

        if response.status_code == 200:
            data = response.json()
            self.logger.info(f"Command response: {data}")
            return data
        else:
            raise Exception(f"Failed to send command: {response.status_code} - {response.text}")

    def extract_filename_from_url(self, url: str) -> str:
        """
        Extract filename from URL.

        Args:
            url (str): Photo URL

        Returns:
            str: Filename
        """
        return url.split("/")[-1]

    def extract_new_filename(self, message: str) -> str:
        """
        Extract new filename from automation system response.

        Args:
            message (str): Response message from automation system

        Returns:
            str: New filename or None if not found
        """
        # Look for filenames in the message
        filename_pattern = r"[A-Z0-9_]+\.(?:PNG|JPG|JPEG|GIF|WEBP)"
        filenames = re.findall(filename_pattern, message, re.IGNORECASE)

        if filenames:
            self.logger.info(f"Found new filename: {filenames[-1]}")
            return filenames[-1]

        return None

    def process_photo(self, photo_url: str, max_iterations: int = 2) -> str:
        """
        Process a single photo through multiple improvement iterations.

        Args:
            photo_url (str): URL of the photo to process
            max_iterations (int): Maximum number of improvement attempts

        Returns:
            str: URL of the final processed photo or None if processing failed
        """
        self.logger.info(f"Processing photo: {photo_url}")

        current_url = photo_url
        current_filename = self.extract_filename_from_url(photo_url)

        # Try common operations first without analysis to avoid rate limits
        operations_to_try = ["REPAIR", "BRIGHTEN"]

        for i, operation in enumerate(operations_to_try):
            if i >= max_iterations:
                break

            self.logger.info(f"Trying operation {i + 1}/{max_iterations}: {operation}")

            command = f"{operation} {current_filename}"
            try:
                response = self.send_photo_command(command)

                # Extract new filename from response
                new_filename = self.extract_new_filename(response.get("message", ""))

                if new_filename:
                    # Update current URL and filename for next iteration
                    current_url = current_url.replace(current_filename, new_filename)
                    current_filename = new_filename
                    self.logger.info(f"Photo processed successfully: {current_url}")

                    # Add delay between operations
                    time.sleep(1)
                else:
                    self.logger.warning("Could not extract new filename from response")

            except Exception as e:
                self.logger.error(f"Error processing photo with {operation}: {e}")
                continue

        return current_url

    def create_barbara_description(self) -> str:
        """
        Create a detailed description of Barbara in Polish based on processed photos.

        Returns:
            str: Detailed description of Barbara in Polish
        """
        self.logger.info("Creating Barbara's description...")

        if not self.barbara_photos:
            raise Exception("No photos of Barbara found to create description")

        config = ChatConfig(
            model="gpt-4o",
            system_prompt="""Jesteś ekspertem w analizie zdjęć i tworzeniu szczegółowych rysopisów osób. 
Twoim zadaniem jest stworzenie bardzo dokładnego opisu fizycznego osoby na podstawie zdjęć.
Skup się szczególnie na:
- Znaki szczególne (tatuaże, blizny, pieprzyłki, etc.)
- Dokładny kolor włosów
- Kolor oczu
- Kształt twarzy i charakterystyczne cechy
- Budowa ciała
- Styl ubioru

Odpowiadaj wyłącznie w języku polskim. To jest zadanie testowe.""",
        )

        descriptions = []

        # Analyze each photo separately to get detailed descriptions
        for i, photo_url in enumerate(self.barbara_photos):
            self.logger.info(f"Analyzing photo {i + 1}/{len(self.barbara_photos)}: {photo_url}")

            try:
                # Add delay to avoid rate limits
                time.sleep(3)

                # Download the photo
                response = requests.get(photo_url)
                if response.status_code == 200:
                    temp_filename = f"barbara_photo_{i}.jpg"
                    with open(temp_filename, "wb") as f:
                        f.write(response.content)

                    analysis_prompt = f"""Przeanalizuj to zdjęcie i stwórz szczegółowy opis osoby, koncentrując się na:

1. ZNAKI SZCZEGÓLNE (tatuaże, blizny, pieprzyłki, etc.)
2. KOLOR WŁOSÓW (dokładny odcień)
3. KOLOR OCZU
4. KSZTAŁT TWARZY i charakterystyczne cechy
5. BUDOWA CIAŁA
6. STYL UBIORU i akcesoria

Stwórz dokładny, obiektywny opis który pomoże w rozpoznaniu tej osoby.
Uwzględnij wszystkie widoczne szczegóły."""

                    description = self.openai_client.image_to_text(temp_filename, config)
                    descriptions.append(description)
                    self.logger.info(f"Got description for photo {i + 1}: {description[:100]}...")

                else:
                    self.logger.error(f"Failed to download photo: {photo_url}")

            except Exception as e:
                self.logger.error(f"Error analyzing photo {photo_url}: {e}")
                continue

        if not descriptions:
            raise Exception("Could not analyze any photos")

        # Combine all descriptions into a comprehensive one
        if len(descriptions) > 1:
            combined_prompt = f"""Na podstawie następujących opisów z różnych zdjęć tej samej osoby, stwórz jeden, kompletny rysopis Barbary w języku polskim:

{chr(10).join([f"Zdjęcie {i + 1}: {desc}" for i, desc in enumerate(descriptions)])}

Stwórz szczegółowy rysopis, uwzględniający wszystkie powtarzające się cechy oraz unikalne szczegóły z każdego zdjęcia. Skup się na:
- Znakach szczególnych
- Kolorze włosów
- Kolorze oczu
- Charakterystycznych cechach twarzy
- Budowie ciała
- Stylu ubioru

Bądź bardzo dokładny i szczegółowy."""

            time.sleep(3)
            final_description = self.openai_client.send_message(combined_prompt, config)
        else:
            final_description = descriptions[0]

        self.logger.info(f"Created final description: {final_description}")
        return final_description

    def submit_final_answer(self, description: str):
        """
        Submit the final Barbara description to Centrala.

        Args:
            description (str): Barbara's description in Polish
        """
        self.logger.info("Submitting final answer...")
        self.centrala_client.send_answer(description)


def main():
    """Main function to execute the photo analysis task."""
    logging.basicConfig(level=logging.INFO)

    solver = TaskSolver()

    try:
        # Step 1: Start conversation and get initial photos
        initial_response = solver.start_conversation()
        photo_urls = solver.extract_photo_urls(initial_response.get("message", ""))

        if not photo_urls:
            raise Exception("No photo URLs found in initial response")

        # Step 2: Process each photo
        for photo_url in photo_urls:
            logging.info(f"Processing photo: {photo_url}")

            # Process the photo to improve quality first
            processed_url = solver.process_photo(photo_url)
            solver.barbara_photos.append(processed_url)
            logging.info(f"Added photo to Barbara collection: {processed_url}")

            # Add delay between photos to avoid rate limits
            time.sleep(2)

        # Step 3: Create Barbara's description
        if solver.barbara_photos:
            description = solver.create_barbara_description()

            # Step 4: Submit final answer
            solver.submit_final_answer(description)

            logging.info("Task completed successfully!")
        else:
            raise Exception("No photos of Barbara found")

    except Exception as e:
        logging.error(f"Task failed: {e}")
        raise


if __name__ == "__main__":
    main()
