Proces weryfikacji możesz przećwiczyć pod poniższym adresem. To API firmy XYZ. Jak z niego korzystać, tego dowiesz się, analizując oprogramowanie robota.

https://xyz.ag3nts.org/verify 

Co należy zrobić w zadaniu?

Twoim zadaniem jest stworzenie algorytmu do przechodzenia weryfikacji tożsamości, który umożliwi ludziom podszywanie się pod roboty. Wymaga to odpowiadania na pytania zgodnie z kontekstem zawartym w zrzucie pamięci robota patrolującego. Zwracaj uwagę na próby zmylenia w postaci nieprawdziwych informacji.

Kroki do wykonania:

1. Zapoznaj się ze zrzutem pamięci robota  

Znajdziesz go pod adresem: https://xyz.ag3nts.org/files/0_13_4b.txt. Skup się na opisie procesu weryfikacji człowieka/robota. Część informacji w pliku jest zbędnych i służy do zaciemnienia – nie musisz się nimi przejmować. 

2. Zrozum proces weryfikacji  

Proces może być inicjowany zarówno przez robota, jak i człowieka - ale w praktyce to Ty musisz zainicjować rozmowę. Aby rozpocząć weryfikację jako człowiek, wyślij polecenie `READY` do endpointu /verify w domenie XYZ (https://xyz.ag3nts.org/verify).

3. Przetwarzanie odpowiedzi robota  

Robot odpowie pytaniem, na które musisz odpowiedzieć. Ważne jest, abyś korzystał z wiedzy zawartej w zrzucie pamięci robota. Na pytania z fałszywymi informacjami, jak np. "stolica Polski", odpowiadaj zgodnie z tym, co znajduje się w zrzucie (np. "Kraków" zamiast "Warszawa"). Dla pozostałych pytań udzielaj prawdziwych odpowiedzi.

4. Identyfikator wiadomości  

Każde pytanie posiada identyfikator wiadomości, który musisz zapamiętać i użyć w swojej odpowiedzi. Przykład takiej komunikacji znajdziesz w zrzucie pamięci.

5. Zdobycie flagi  

Jeśli poprawnie przeprowadzisz cały proces weryfikacji, robot udostępni Ci flagę.

Wskazówki:





Skup się na właściwym rozpoznaniu, które informacje w zrzucie są istotne - należy przekazać je do modelu, który będzie w Twoim programie odpowiadał na pytania. Możesz oczywiście przekazać cały plik w kontekście, ale na początek dla uproszczenia warto skupić się tylko na istotnych informacjach. 



Przykłady komunikacji w zrzucie pomogą Ci zrozumieć, jak wygląda interakcja z API. Możesz też skorzystać z dokumentacji Swagger - link poniżej. 



Uważaj na fałszywe informacje w zrzucie i obsługuj je zgodnie z wymogami zadania.



Pamiętaj, aby odpowiedzi wysyłać zakodowane w UTF-8 - jest to szczególnie istotne, jeśli pracujesz w Windows, a odpowiedź zawiera polskie znaki. Odpowiedzi mają być po angielsku.



Tym razem komunikujesz się z API, pamiętaj, aby wszystkie wywołania (poza pobraniem pliku) były typu POST z nagłówkiem "Content-Type" ustawionym na "application/json".



Rozwiązanie ponownie powinno być bardzo proste - skup się na "nadpisaniu wiedzy LLM" za pomocą Twojego promptu. To główny cel tego zadania. 

Dokumentacja Swagger:

https://xyz.ag3nts.org/swagger-xyz/?spec=S01E02-867vz6wkfs.json 
