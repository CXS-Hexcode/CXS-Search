import os
from colorama import Fore, init
from requests import get
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
import time
init()

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

class DirectorySearch:
    def __init__(self):
        self.base_url = "https://gepatroj.com/{}/adresse-et-telephone-"

    def search(self, last_name, max_pages=700, max_errors=5):
        first_char = last_name[0].lower()
        page_numbers = list(range(1, max_pages + 1))
        all_data = []
        total_found = 0
        consecutive_errors = 0

        progress_bar = tqdm(total=max_pages, desc="Chargement des pages", unit="page", ncols=100)

        with ThreadPoolExecutor(max_workers=50) as executor:
            page_futures = {
                executor.submit(self.fetch_page, page, first_char, last_name): page
                for page in page_numbers
            }

            for future in as_completed(page_futures):
                page = page_futures[future]
                try:
                    result = future.result()
                    if result is None:
                        consecutive_errors += 1
                        if consecutive_errors >= max_errors:
                            time.sleep(1)
                            break
                    else:
                        data, count = result
                        if count == 0:
                            consecutive_errors += 1
                        else:
                            consecutive_errors = 0
                        
                        total_found += count
                        all_data.extend(data)
                        progress_bar.update(1)

                except Exception as e:
                    print(f"{Fore.LIGHTRED_EX}[+]{Fore.LIGHTWHITE_EX} Erreur lors de la récupération de la page {page}: {str(e)}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        break

        progress_bar.close()
        print(f"\n{Fore.LIGHTGREEN_EX}[+] Recherche terminée : {total_found} résultats trouvés pour '{last_name}'.")
        return all_data

    def fetch_page(self, page_num, first_char, search_name):
        url = f"{self.base_url.format(first_char)}{search_name.lower()}-{page_num}.php"
        try:
            response = get(url)
            if response.status_code == 404:
                time.sleep(1)
                return None

            elif response.status_code == 200:
                return self.parse_html(response.text)
            else:
                print(f"{Fore.LIGHTRED_EX}[+]{Fore.LIGHTWHITE_EX} Erreur: impossible de récupérer la page {page_num} (status: {response.status_code}).")
                return None
        except Exception as e:
            print(f"{Fore.LIGHTRED_EX}[+]{Fore.LIGHTWHITE_EX} Erreur lors de la récupération de la page {page_num}: {str(e)}")
            return [], 0


    def parse_html(self, html):
        soup = BeautifulSoup(html, 'html.parser')
        results = soup.find_all('li')
        parsed_data = []
        count = 0

        if results:
            for result in results:
                try:
                    name = result.find('h2').text.strip()
                    phone = result.find('label').text.strip().split(' - ')[0]
                    address = result.find('p').text.strip()
                    parsed_data.append((name, phone, address))
                    count += 1
                except AttributeError:
                    continue
        return parsed_data, count

    def filter_by_city(self, data, city):
        filtered_data = []
        city_lower = city.lower().strip() if city else None

        if city_lower:
            for name, phone, address in data:
                normalized_address = " ".join(address.lower().split())
                if city_lower in normalized_address:
                    filtered_data.append((name, phone, address))

        return filtered_data

    def show_results(self, data):
        if data:
            print(f"\n{Fore.LIGHTGREEN_EX}[+] Résultats:\n")
            for entry in data:
                print(f"    {Fore.LIGHTWHITE_EX}{entry[0]} - {entry[1]} - {entry[2]}")
        else:
            print(f"{Fore.LIGHTRED_EX}[+]{Fore.LIGHTWHITE_EX} Aucun résultat trouvé.")

if __name__ == "__main__":
    directory = DirectorySearch()

    while True:
        clear_screen()
        print(""" 
 ██████╗██╗  ██╗███████╗      ███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
██╔════╝╚██╗██╔╝██╔════╝      ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
██║      ╚███╔╝ ███████╗█████╗███████╗█████╗  ███████║██████╔╝██║     ███████║
██║      ██╔██╗ ╚════██║╚════╝╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
╚██████╗██╔╝ ██╗███████║      ███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
 ╚═════╝╚═╝  ╚═╝╚══════╝      ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ by Hexcode
                        https://t.me/theCXSgroup""")

        last_name = input(f"{Fore.LIGHTCYAN_EX}Entrez le nom de famille à rechercher: {Fore.LIGHTWHITE_EX}")
        city = input(f"{Fore.LIGHTCYAN_EX}Entrez la ville (laisser vide pour ignorer le filtrage): {Fore.LIGHTWHITE_EX}")

        results = directory.search(last_name)

        if city.strip():
            filtered_results = directory.filter_by_city(results, city)
            print(f"\n{Fore.LIGHTGREEN_EX}[+] Résultats filtrés pour la ville '{city}':")
            directory.show_results(filtered_results)
        else:
            directory.show_results(results)

        continue_search = input(f"\n{Fore.LIGHTCYAN_EX}Voulez-vous effectuer une autre recherche ? (o/n): {Fore.LIGHTWHITE_EX}")
        if continue_search.lower() != 'o':
            print(f"{Fore.LIGHTGREEN_EX}[+] Merci d'avoir utilisé le script !")
            break
