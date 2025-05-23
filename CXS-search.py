import os
import re
import time
import logging
from colorama import Fore, init
from requests import get
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

log_directory = 'logs'
os.makedirs(log_directory, exist_ok=True)

error_log = logging.FileHandler(os.path.join(log_directory, 'error.logs'))
running_log = logging.FileHandler(os.path.join(log_directory, 'running.logs'))
cxs_log = logging.FileHandler(os.path.join(log_directory, 'cxs.logs'))

error_log.setLevel(logging.ERROR)
running_log.setLevel(logging.INFO)
cxs_log.setLevel(logging.INFO)

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

error_log.setFormatter(formatter)
running_log.setFormatter(formatter)
cxs_log.setFormatter(formatter)

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(error_log)
logger.addHandler(running_log)
logger.addHandler(cxs_log)

init()

NAME_REGEX = re.compile(r"^[a-zA-Zà-ÿÀ-ÿ' -]+$")
CITY_REGEX = re.compile(r"^[a-zA-Zà-ÿÀ-ÿ' -]+$")

MAX_REQUESTS = 700
MAX_THREADS = min(20, os.cpu_count() * 2)

class DirectorySearch:
    def __init__(self):
        self.base_url = "https://gepatroj.com/{}/adresse-et-telephone-"

    def search(self, last_name, max_pages=700, max_errors=5):
        first_char = last_name[0].lower()
        page_numbers = list(range(1, min(max_pages, MAX_REQUESTS) + 1))
        all_data = []
        total_found = 0
        consecutive_errors = 0

        progress_bar = tqdm(total=1000, desc="Chargement des pages", unit="page", ncols=100)

        with ThreadPoolExecutor(max_workers=MAX_THREADS) as executor:
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
                            logger.warning(f"Nombre maximum d'erreurs consécutives atteint (page {page}).")
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
                    logger.error(f"Erreur lors de la récupération de la page {page}: {str(e)}")
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        break

        progress_bar.close()
        logger.info(f"Recherche terminée : {total_found} résultats trouvés pour '{last_name}'.")
        return all_data

    def fetch_page(self, page_num, first_char, search_name):
        url = f"{self.base_url.format(first_char)}{search_name.lower()}-{page_num}.php"
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = get(url, headers=headers, timeout=5)
            if response.status_code == 404:
                time.sleep(1)
                return None
            elif response.status_code == 200:
                return self.parse_html(response.text)
            else:
                logger.error(f"Erreur: impossible de récupérer la page {page_num} (status: {response.status_code}).")
                return None
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la page {page_num}: {str(e)}")
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
            logger.info(f"Résultats :")
            for entry in data:
                print(f"    {Fore.LIGHTWHITE_EX}{entry[0]} - {entry[1]} - {entry[2]}")
        else:
            logger.warning(f"Aucun résultat trouvé.")

def validate_input(prompt, regex, allow_empty=False):
    while True:
        user_input = input(prompt).strip()
        if allow_empty and user_input == "":
            return user_input 
        if regex.match(user_input):
            return user_input
        else:
            print(f"{Fore.LIGHTRED_EX}[!] Entrée invalide. Veuillez entrer une valeur valide.")

if __name__ == "__main__":
    logger.info("Démarrage du programme...")
    directory = DirectorySearch()

    while True:
        print(""" 
 ██████╗██╗  ██╗███████╗      ███████╗███████╗ █████╗ ██████╗  ██████╗██╗  ██╗
██╔════╝╚██╗██╔╝██╔════╝      ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔════╝██║  ██║
██║      ╚███╔╝ ███████╗█████╗███████╗█████╗  ███████║██████╔╝██║     ███████║
██║      ██╔██╗ ╚════██║╚════╝╚════██║██╔══╝  ██╔══██║██╔══██╗██║     ██╔══██║
╚██████╗██╔╝ ██╗███████║      ███████║███████╗██║  ██║██║  ██║╚██████╗██║  ██║
 ╚═════╝╚═╝  ╚═╝╚══════╝      ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝ by Hexcode
                        https://t.me/theCXSgroup""")

        last_name = validate_input(f"{Fore.LIGHTCYAN_EX}Entrez le nom de famille à rechercher: {Fore.LIGHTWHITE_EX}", NAME_REGEX)
        city = validate_input(f"{Fore.LIGHTCYAN_EX}Entrez la ville (laisser vide pour ignorer le filtrage): {Fore.LIGHTWHITE_EX}", CITY_REGEX, allow_empty=True)

        results = directory.search(last_name)

        if city.strip():
            filtered_results = directory.filter_by_city(results, city)
            logger.info(f"Résultats filtrés pour la ville '{city}':")
            directory.show_results(filtered_results)
        else:
            directory.show_results(results)

        continue_search = input(f"\n{Fore.LIGHTCYAN_EX}Voulez-vous effectuer une autre recherche ? (o/n): {Fore.LIGHTWHITE_EX}")
        if continue_search.lower() != 'o':
            logger.info(f"Merci d'avoir utilisé le script !")
            break
