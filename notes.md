Pracować szybko, nie zatrzymywać się przy jednem problemie na dłużej niż to konieczne, potem będzie czas na poprawki
 - [x] Zrobić reposytorium github i projekt Overleaf
 - [x] Zrobić przegląd artykułów na temat
 - [ ] Przygotować konspekt, cele i aspekty 
 - [x] Przerobić dane, żeby zorientować się co do ich jakości i tego co zawierają
 - [x] Skontaktować się z Panią Dyrektor i byłym promotorem
 - [ ] Wypełnić formularz WZI od nowa





Podsumowanie:

1. Dane
   1. Populacyjne
      1. Miejsce zamieszkania (ludność De Jure) <br/> Dane przestrzenne o gęstości/rozmieszczeniu populacji dla 
         wszystkich miast 
         europejskich są szeroko dostępne. Najprzystępniejszą formą są dane z badania Census, które zapisane są dla 
         całego obszaru UE na poziomie granuralności siatki 1 km x 1 km. <br/> Problemem okazują się dane z 
         Australii. Tamtejszy odpowiednik Urzędu Statystycznego dzieli obszary w niestandardowy sposób utrudniający 
         analizę, dodatkowo sama możliwość eksportu tych danych jest mocno ograniczona. Problem ten ma przełożenie 
         na wszystkie inne przestrzenne dane populacyjne dotyczące Australii.
      2. Miejsce zatrudnienia/populacja dzienna/populacja w miejscu pracy (ludność De Facto) <br/> O ile ten typ danych nie znajdował się 
         początkowo w obszarze moich poszukiwań, to może on jednak wykazywać wyższą rzeczywistą użyteczność w analizie dostępności transportu miejskiego przy 
         analizie uwzględniającej liczbę zatrudnionych. Dane takie dostępne są często wraz z poprzednim typem danych,
         jednak dla Francji i Niemiec nie zostały uwzględnione w głównym spisie powszechnym, ale dostępne są do 
         pobrania w podobnej formie z innych źródeł. Status dostępności danych dotyczących Australii taki sam jak 
         wyżej.
      3. Dokładana lokalizacja miejsca pracy <br/> Dane te różnią się od poprzednich tym, że określają dokąd ludzie 
         udają się do pracy, a nie ile osób na danym obszarze ma pracę. Dane tego typu pozwoliłyby mi uwzględnić 
         potencjalne dzienne przepływy ludności, co znacząco podniosłoby trafność analiz, jednakże ich dostępność 
         jest bardzo mocno ograniczona:
         - Dublin - zdecydowanie najlepsza sytuacja, gdzie dostępne są dane o lokalizacji zatrudnienia w siatce 1 km 
           x 1km.
         - Paryż - pomimo istnienia danych takick, jak w przypadku Dublina, nie są one publicznie dostępne (bądź nie 
           udało mi się ich znaleźć, pomimo intesywnych poszukiwań), jednakże odnalazłem dane określające strefy o 
           wysokim zatrudnieniu, które pomimo trudności z eksportem ich są możliwe do zescrappowania.
         - Warszawa - nie są publicznie dostępne dane w stylu Dublina, czy nawet Paryża, jedynie udało mi się 
           znaleźć dane określające liczbę ofert pracy w podziale na dzielnice, co stanowi punkt wyjścia. O ile się 
           orientuję, to istnieje jeszcze możliwość zamówienia indywidualnej analizy poprzez GUS, ale zgłębiałem w 
           pełni tego tematu.
         - Dla pozostałych miast, dla których szukałem danych tj. Lublin, Adelaide, Berlin, Brisbane, 
           Canberra, Helsinki, Kuopio, Luxembourg, Melbourne, Rzym, Turku, Sydney, Winnipeg; nie udało mi się 
           znaleźć tego typu danych. 

   2. Dotyczące komunikacji miejskiej
      1. Polska <br/> Udało mi się znaleźć dane dotyczące wszystkich interesujących mnie przewoźników (ZTM Warszawa, 
         Warszawska Kolej Dojazdowa, Koleje Mazowieckie, PolRegio, ZTM Lublin), 
         udostępnianie bezpośrednio przez nich i skatalogowane na stronie [dane.gov.pl](https://dane.gov.pl/pl/dataset/1739,krajowy-punkt-dostepowy-kpd-multimodalne-usugi-informacji-o-podrozach/resource/327976/table?page=1&per_page=20&q=warszaw&sort=).
      2. Zbiór 25-cities <br/> 

--------------------------------------------------------------------------------
I. Cele Pracy Magisterskiej (Cele)
Głównym celem pracy jest opracowanie i zastosowanie holistycznych ram oceny dostępności transportu zbiorowego (TZ), które wykraczają poza tradycyjne miary bazujące wyłącznie na podaży (ofercie przewozowej), w celu przeprowadzenia komparatywnej analizy trzech zróżnicowanych aglomeracji: Paryża, Dublina i Warszawy.
Cel ten zostanie osiągnięty poprzez realizację następujących szczegółowych celów:
1. Rozszerzenie Metodologiczne Analizy Dostępności (Paryż): Rozbudowanie wyników projektu zaliczeniowego [1] o zaawansowane miary dostępności, w tym modele grawitacyjne i analizę topologiczną L-space/P-space [2].
2. Integracja Perspektywy Popytu i Podaży (Modele Grawitacyjne): Kwantyfikacja potencjału dostępu do kluczowych celów (np. miejsc pracy, POI) z wykorzystaniem modelu grawitacyjnego, najlepiej dwustronnie ograniczonego (doubly constrained) [3-5], który uwzględnia zarówno popyt (ludność), jak i podaż (pojemność celów) [5, 6].
3. Wzbogacenie Behawioralne Impedancji (Whole Travel Chain - WTC): Uwzględnienie pełnego kosztu podróży z perspektywy użytkownika, włączając tzw. pierwszą i ostatnią milę (first/last mile), oraz czasy oczekiwania i transferów, w celu uzyskania bardziej realistycznej miary impedancji (c_ij) [7-9].
4. Weryfikacja Wymiaru Sprawiedliwości Społecznej (Mapowanie Społeczne): Przeprowadzenie analizy równości dostępu do możliwości, poprzez segmentację modelu grawitacyjnego i kalibrację współczynnika zaniku (
beta) w oparciu o różnice w zamożności (dochody) poszczególnych stref [10, 11].
5. Analiza Komparatywna i Zarządzanie Niespójnością Danych: Porównanie wyników dostępności uzyskanych za pomocą tej samej holistycznej metodologii dla trzech miast o różnym charakterze (metropolia globalna - Paryż, metropolia o dobrych danych - Dublin, miasto lokalne - Warszawa), przy jednoczesnym uwzględnieniu faktu, że dane pochodzą z różnych okresów czasowych, co jest kluczowym problemem do zaadresowania w dyskusji i metodologii [12].
--------------------------------------------------------------------------------
II. Konspekt Pracy Magisterskiej (Konspekt)
Wprowadzenie
1. Wstęp: Definicja dostępności obszarowej i jej znaczenie w planowaniu zrównoważonego transportu [13].
2. Kontekst Badawczy: Krótki przegląd istniejących miar dostępności (np. kumulatywne możliwości, modele potencjalne/grawitacyjne) [14, 15].
3. Ograniczenia Projektu Wstępnego: Krytyka wskaźnika użytego w projekcie dla Paryża (skoncentrowanie na podaży/ofercie) i uzasadnienie potrzeby przejścia na model grawitacyjny i perspektywę behawioralną [16-18].
4. Cele i Pytania Badawcze: Jasne sformułowanie celów pracy (patrz sekcja I) oraz hipotez badawczych.
5. Struktura Pracy.
Rozdział 1: Przegląd Literatury i Podstawy Metodologiczne
1. Teoretyczne Ramy Dostępności: Cztery komponenty dostępności: transportowy, przestrzenny, czasowy, indywidualny [19, 20].
2. Topologiczna Analiza Sieci (L-space i P-space): Definicja, różnice i znaczenie dualizmu L-space/P-space w diagnozowaniu problemów infrastrukturalnych vs. operacyjnych [21-23].
3. Modele Grawitacyjne w Ocenie Dostępności: Podstawy Modelu Hansena [24, 25], rola atrakcyjności celów (T_attr - POI, zatrudnienie) i impedancji (f(c_ij)) [26, 27]. Uzasadnienie wyboru modelu dwustronnie ograniczonego jako bardziej realistycznego [3, 5].
4. Modelowanie Całego Łańcucha Podróży (WTC): Konieczność włączenia pierwszej i ostatniej mili (access/egress) [7]. Włączenie kosztów oczekiwania i transferów (penalizacja) do funkcji użyteczności/kosztu [8, 9, 28].
5. Sprawiedliwość Transportowa i Mapowanie Społeczne: Koncepcja równości (equality) vs. sprawiedliwości (justice) [29]. Rola segmentacji demograficznej w kalibracji współczynnika zaniku
beta (wrażliwość na czas a zamożność) [10, 11].
Rozdział 2: Dane i Rozwiązanie Problemu Niespójności Czasowej
1. Studia Przypadku: Uzasadnienie wyboru Paryża (kontynuacja), Dublina (dostępność danych przepływów [30]) i Warszawy (miasto lokalne, polski kontekst).
2. Dostępność Danych Transportowych (GTFS):
    ◦ Źródła GTFS dla Paryża i Dublina (dane z 2016 r. i 2018 r.) [31-33].
    ◦ Wyzwania i rola GTFS w modelowaniu sieci (zawiera czasy podróży, częstotliwości, itp.) [34, 35].
3. Dostępność Danych Popytowych i Celów (POI/Zatrudnienie):
    ◦ Paryż: Dane o strefach wysokiego zatrudnienia [36].
    ◦ Dublin: Dostępność dokładnych danych o lokalizacji zatrudnienia w siatce 1x1 km [30].
    ◦ Warszawa: Dane o liczbie ofert pracy (punkt wyjścia) [36, 37].
    ◦ Ludność (De Jure): Dane z siatki 1x1 km (dane ISTAT dla Rzymu/ogólnie dla UE) [38, 39].
    ◦ Wskaźniki Zamożności: Konieczność pozyskania lub użycia zastępczych wskaźników społeczno-ekonomicznych dla segmentacji [10, 11].
4. Adresowanie Niespójności Czasowej Danych (Data Inconsistency):
    ◦ GTFS z różnych lat (np. Paryż 2016) i dane demograficzne/zatrudnienia z innych okresów (np. Dublin 1x1 km) [30, 31, 38].
    ◦ Strategie normalizacji/harmonizacji: Wyjaśnienie, w jaki sposób różnice czasowe (lata) między danymi transportowymi a demograficznymi zostaną zaadresowane (np. poprzez uznanie, że sieć transportowa jest statyczna w krótkim okresie lub poprzez walidację, że główne wskaźniki demograficzne nie uległy drastycznym zmianom). Konieczność przedstawienia tego jako ograniczenia w dyskusji [12].
Rozdział 3: Metodologia Zaawansowanej Analizy Dostępności
1. Etap I: Przygotowanie Danych i Topologia Sieci:
    ◦ Integracja i czyszczenie danych GTFS (autobusy, metro/kolej, tramwaje) [40, 41].
    ◦ Modelowanie sieci dla każdego miasta w dualizmie L-space (infrastruktura) i P-space (usługa) [21, 23].
    ◦ Analiza podstawowych właściwości topologicznych sieci (np. centralność, spójność) [42].
2. Etap II: Kalibracja Kosztu Podróży (WTC):
    ◦ Obliczenie uogólnionego kosztu podróży (GTC) c_ij, uwzględniającego cały łańcuch podróży [43, 44].
    ◦ Włączenie elementów "pierwszej i ostatniej mili": czas dotarcia pieszego (na podstawie OpenStreetMap) [45, 46], czas oczekiwania (na podstawie częstotliwości - T_wait) i czas transferu (penalizacja) [8, 28].
3. Etap III: Implementacja Modeli Grawitacyjnych:
    ◦ Definicja stref analitycznych (np. siatka 1x1 km) [38, 47, 48].
    ◦ Identyfikacja i kwantyfikacja celów (POI) oraz potencjału zatrudnienia (T_attr) [26].
    ◦ Zastosowanie modelu grawitacyjnego (prawdopodobnie dwustronnie ograniczonego) do obliczenia macierzy przepływów [5, 49].
    ◦ Kalibracja współczynnika zaniku (
beta) dla różnych grup społeczno-ekonomicznych (wykorzystanie danych o zamożności do segmentacji) [10, 11].
    ◦ Obliczenie wskaźnika dostępności A_i (np. odwrócony średni koszt dojazdu) [50].
4. Etap IV: Mapowanie Społeczne i Porównanie:
    ◦ Wizualizacja i przestrzenna analiza nierówności w dostępie dla poszczególnych grup społecznych (Mapowanie Społeczne) [11, 51].
    ◦ Porównanie miar dostępności między Paryżem, Dublinem i Warszawą.
Rozdział 4: Wyniki i Dyskusja
1. Wyniki Topologiczne (L/P-space): Diagnoza problemów infrastruktury i operacyjnych w każdym mieście [22].
2. Wyniki Grawitacyjne i WTC: Prezentacja map dostępności potencjalnej i ocena, jak uwzględnienie WTC i segmentacji
beta zmieniło wyniki w stosunku do pierwotnego projektu dla Paryża [52].
3. Analiza Sprawiedliwości Transportowej: Kwantyfikacja różnic w dostępie (np. do miejsc pracy) w zależności od zamożności strefy/grupy docelowej [11, 53].
4. Dyskusja Komparatywna i Ograniczenia: Analiza wpływu różnic w jakości/okresie danych na porównywalność miast [54].
Wnioski i Rekomendacje
1. Synteza Osiągniętych Celów.
2. Rekomendacje Planistyczne: Ukierunkowane interwencje dla każdego miasta (np. wzmocnienie L-space, poprawa częstotliwości, wsparcie mikromobilności - "ostatniej mili") [22, 55].
3. Kierunki Dalszych Badań.
--------------------------------------------------------------------------------
III. Aspekty Analityczne (Aspekty)
1. Analiza Topologiczna (L-space i P-space)
Zastosowanie topologii L-space (Space-of-Infrastructure) i P-space (Space-of-Service) [23, 56] jest niezbędne do:
• Modelowania Sieci Transportu Zbiorowego (PTN): L-space modeluje fizyczne powiązania między kolejnymi przystankami na trasie [57]. P-space modeluje połączenia między wszystkimi przystankami obsługiwanymi przez tę samą linię, odzwierciedlając bezpośrednią łączność i doświadczenie użytkownika [58].
• Diagnostyka Problemów: Porównanie centralności lub miar dostępności obliczonych w obu przestrzeniach pozwala zdiagnozować, czy niski poziom dostępności wynika z braku infrastruktury (niski L-space) czy z nieefektywnych operacji (niski P-space przy wysokim L-space, np. rzadkie kursy lub złe przesiadki) [22].
• Źródła Danych: Wymaga to użycia danych GTFS dla każdego z miast, które zawierają informacje o trasach, przystankach i sekwencjach [34, 35].
2. Modele Grawitacyjne i Impedancja
Modele grawitacyjne (Gravity-type approach) [24, 59] będą stanowiły rdzeń ilościowej oceny dostępności potencjalnej:
• Identyfikacja POI (Points of Interest): Wskaźnik atrakcyjności (T_attr) musi uwzględniać dzienne cele przepływu ludności, takie jak miejsca pracy (zatrudnienie), jako kluczowy element analizy dojazdów [26, 49]. Możliwe będzie wykorzystanie istniejących danych demograficznych (siatka 1x1 km) [38] oraz specyficznych danych o lokalizacji zatrudnienia, szczególnie dostępnych dla Dublina [30].
• Aktualizacja Metryki Kosztu: Zamiast prostego syntetycznego wskaźnika, użytego w projekcie wstępnym [60], zastosowany zostanie uogólniony koszt podróży (Generalized Travel Cost - GTC), który będzie stanowił podstawę funkcji impedancji f(c_ij) [43, 44]. Koszt c_ij powinien być oczekiwanym czasem podróży transportem zbiorowym [49, 61, 62].
• Współczynnik Impedancji oparty o Zamożność (
beta): W celu uwzględnienia sprawiedliwości społecznej (Society Mapping), współczynnik zaniku (
beta), określający wrażliwość na czas podróży, musi być kalibrowany w oparciu o różnice w zamożności (dochody) [10, 11]. Wysoki dochód często koreluje z wyższą wrażliwością na czas (wyższe
beta), co wymaga segmentacji demograficznej modelu [10].
3. Cały Łańcuch Podróży (Whole Travel Chain - WTC)
Analiza WTC zapewni realistyczne uwzględnienie multimodalnego charakteru podróży:
• Pierwsza i Ostatnia Mila (First and Last Mile): Całkowity koszt podróży (c_ij) musi być obliczony jako suma wszystkich segmentów: czas dostępu pieszo/rowerem (do przystanku), czas oczekiwania/transferu (w tym penalizacja za przesiadki) oraz czas w pojeździe [7-9].
• Źródła Danych WTC: Czas przejścia pieszego między przystankami jest już częściowo dostępny w zbiorze GTFS na podstawie OpenStreetMap [31, 45, 46]. Czas oczekiwania (T_wait) zostanie oszacowany na podstawie częstotliwości kursowania (headway) z danych GTFS [63, 64]. Pominięcie tych kosztów (jak to często bywa w uproszczonych modelach) prowadzi do przeszacowania użyteczności systemu TZ [7].
• Włączenie Baterii (Bariery Fizyczne i Społeczne): Choć trudne, bariery socjologiczne (np. w przypadku osób z niepełnosprawnościami) mogą być włączone do modelu WTC jako negatywne stałe specyficzne dla alternatywy (ASC_m), obniżające użyteczność całego łańcucha podróży dla wrażliwych grup [11, 65].
4. Zarządzanie Niespójnością Czasową Danych
Fakt, że dane transportowe (GTFS, np. Paryż 2016) i dane demograficzne/zatrudnienia (np. spis powszechny, dane Dublin 1x1 km) pochodzą z różnych okresów czasowych, musi zostać jasno zaadresowany [12]. W pracy należy:
• Udokumentować Horyzonty Czasowe: Szczegółowo opisać, z jakiego okresu pochodzi każda kategoria danych dla każdego miasta [31, 38, 66].
• Oszacować Ryzyko Zniekształcenia: Ocenić, w jakim stopniu zmiany w sieci transportowej (GTFS) lub dystrybucji populacji/zatrudnienia mogły wpłynąć na wyniki w okresie między pozyskaniem danych a datą analizy.
• Strategia Metodologiczna: Przyjąć spójne założenia, np. używać starszych danych populacyjnych jako statycznego rozkładu popytu dla analizy wrażliwości sieci transportowej z danego okresu.
Podsumowując, praca magisterska przekształca analizę podaży (Projekt Kozińskiego) w holistyczną, popytowo-grawitacyjną ocenę dostępności, wzbogaconą o wymiar behawioralny (WTC) i sprawiedliwości społecznej (segmentacja
beta na podstawie danych o zamożności), co jest zgodne z zaawansowanymi ramami modelowania transportowego [13, 52].

