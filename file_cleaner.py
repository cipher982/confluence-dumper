import os
import re
import json
import shutil
import requests
from typing import List
from bs4 import BeautifulSoup
from tqdm import tqdm


class URLProcessor:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.mapping = {}

    def extract_href_urls(self, text: str, url_subdir: str) -> List[str]:
        pattern = r'href="([^"]*)"'
        urls = re.findall(pattern, text)
        print(f"Found {len(urls)} URLs")
        return [self.base_url + url for url in urls if url.startswith(f"/{url_subdir}/")]

    def save_urls_to_file(self, urls: List[str], output_file: str) -> None:
        with open(output_file, "w") as file:
            file.writelines(f"{url}\n" for url in urls)

    def find_links_in_html(self, input_file: str, url_subdir: str, output_file: str) -> None:
        with open(input_file, "r") as file:
            text = file.read()

        urls = self.extract_href_urls(text, url_subdir)
        print(f"Found {len(urls)} cleaned URLs")
        self.save_urls_to_file(urls, output_file)

    def create_page_id_mapping(self, urls: List[str]) -> None:
        for url in tqdm(urls):
            response = requests.get(url)
            html = response.text
            soup = BeautifulSoup(html, "html.parser")
            tag = soup.find("html", class_="no-js")
            page_id = tag.get("data-vp-page-id")  # type: ignore
            self.mapping[url] = page_id

        print(f"Found {len(self.mapping)} page IDs")

    def clean_export_data(self, input_folder: str, output_folder: str) -> None:
        if os.path.exists(output_folder):
            shutil.rmtree(output_folder)
        os.makedirs(output_folder)

        good_mappings = []
        failed_mappings = []

        for filename in os.listdir(input_folder):
            file_path = os.path.join(input_folder, filename)

            if not filename.endswith(".json"):
                print(f"Skipping {file_path} - Not a JSON file")
                continue

            with open(file_path, "r") as file:
                data = json.load(file)

            current_page_id = data["url"].rstrip("/").split("/")[-1]

            if any(page_id == current_page_id for page_id in self.mapping.values()):
                for key, value in self.mapping.items():
                    if value in data["url"]:
                        data["internal_url"] = data["url"]
                        data["url"] = key
                        break

                if data["title"].startswith("Forward to"):
                    continue

                data = {k: data[k] for k in ["title", "internal_url", "url", "paragraphs"]}

                output_path = os.path.join(output_folder, filename)
                with open(output_path, "w") as file:
                    json.dump(data, file, indent=4)
                good_mappings.append(data["url"])
            else:
                failed_mappings.append(data["url"])

        print(f"successfull mappings: {len(good_mappings)/len(good_mappings+failed_mappings)}")
        print(f"Sample successfull mappings: {good_mappings[:5]}")
        print(f"Sample failed mappings: {failed_mappings[:5]}")


if __name__ == "__main__":
    base_url = "https://knowledgebase.zetaglobal.com"

    processor = URLProcessor(base_url)

    html_space_mapping = {
        "./data/raw_html/zmp.txt": "KB",
        "./data/raw_html/programmatic-user-guide.txt": "PUG",
        "./data/raw_html/gswz.txt": "GSWZ",
    }

    html_url_mapping = {
        "./data/raw_html/zmp.txt": "zmp",
        "./data/raw_html/programmatic-user-guide.txt": "programmatic-user-guide",
        "./data/raw_html/gswz.txt": "gswz",
    }

    for html_file, space in html_space_mapping.items():
        print(f"===== Processing {html_file} for space {space} =====")

        urls_file = f"links_{space}.txt"
        processor.find_links_in_html(
            input_file=html_file,
            url_subdir=html_url_mapping[html_file],
            output_file=urls_file,
        )

        # Load the URLs from the file
        with open(urls_file, "r") as f:
            urls = f.read().splitlines()

        processor.create_page_id_mapping(urls)

        # Define the input and output folder paths
        input_folder = f"./export/{space}"
        output_folder = f"./export_cleaned/{space}"

        processor.clean_export_data(input_folder, output_folder)
