import logging
import requests
from clients.openai_client import OpenAIClient
from clients.centrala_client import CentralaClient
from clients.llm_configs import ChatConfig

# System prompts for OpenAI interactions
EXTRACT_NAMES_CITIES_PROMPT = """Extract all person names and city names from the given text. 
Return them in a simple format:
NAMES: name1, name2, name3
CITIES: city1, city2, city3

Only extract actual names and places, ignore other words."""

NORMALIZE_NAME_PROMPT = """Convert the given Polish name to nominative case (mianownik) and remove Polish characters.
Return only the normalized name in uppercase, nothing else. Return only the first name if multiple names are provided.
Examples: Grześkowi Kowalskiemu -> GRZESIEK, Aleksandrowi Nowakowi -> ALEKSANDER, Barbary -> BARBARA, Pawłowi -> PAWEL, Małgorzatą -> MALGORZATA"""

NORMALIZE_CITY_PROMPT = """Convert the given Polish city name to remove Polish characters and return in uppercase.
Return only the normalized city name, nothing else.
Examples: Kraków -> KRAKOW, Łódź -> LODZ, Gdańsk -> GDANSK"""


class TaskSolver:
    """Solver for finding Barbara Zawadzka using people and places API endpoints."""

    def __init__(self):
        """Initialize the task solver with required clients."""
        self.logger = logging.getLogger("TaskSolver")
        self.openai_client = OpenAIClient()
        self.centrala_client = CentralaClient("loop")
        self.chat_config = ChatConfig(model="gpt-4.1-nano", temperature=0.1)

        # Track what we've already checked to avoid duplicates
        self.checked_people = set()
        self.checked_places = set()

        # Track original locations from Barbara's note
        self.original_barbara_locations = set()

        # Queues for processing
        self.people_queue = set()
        self.places_queue = set()

    def download_barbara_note(self) -> str:
        """Download Barbara's note from the provided URL."""
        url = "https://c3ntrala.ag3nts.org/dane/barbara.txt"
        self.logger.info(f"Downloading Barbara's note from: {url}")

        try:
            response = requests.get(url)
            response.raise_for_status()
            content = response.text
            self.logger.info(
                f"Successfully downloaded Barbara's note. Content length: {len(content)} characters"
            )
            self.logger.info(f"Note content: {content}")
            return content
        except requests.RequestException as e:
            self.logger.error(f"Failed to download Barbara's note: {e}")
            raise

    def extract_names_and_cities(self, text: str) -> tuple[list[str], list[str]]:
        """Extract person names and city names from text using OpenAI."""
        self.logger.info("Extracting names and cities from Barbara's note using OpenAI")

        self.chat_config.system_prompt = EXTRACT_NAMES_CITIES_PROMPT
        response = self.openai_client.send_message(text, self.chat_config)

        self.logger.info(f"OpenAI extraction response: {response}")

        names = []
        cities = []

        for line in response.split("\n"):
            line = line.strip()
            if line.startswith("NAMES:"):
                names_str = line[6:].strip()
                if names_str:
                    names = [name.strip() for name in names_str.split(",") if name.strip()]
            elif line.startswith("CITIES:"):
                cities_str = line[7:].strip()
                if cities_str:
                    cities = [city.strip() for city in cities_str.split(",") if city.strip()]

        self.logger.info(f"Extracted names: {names}")
        self.logger.info(f"Extracted cities: {cities}")

        return names, cities

    def normalize_name(self, name: str) -> str:
        """Normalize a Polish name to nominative case without Polish characters."""
        self.logger.info(f"Normalizing name: {name}")

        self.chat_config.system_prompt = NORMALIZE_NAME_PROMPT
        normalized = self.openai_client.send_message(name, self.chat_config).strip().upper()

        self.logger.info(f"Normalized name '{name}' to '{normalized}'")
        return normalized

    def normalize_city(self, city: str) -> str:
        """Normalize a Polish city name without Polish characters."""
        self.logger.info(f"Normalizing city: {city}")

        self.chat_config.system_prompt = NORMALIZE_CITY_PROMPT
        normalized = self.openai_client.send_message(city, self.chat_config).strip().upper()

        self.logger.info(f"Normalized city '{city}' to '{normalized}'")
        return normalized

    def query_person(self, name: str) -> list[str]:
        """Query the people endpoint for places where a person was seen."""
        if name in self.checked_people:
            self.logger.info(f"Person '{name}' already checked, skipping")
            return []

        self.logger.info(f"Querying people endpoint for: {name}")
        self.checked_people.add(name)

        try:
            response = self.centrala_client.query_people(name)

            # Handle different response formats
            places = []
            if "reply" in response and isinstance(response["reply"], list):
                places = response["reply"]
            elif "message" in response and isinstance(response["message"], str):
                # Check for restricted data or other special messages
                if "[**RESTRICTED DATA**]" in response["message"]:
                    self.logger.info(
                        f"RESTRICTED DATA found for person '{name}': {response['message']}"
                    )
                    return []
                # Parse space-separated string
                places_str = response["message"].strip()
                if places_str:
                    places = [place.strip() for place in places_str.split() if place.strip()]
            else:
                self.logger.warning(f"Unexpected response format for person '{name}': {response}")
                return []

            self.logger.info(f"Person '{name}' was seen in places: {places}")
            return places

        except Exception as e:
            self.logger.error(f"Error querying person '{name}': {e}")
            return []

    def query_place(self, place: str) -> list[str]:
        """Query the places endpoint for people seen in a place."""
        if place in self.checked_places:
            self.logger.info(f"Place '{place}' already checked, skipping")
            return []

        self.logger.info(f"Querying places endpoint for: {place}")
        self.checked_places.add(place)

        try:
            response = self.centrala_client.query_places(place)

            # Handle different response formats
            people = []
            if "reply" in response and isinstance(response["reply"], list):
                people = response["reply"]
            elif "message" in response and isinstance(response["message"], str):
                # Check for restricted data or other special messages
                if "[**RESTRICTED DATA**]" in response["message"]:
                    self.logger.info(
                        f"RESTRICTED DATA found for place '{place}': {response['message']}"
                    )
                    return []
                # Parse space-separated string
                people_str = response["message"].strip()
                if people_str:
                    people = [person.strip() for person in people_str.split() if person.strip()]
            else:
                self.logger.warning(f"Unexpected response format for place '{place}': {response}")
                return []

            self.logger.info(f"Place '{place}' had these people: {people}")

            # Check if Barbara is in this place
            if "BARBARA" in people:
                self.logger.info(f"FOUND BARBARA IN PLACE: {place}")
                # Check if this is a new location (not in original note)
                if place not in self.original_barbara_locations:
                    self.logger.info(f"This is a NEW location for Barbara: {place}")
                    return people  # Return the people list for further processing
                else:
                    self.logger.info(
                        f"This is a known location for Barbara from original note: {place}"
                    )

            return people

        except Exception as e:
            self.logger.error(f"Error querying place '{place}': {e}")
            return []

    def solve(self) -> str:
        """Main solving logic to find Barbara's current location."""
        self.logger.info("Starting Barbara search task")

        # Step 1: Download and parse Barbara's note
        note_content = self.download_barbara_note()
        names, cities = self.extract_names_and_cities(note_content)

        # Step 2: Normalize initial names and cities
        for name in names:
            normalized_name = self.normalize_name(name)
            self.people_queue.add(normalized_name)

        for city in cities:
            normalized_city = self.normalize_city(city)
            self.places_queue.add(normalized_city)
            # Track original Barbara locations
            self.original_barbara_locations.add(normalized_city)

        self.logger.info(f"Initial people queue: {self.people_queue}")
        self.logger.info(f"Initial places queue: {self.places_queue}")
        self.logger.info(f"Original Barbara locations: {self.original_barbara_locations}")

        # Step 3: Iterative search
        barbara_current_location = None
        iteration = 0

        while self.people_queue or self.places_queue:
            iteration += 1
            self.logger.info(f"--- Iteration {iteration} ---")

            # Process people queue
            if self.people_queue:
                person = self.people_queue.pop()
                places = self.query_person(person)

                # Add new places to queue
                for place in places:
                    if place not in self.checked_places:
                        self.places_queue.add(place)
                        self.logger.info(f"Added new place to queue: {place}")

            # Process places queue
            if self.places_queue:
                place = self.places_queue.pop()
                people = self.query_place(place)

                # Check if Barbara is in this place and it's new
                if "BARBARA" in people and place not in self.original_barbara_locations:
                    if not barbara_current_location:  # Only log the first time we find her
                        barbara_current_location = place
                        self.logger.info(
                            f"FOUND BARBARA'S CURRENT LOCATION: {barbara_current_location}"
                        )
                        self.logger.info(
                            "Continuing to process all remaining items to find secrets..."
                        )

                # Add new people to queue (normalize them first)
                for person in people:
                    # Handle Polish characters in names from API responses
                    try:
                        normalized_person = self.normalize_name(person)
                        if normalized_person not in self.checked_people:
                            self.people_queue.add(normalized_person)
                            self.logger.info(
                                f"Added new person to queue: {normalized_person} (from {person})"
                            )
                    except Exception as e:
                        self.logger.warning(f"Could not normalize person name '{person}': {e}")
                        # Add the original name if normalization fails
                        if person not in self.checked_people:
                            self.people_queue.add(person)
                            self.logger.info(f"Added original person name to queue: {person}")

            self.logger.info(
                f"End of iteration {iteration}. People queue: {len(self.people_queue)}, Places queue: {len(self.places_queue)}"
            )

            # Safety check to avoid infinite loops
            if iteration > 200:
                self.logger.warning("Reached maximum iterations (200), stopping search")
                break

        self.logger.info("Finished processing all queues. Search complete!")

        if barbara_current_location:
            self.logger.info(
                f"Task completed successfully. Barbara's current location: {barbara_current_location}"
            )
            return barbara_current_location
        else:
            self.logger.warning("Could not find Barbara's current location")
            return None


def main():
    """Main function to run the Barbara search task."""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger("main")
    logger.info("Starting Barbara search task (S03E04)")

    try:
        # Initialize task solver
        solver = TaskSolver()

        # Solve the task
        barbara_location = solver.solve()

        if barbara_location:
            # Send the answer to Centrala
            logger.info(f"Sending answer to Centrala: {barbara_location}")
            solver.centrala_client.send_answer(barbara_location)
            logger.info("Task completed successfully!")
        else:
            logger.error("Could not find Barbara's location")

    except Exception as e:
        logger.error(f"Task failed with error: {e}")
        raise
