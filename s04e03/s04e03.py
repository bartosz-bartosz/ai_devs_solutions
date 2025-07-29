import logging
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from urllib.parse import urljoin, urlparse
from clients.centrala_client import CentralaClient
from clients.openai_client import OpenAIClient
from clients.llm_configs import ChatConfig


class TaskSolver:
    """
    Solver for s04e03 - Universal web information search mechanism.
    Creates an intelligent web scrapping agent that uses LLM guidance to navigate
    websites and find specific information.
    """

    def __init__(self):
        """Initialize the task solver with necessary clients."""
        self.logger = logging.getLogger("TaskSolver")
        self.openai_client = OpenAIClient()
        self.centrala_client = CentralaClient("softo")
        self.visited_urls = set()
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        )

    def fetch_questions(self) -> Dict[str, str]:
        """Fetch questions from Centrala API."""
        questions_url = (
            f"https://c3ntrala.ag3nts.org/data/{self.centrala_client.api_key}/softo.json"
        )
        response = requests.get(questions_url)
        response.raise_for_status()
        questions = response.json()
        self.logger.info(f"Fetched questions: {list(questions.keys())}")
        return questions

    def html_to_markdown(self, html_content: str) -> str:
        """Convert HTML content to markdown-like text."""
        soup = BeautifulSoup(html_content, "html.parser")

        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Get text content
        text = soup.get_text()

        # Clean up whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text = " ".join(chunk for chunk in chunks if chunk)

        # Extract links
        links = []
        for a in soup.find_all("a", href=True):
            link_text = a.get_text().strip()
            link_url = a["href"]
            if link_text and link_url:
                links.append(f"[{link_text}]({link_url})")

        # Combine text and links
        if links:
            text += "\n\nLinks found:\n" + "\n".join(links)

        return text

    def fetch_page_content(self, url: str) -> Optional[str]:
        """Fetch and convert HTML page to markdown-like text."""
        try:
            self.logger.info(f"Fetching page: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()

            # Convert HTML to markdown-like text
            markdown_content = self.html_to_markdown(response.text)
            return markdown_content.strip()

        except Exception as e:
            self.logger.error(f"Error fetching {url}: {e}")
            return None

    def extract_links(self, html_content: str, base_url: str) -> List[str]:
        """Extract all links from HTML content."""
        soup = BeautifulSoup(html_content, "html.parser")
        links = []

        for a in soup.find_all("a", href=True):
            link = a["href"]
            if link.startswith("http"):
                links.append(link)
            elif link.startswith("/"):
                links.append(urljoin(base_url, link))
            elif link.startswith("#"):
                continue  # Skip anchor links
            else:
                links.append(urljoin(base_url, link))

        # Filter to keep only relevant links (same domain or subdomains)
        base_domain = urlparse(base_url).netloc
        filtered_links = []
        for link in links:
            link_domain = urlparse(link).netloc
            if base_domain in link_domain or link_domain in base_domain:
                filtered_links.append(link)

        return list(set(filtered_links))  # Remove duplicates

    def can_answer_question(self, content: str, question: str) -> tuple[bool, Optional[str]]:
        """Check if the current page content can answer the question."""
        config = ChatConfig(model="gpt-4o-mini", temperature=0.0)

        prompt = f"""
        Analyze the following webpage content and determine if it contains the answer to this specific question.

        QUESTION: {question}

        WEBPAGE CONTENT:
        {content}

        Instructions:
        1. If you can find a DIRECT and SPECIFIC answer to the question in the content, respond with:
           ANSWER_FOUND: [the exact, concise answer]
        
        2. If you cannot find the answer, respond with:
           ANSWER_NOT_FOUND
        
        Be very precise - only return ANSWER_FOUND if you can provide the exact information requested.
        The answer should be as concise as possible (e.g., just an email address, phone number, etc.).
        Do NOT include phrases like "The email is:" - just provide the raw information.
        """

        response = self.openai_client.send_message(prompt, config)

        if response.startswith("ANSWER_FOUND:"):
            answer = response.replace("ANSWER_FOUND:", "").strip()
            return True, answer

        return False, None

    def choose_best_link(
        self, content: str, question: str, available_links: List[str]
    ) -> Optional[str]:
        """Use LLM to choose the most promising link for finding the answer."""
        if not available_links:
            return None

        config = ChatConfig(model="gpt-4o-mini", temperature=0.0)

        links_text = "\n".join([f"{i + 1}. {link}" for i, link in enumerate(available_links)])

        prompt = f"""You are an expert web navigator. Your task is to analyze a question and choose the most promising link to find the answer.

QUESTION TO ANSWER: {question}

CURRENT PAGE CONTENT:
{content}

AVAILABLE LINKS TO EXPLORE:
{links_text}

INSTRUCTIONS:
1. Analyze the question to understand what specific information is being requested
2. Look at the current page content to understand the context and site structure
3. Examine each available link and consider:
   - Does the URL path/name suggest it contains relevant information?
   - Does any link text or context on the current page indicate it leads to the answer?
   - Which section of the website would logically contain this type of information?

4. Choose the ONE link most likely to contain the direct answer to the question
5. Respond with ONLY the complete URL of your chosen link
6. If no links seem relevant at all, respond with: NONE

Think step by step but respond with only the URL or NONE."""

        response = self.openai_client.send_message(prompt, config).strip()

        if response == "NONE" or response not in available_links:
            return None

        return response

    def search_for_answer(
        self, question: str, start_url: str = "https://softo.ag3nts.org", max_depth: int = 5
    ) -> Optional[str]:
        """Search for answer to a specific question using intelligent navigation."""
        self.visited_urls.clear()  # Reset for each question
        current_url = start_url
        depth = 0

        self.logger.info(f"Searching for answer to: {question}")

        while depth < max_depth and current_url and current_url not in self.visited_urls:
            self.visited_urls.add(current_url)

            # Fetch page content
            content = self.fetch_page_content(current_url)
            if not content:
                self.logger.warning(f"Could not fetch content from {current_url}")
                break

            # Check if current page has the answer
            has_answer, answer = self.can_answer_question(content, question)
            if has_answer and answer:
                self.logger.info(f"Found answer: {answer}")
                return answer

            # If no answer found, get available links and choose the best one
            # We need to fetch the raw HTML to extract links properly
            try:
                response = self.session.get(current_url, timeout=30)
                if response.status_code == 200:
                    available_links = self.extract_links(response.text, current_url)
                    # Filter out already visited links
                    available_links = [
                        link for link in available_links if link not in self.visited_urls
                    ]

                    if not available_links:
                        self.logger.info("No more links to explore")
                        break

                    # Choose the best link to follow
                    next_url = self.choose_best_link(content, question, available_links)
                    if not next_url:
                        self.logger.info("LLM couldn't choose a promising link")
                        break

                    self.logger.info(f"Following link: {next_url}")
                    current_url = next_url
                    depth += 1
                else:
                    break
            except Exception as e:
                self.logger.error(f"Error extracting links from {current_url}: {e}")
                break

        self.logger.warning(f"Could not find answer for question: {question}")
        return None

    def solve(self) -> Dict[str, str]:
        """
        Main solving logic for the task.

        Returns:
            Dictionary with answers for each question
        """
        # Fetch questions from Centrala
        questions = self.fetch_questions()
        answers = {}

        # Process each question
        for question_id, question_text in questions.items():
            self.logger.info(f"Processing question {question_id}: {question_text}")

            answer = self.search_for_answer(question_text)
            if answer:
                answers[question_id] = answer
                self.logger.info(f"Answer for {question_id}: {answer}")
            else:
                self.logger.error(f"Could not find answer for question {question_id}")
                answers[question_id] = "Answer not found"

        return answers


def main():
    """Main function to execute the task."""
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger("S04E03")
    logger.info("Starting S04E03 - Universal web search mechanism")

    try:
        # Initialize task solver
        solver = TaskSolver()

        # Solve the task
        answer = solver.solve()

        # Send answer to Centrala
        logger.info(f"Sending answer to Centrala: {answer}")
        solver.centrala_client.send_answer(answer)

        logger.info("Task completed successfully!")

    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise


if __name__ == "__main__":
    main()

