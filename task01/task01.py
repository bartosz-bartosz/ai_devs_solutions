import re
import requests
import logging
import os
from openai import OpenAI
from bs4 import BeautifulSoup

# Konfiguracja loggera
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("robot_login")


class WebClient:
    """Klasa obsługująca operacje HTTP i parsowanie danych."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.logger = logging.getLogger("robot_login.WebClient")

    def fetch_login_page(self) -> str:
        """Pobiera stronę logowania."""
        self.logger.info(f"Pobieranie strony logowania z {self.base_url}")
        response = requests.get(self.base_url)
        response.raise_for_status()
        return response.text

    def extract_question(self, html_content: str) -> str:
        """Wyciąga pytanie z elementu human-question."""
        self.logger.info("Ekstrakcja pytania z HTML")
        soup = BeautifulSoup(html_content, "html.parser")
        question_element = soup.find(id="human-question")

        if not question_element:
            self.logger.error("Nie znaleziono elementu z pytaniem")
            raise ValueError("Nie znaleziono elementu z pytaniem")

        # Wyciągamy samo pytanie, usuwając "Question:" i zbędne spacje
        question_text = question_element.text.strip()
        # Usuwamy "Question:" jeśli występuje
        if "Question:" in question_text:
            question_text = question_text.replace("Question:", "").strip()

        self.logger.info(f"Znalezione pytanie: {question_text}")
        return question_text

    def login(self, username: str, password: str, answer: str) -> requests.Response:
        """Wykonuje logowanie do serwisu."""
        self.logger.info(f"Wykonywanie logowania dla użytkownika {username}")
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        data = {"username": username, "password": password, "answer": answer}

        response = requests.post(self.base_url, headers=headers, data=data)
        self.logger.info(f"Status odpowiedzi: {response.status_code}")
        return response


class OpenAIClient:
    """Klasa obsługująca komunikację z API OpenAI wykorzystująca oficjalną bibliotekę."""

    def __init__(self, api_key: str, model: str = "gpt-4.1-nano"):
        self.model = model
        self.client = OpenAI(api_key=api_key)
        self.logger = logging.getLogger("robot_login.OpenAIClient")

    def get_year_answer(self, question: str) -> str:
        """
        Pobiera odpowiedź na pytanie z modelu LLM korzystając z oficjalnej biblioteki OpenAI.
        Prompt skonstruowany jest tak, aby odpowiedź zawierała tylko rok.
        """
        self.logger.info(f"Wysyłanie pytania do modelu {self.model}")

        prompt = """
        Odpowiedz wyłącznie cyframi reprezentującymi rok, bez żadnego dodatkowego tekstu, 
        zdań czy wyjaśnień. Twoja odpowiedź musi zawierać tylko 4 cyfry roku.
        
        Na przykład:
        Pytanie: Kiedy wybuchła II wojna światowa?
        Odpowiedź: 1939
        
        Pytanie: W którym roku powstał pierwszy iPhone?
        Odpowiedź: 2007
        
        Oto pytanie do odpowiedzi (podaj tylko rok):
        """

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": question},
                ],
                temperature=0.1,
            )

            # Wyciąganie odpowiedzi
            answer = response.choices[0].message.content.strip()

            # Upewniamy się, że odpowiedź to sam rok (4 cyfry)
            if not answer.isdigit():
                self.logger.warning(f"Otrzymana odpowiedź nie jest liczbą: {answer}")
                # Próba wyciągnięcia roku za pomocą regex
                year_match = re.search(r"\b\d{4}\b", answer)
                if year_match:
                    answer = year_match.group(0)
                    self.logger.info(f"Wyekstrahowano rok z odpowiedzi: {answer}")
                else:
                    self.logger.error("Nie udało się wyekstrahować roku z odpowiedzi")
                    raise ValueError("Odpowiedź LLM nie zawiera roku")

            self.logger.info(f"Otrzymano odpowiedź: {answer}")
            return answer

        except Exception as e:
            self.logger.error(f"Błąd komunikacji z API OpenAI: {e}")
            raise


def main():
    # Konfiguracja
    url = "https://xyz.ag3nts.org/"
    username = "tester"
    password = "574e112a"

    # Pobierz klucz API z zmiennej środowiskowej
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("Błąd: Ustaw zmienną środowiskową OPENAI_API_KEY")
        return

    try:
        # Inicjalizacja klientów
        web_client = WebClient(url)
        openai_client = OpenAIClient(api_key)

        # Krok 1: Pobierz stronę logowania
        html_content = web_client.fetch_login_page()

        # Krok 2: Wyciągnij pytanie
        question = web_client.extract_question(html_content)

        # Krok 3: Uzyskaj odpowiedź od modelu LLM
        answer = openai_client.get_year_answer(question)

        # Krok 4: Wykonaj logowanie
        response = web_client.login(username, password, answer)

        # Wypisz część odpowiedzi
        logger.info(f"Treść odpowiedzi: {response.text}...")

    except Exception as e:
        logger.error(f"Wystąpił błąd: {e}")

