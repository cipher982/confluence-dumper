import json
import requests
import shutil
import re
from typing import Optional, Dict, Tuple, List
from urllib.parse import quote, unquote

from bs4 import BeautifulSoup


class ConfluenceException(Exception):
    """Exception for Confluence export issues"""

    def __init__(self, message: str) -> None:
        super().__init__(message)


def http_get(
    request_url: str,
    auth: Optional[Tuple[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    verify_peer_certificate: bool = True,
    proxies: Optional[Dict[str, str]] = None,
) -> Dict:
    """Requests a HTTP url and returns a requested JSON response."""

    response = requests.get(request_url, auth=auth, headers=headers, verify=verify_peer_certificate, proxies=proxies)
    if response.status_code == 200:
        return response.json()
    else:
        raise ConfluenceException(f"Error {response.status_code}: {response.reason} on requesting {request_url}")


def http_download_binary_file(
    request_url: str,
    file_path: str,
    auth: Optional[Tuple[str, str]] = None,
    headers: Optional[Dict[str, str]] = None,
    verify_peer_certificate: bool = True,
    proxies: Optional[Dict[str, str]] = None,
) -> None:
    """Requests a HTTP url to save a file on the local filesystem."""

    response = requests.get(
        request_url, stream=True, auth=auth, headers=headers, verify=verify_peer_certificate, proxies=proxies
    )
    if response.status_code == 200:
        with open(file_path, "wb") as downloaded_file:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, downloaded_file)
    else:
        raise ConfluenceException(f"Error {response.status_code}: {response.reason} on requesting {request_url}")


def write_html(path: str, content: str) -> None:
    """Writes a string to a file."""

    with open(path, "w", encoding="utf-8") as the_file:
        the_file.write(content)


def write_json(path: str, content: dict) -> None:
    """Writes a dictionary to a file in JSON format with proper formatting."""
    with open(path, "w", encoding="utf-8") as the_file:
        json.dump(content, the_file, ensure_ascii=False, indent=4)


def extract_content(html: str, web_url: str) -> Dict:
    # Parse the HTML with Beautiful Soup
    soup = BeautifulSoup(html, "html.parser")

    # Initialize the current_header variable
    current_header = ""

    # Iterate over all elements in the HTML
    paragraphs = []
    for element in soup.find_all():
        if element.name.startswith("h") and len(element.name) == 2 and element.name[1].isdigit():
            # Header found, update the current_header variable
            current_header = element.get_text()
        elif element.name == "p":
            # Paragraph found, add it to the paragraphs list with the current_header as the key
            paragraphs.append({"header": current_header, "content": element.get_text()})

    # Find title
    title = soup.title.string if soup.title else "No Title"

    # Create a dictionary with all the data
    data = {"title": title, "url": web_url, "paragraphs": paragraphs}

    return data


def write_html_2_file(
    path: str,
    title: str,
    content: str,
    html_template: str,
    web_url: str,
    additional_headers: Optional[List[str]] = None,
) -> None:
    """Writes HTML content to a file using a template."""

    additional_html_headers = "\n\t".join(additional_headers) if additional_headers else ""
    replacements = {"title": title, "content": content, "additional_headers": additional_html_headers}

    html_content = html_template  # Start with the original template

    for placeholder, replacement in replacements.items():
        regex_placeholder = rf"{{%\s*{placeholder}\s*%}}"
        html_content = re.sub(
            regex_placeholder,
            replacement.replace("\\", "\\\\"),
            html_content,
            flags=re.IGNORECASE,
        )

    # Extract the html_content again to remove fluff
    json_content = extract_content(html_content, web_url)

    # Replace .html with .json
    path = path.replace(".html", ".json")

    # Write the file
    write_json(path, json_content)


def sanitize_for_filename(original_string: str) -> str:
    """Sanitizes a string to use it as a filename on most filesystems."""

    return re.sub('[\\\\/:*?"<>|]', "_", original_string)


def decode_url(encoded_url: str) -> str:
    """Unquotes and decodes a given URL."""

    return unquote(encoded_url)


def encode_url(decoded_url: str) -> str:
    """Quotes and encodes a given URL."""

    return quote(decoded_url)


def is_file_format(file_name: str, file_extensions: List[str]) -> bool:
    """Checks whether the extension of the given file is in a list of file extensions."""
