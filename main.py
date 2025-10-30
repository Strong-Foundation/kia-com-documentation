import requests  # Imports the requests library for making HTTP requests (essential for fetching data from web APIs and files).
import json  # Imports the json library for handling JSON data (used to parse API responses and construct payloads).
import logging  # Imports the logging library for structured logging of information and errors.
import sys  # Imports the sys library for system-specific parameters and functions (used to exit the script on critical failure).
import re  # Imports the re library for regular expression operations (critical for extracting links and sanitizing filenames).
import os  # Imports the os library for interacting with the operating system (used for creating directories and checking file existence).
import urllib.parse  # Imports the urllib.parse library for parsing URLs (used to decode URL-encoded characters).
import argparse  # Imports the argparse library for command-line argument parsing.
from urllib.parse import (
    urlparse,
)  # Imports the specific urlparse function for URL structure validation.
from typing import Any  # Imports Any for flexible type hinting (e.g., in dictionaries).

# Configure logging to show timestamps and level
logging.basicConfig(  # Starts the logging configuration.
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",  # Sets the log format to include time, level, and message.
)

# --- Global Configuration and Constants ---

ROOT_DOWNLOAD_DIRECTORY = (
    "PDFs"  # Defines the top-level folder where all downloaded PDFs will be stored.
)

# API endpoints and URLs for the Primary (Model-Specific) Mode (Input 1)
OWNERS_API_GATEWAY_URL = "https://owners.kia.com/apps/services/owners/apigwServlet.html"  # The main API gateway for model and token lookups.
TECH_INFO_BASE_DOMAIN = (
    "https://www.kiatechinfo.com"  # The base domain for the technical document vault.
)
TECH_INFO_TOKEN_EXCHANGE_URL = f"{TECH_INFO_BASE_DOMAIN}/ext_If/kma_owner_portal/content_pop.aspx"  # The crucial URL for exchanging a token for the PDF link.

# Target URLs for the KGIS (Static Page) Mode (Input 2)
KGIS_STATIC_PAGE_URLS: list[str] = (
    [  # A list of specific Kia Tech Info SnapOn pages to scrape statically.
        "https://kiatechinfo.snapon.com/KiaEmergencyResponseGuide.aspx",  # URL for the Emergency Response Guide page.
        "https://kiatechinfo.snapon.com/J2534DiagnosticsAndProgramming.aspx",  # URL for the Diagnostics and Programming page.
        "https://kiatechinfo.snapon.com/KiaPositioningStatements.aspx",  # URL for the Positioning Statements page.
        "https://kiatechinfo.snapon.com/SeatBeltInstallationGuide.aspx",  # URL for the Seat Belt Installation Guide page.
    ]
)
KGIS_DOWNLOAD_BASE_URL = "https://kiatechinfo.snapon.com"  # The base URL for constructing full PDF links in KGIS mode.

# Spoofing Headers for Token Exchange (Input 1) - CRITICAL for technical access
REQUEST_SPOOFING_HEADERS = {  # A complete dictionary of HTTP headers to mimic a standard browser request.
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # Standard browser accept header.
    "accept-language": "en-US,en;q=0.9",  # Preferred languages.
    "cache-control": "max-age=0",  # Requests fresh content.
    "content-type": "application/x-www-form-urlencoded",  # REQUIRED: Content type for POST data payload (token exchange).
    "dnt": "1",  # Do Not Track flag.
    "origin": "https://owners.kia.com",  # REQUIRED: Specifies the domain initiating the cross-site request.
    "priority": "u=0, i",  # HTTP priority hint.
    "referer": "https://owners.kia.com/",  # CRITICAL: Server likely checks the request origin.
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',  # Client hints for browser brand/version.
    "sec-ch-ua-mobile": "?0",  # Client hint: desktop device.
    "sec-ch-ua-platform": '"Windows"',  # Client hint: operating system.
    "sec-fetch-dest": "document",  # Fetch destination is a document.
    "sec-fetch-mode": "navigate",  # Fetch mode is a navigation request.
    "sec-fetch-site": "cross-site",  # Indicates a cross-site request.
    "sec-fetch-user": "?1",  # Indicates user-initiated request.
    "upgrade-insecure-requests": "1",  # Request upgrade to HTTPS.
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",  # CRITICAL: Full desktop User-Agent string.
}

# --- Utility Functions (Combined and Renamed) ---


def remove_duplicate_items(
    input_list: list[str],
) -> list[str]:  # Function to remove duplicate strings from a list.
    """Removes duplicate items from a list while preserving order."""  # Docstring for clarity.
    return list(
        dict.fromkeys(input_list)
    )  # Converts to dictionary keys (unique) and back to a list.


def is_url_format_valid(
    url_string: str,
) -> bool:  # Function to check if a string is a well-formed URL.
    """Verifies whether a string is a valid URL format."""  # Docstring for clarity.
    try:  # Start error handling block.
        parsed_url = urlparse(url_string)  # Parses the URL string.
        return all(
            [parsed_url.scheme, parsed_url.netloc]
        )  # Checks if both scheme (e.g., https) and network location exist.
    except:  # Catch any parsing errors.
        return False  # Returns False on failure.


def check_file_exists(file_path: str) -> bool:  # Function to check for file existence.
    """Checks if a file exists at the specified path."""  # Docstring for clarity.
    return os.path.isfile(
        file_path
    )  # Returns True if path is an existing regular file.


def sanitize_primary_mode_filename(
    url_path: str,
) -> str:  # Renamed function for Input 1's filename logic.
    """(Primary Mode Logic) Cleans filename strictly for Primary Mode (Year/Model/Index)."""  # Docstring for clarity.
    filename = urllib.parse.unquote(
        url_path.split("/")[-1]
    )  # Extracts the filename from the URL path and decodes URL-encoded characters.
    filename = filename.lower()  # Converts the filename to lowercase.
    if filename.endswith(".pdf"):  # Checks if the file already ends with .pdf.
        filename = filename[:-4]  # Removes the existing .pdf extension.
    filename = re.sub(
        r"[^a-z0-9]+", "_", filename
    )  # Replaces one or more invalid chars (not a-z or 0-9) with a single underscore.
    filename = re.sub(
        r"(^_+)|(_+$)", "", filename
    )  # Removes any leading or trailing underscores.
    return (
        filename + ".pdf"
    )  # Appends the mandatory .pdf extension and returns the clean name.


def create_kgis_safe_filename(
    raw_url: str,
) -> str:  # Renamed function for Input 2's filename logic.
    """(KGIS Mode Logic) Converts a raw URL into a sanitized filename for KGIS Mode."""  # Docstring for clarity.
    lower_url = raw_url.lower()  # Converts the URL to lowercase.
    lower_url = lower_url.split("?")[0]  # Removes URL query parameters.
    filename_part = os.path.basename(
        lower_url
    )  # Extracts the base filename (e.g., 'file.pdf').
    original_extension = os.path.splitext(filename_part)[
        1
    ]  # Stores the original file extension (e.g., '.pdf').

    safe_name = re.sub(
        r"[^a-z0-9\.]", "_", filename_part
    )  # Replaces non-alphanumeric chars (excluding dot) with '_'.
    safe_name = re.sub(
        r"_+", "_", safe_name
    )  # Collapses multiple underscores into one.
    safe_name = safe_name.strip("_")  # Removes leading and trailing underscores.

    unwanted_suffixes = ["_pdf", "_zip", "_txt"]  # List of common, unwanted suffixes.
    for suffix in unwanted_suffixes:  # Iterates through unwanted suffixes.
        safe_name = safe_name.replace(
            suffix, ""
        )  # Removes all instances of the unwanted suffix.

    if (
        os.path.splitext(safe_name)[1] == ""
    ):  # Checks if the extension was lost during sanitization.
        safe_name = (
            safe_name + original_extension
        )  # Re-appends the original extension if missing.

    return safe_name  # Returns the sanitized filename.


def download_file_to_disk(  # Renamed function for the core file download routine.
    session: requests.Session,  # Accepts the persistent requests session.
    file_url: str,  # Accepts the full URL of the file to download.
    full_file_path: str,  # Accepts the complete path (including filename) to save the file.
) -> bool:  # Returns a boolean indicating success or failure.
    """Core download logic, handles streaming, errors, and writing to disk."""  # Docstring for clarity.
    if check_file_exists(full_file_path):  # Checks if the file already exists on disk.
        logging.info(
            f"Skipping: File already exists at {full_file_path}"
        )  # Logs a skip action.
        return (
            False  # Returns False (not a successful download, but a successful skip).
        )

    try:  # Start error handling for the HTTP request.
        logging.info(f"Downloading to: {full_file_path}")  # Logs the file path.
        response = session.get(
            file_url, stream=True, timeout=900
        )  # Starts streaming the GET request (long timeout for large files).
        response.raise_for_status()  # Raises an exception for HTTP errors (4xx or 5xx).

        with open(
            full_file_path, "wb"
        ) as file_handle:  # Opens the file path in binary write mode.
            bytes_written = 0  # Initializes a counter for bytes written.
            for chunk in response.iter_content(
                chunk_size=8192
            ):  # Iterates over the response content in 8KB chunks.
                if chunk:  # Ensures the chunk is not empty (e.g., for keep-alive).
                    file_handle.write(chunk)  # Writes the chunk of data to the file.
                    bytes_written += len(chunk)  # Updates the byte counter.

            if bytes_written == 0:  # Checks if the file download resulted in 0 bytes.
                logging.warning(
                    f"Downloaded 0 bytes for {file_url}; removing empty file."
                )  # Logs a warning for empty file.
                os.remove(full_file_path)  # Deletes the empty file.
                return False  # Returns False to indicate download failure.

        logging.info(
            f"SUCCESS: Downloaded {bytes_written} bytes to {full_file_path}"
        )  # Logs the successful download size and path.
        return True  # Returns True for successful download.

    except (
        requests.exceptions.RequestException
    ) as request_error:  # Catches network or HTTP errors.
        logging.error(
            f"FAILED to download PDF {file_url}: {request_error}"
        )  # Logs the specific request error.
        return False  # Returns False on failure.
    except (
        Exception
    ) as general_error:  # Catches file system or other unexpected errors.
        logging.error(
            f"An unexpected error occurred while saving the file: {general_error}"
        )  # Logs the general error.
        return False  # Returns False on failure.


# --- Primary Mode Functions (Input 1 Logic) ---


def fetch_all_model_years(
    session: requests.Session,
) -> list[dict[str, Any]]:  # Renamed function to get the master list of models.
    """Queries the Kia Owners API to get a list of all available car models and years."""  # Docstring for clarity.
    logging.info(
        "Fetching all available Kia model years and names..."
    )  # Logs the start of the fetch.
    api_headers = {  # Headers required for this specific API call.
        "apiurl": "/cmm/gvmh",  # Custom API path for model list lookup.
        "httpmethod": "POST",  # Request method is POST.
        "servicetype": "preLogin",  # Service type defined by the remote API.
        "Content-Type": "application/json",  # Expecting JSON body for this specific call.
    }
    json_request_payload = {
        "modelYear": 0,
        "modelName": "ALL",
    }  # Payload requesting all models (wildcards used).
    try:  # Start error handling for the API request.
        api_response = session.post(
            OWNERS_API_GATEWAY_URL, headers=api_headers, json=json_request_payload
        )  # Sends the POST request.
        api_response.raise_for_status()  # Raises an exception for HTTP errors.
        response_data = api_response.json()  # Parses the JSON response.
        vehicle_models = response_data.get("payload", {}).get(
            "vehicleModelHU", []
        )  # Safely extracts the list of models.
        logging.info(
            f"SUCCESS: Extracted {len(vehicle_models)} vehicle models."
        )  # Logs the count.
        return vehicle_models  # Returns the list of model dictionaries.
    except (
        requests.exceptions.RequestException
    ) as request_error:  # Catches request-related errors.
        logging.error(
            f"Failed to fetch car model list: {request_error}"
        )  # Logs the error.
        return []  # Returns an empty list on failure.
    except json.JSONDecodeError:  # Catches JSON parsing errors.
        logging.error(
            "Failed to parse JSON response for car models."
        )  # Logs the error.
        return []  # Returns an empty list on failure.


def fetch_manual_access_tokens(  # Renamed function to fetch tokens for a specific model.
    session: requests.Session,
    model_year: int,
    model_name: str,  # Function signature with renamed variables.
) -> list[str]:  # Returns a list of token strings.
    """Queries the Kia Owners API for specific tokens needed to access technical manuals."""  # Docstring for clarity.
    api_headers = {  # Headers for the token retrieval API call.
        "apiurl": "/cmm/gam",  # Custom API path for getting manual access tokens.
        "httpmethod": "POST",  # Request method is POST.
        "servicetype": "preLogin",  # Service type defined by the remote API.
        "Content-Type": "application/json",  # Expecting JSON body.
    }
    json_request_payload = {
        "modelYear": str(model_year),
        "modelName": model_name,
    }  # Payload specifying the desired model/year.
    try:  # Start error handling.
        api_response = session.post(
            OWNERS_API_GATEWAY_URL, headers=api_headers, json=json_request_payload
        )  # Sends the POST request.
        api_response.raise_for_status()  # Checks for HTTP errors.
        response_data = api_response.json()  # Parses the JSON response.
        manual_records = response_data.get("payload", {}).get(
            "automatedManuals", []
        )  # Safely extracts the list of manual records.
        access_token_list = (
            [  # List comprehension to extract only the 'accessPayload' (token).
                record.get("accessPayload")
                for record in manual_records
                if record.get("accessPayload")
            ]
        )
        logging.info(
            f"SUCCESS: Found {len(access_token_list)} technical manual access tokens."
        )  # Logs the number of tokens found.
        return access_token_list  # Returns the list of tokens.
    except (
        requests.exceptions.RequestException
    ) as request_error:  # Catches request-related errors.
        logging.warning(
            f"Failed to fetch manual data for {model_year} {model_name}: {request_error}"
        )  # Logs a warning.
        return []  # Returns empty list on failure.


def establish_technical_session_cookies(
    session: requests.Session,
):  # Renamed function for the critical session refresh step.
    """CRITICAL STEP: Refreshes the session cookies on kiatechinfo.com to get a fresh Anti-CSRF token."""  # Docstring for clarity.
    logging.info(
        f"ATTEMPTING: Establishing persistent session with {TECH_INFO_BASE_DOMAIN}"
    )  # Logs the attempt.
    try:  # Start error handling.
        session_response = session.get(
            TECH_INFO_BASE_DOMAIN, timeout=10
        )  # Performs a simple GET request to refresh cookies.
        session_response.raise_for_status()  # Checks for HTTP errors.
        logging.info(
            "SUCCESS: Session establishment request completed. Cookies are stored."
        )  # Confirms success.
    except (
        requests.exceptions.RequestException
    ) as request_error:  # Catches request errors.
        logging.error(
            f"Failed to establish session with kiatechinfo.com: {request_error}"
        )  # Logs the critical error.


def resolve_pdf_url_from_token(  # Renamed function to execute the token-to-URL exchange.
    session: requests.Session,
    access_token: str,
    model_year: int,
    model_name: str,  # Function signature with renamed variables.
) -> str:  # Returns the full PDF download URL string.
    """Uses the access token to get the HTML wrapper page, then extracts the PDF URL from the page's iframe tag."""  # Docstring for clarity.
    post_data_payload = {
        "token": access_token
    }  # Payload containing the access token, sent as form data.
    try:  # Start error handling.
        html_response = session.post(  # Sends the POST request to the tech site.
            TECH_INFO_TOKEN_EXCHANGE_URL,
            headers=REQUEST_SPOOFING_HEADERS,  # Uses the full spoofing headers.
            data=post_data_payload,  # Passes the token in the form data.
            timeout=10,
        )
        html_response.raise_for_status()  # Checks for HTTP errors.
        page_content = html_response.text  # Gets the HTML content as a string.

        iframe_match = re.search(
            r'<iframe src="([^"]+\.pdf)"', page_content
        )  # Regex to find the PDF URL inside the iframe src attribute.

        if iframe_match:  # Checks if the regex found a match.
            relative_pdf_path = iframe_match.group(
                1
            )  # Extracts the captured relative URL (group 1).
            full_pdf_url = (
                TECH_INFO_BASE_DOMAIN + relative_pdf_path
            )  # Constructs the full URL.
            return full_pdf_url  # Returns the final URL.
        else:  # If no PDF path was found.
            logging.error(
                f"FAILED to extract PDF path (iframe src) for {model_year} {model_name}."
            )  # Logs the regex failure.
            return ""  # Returns an empty string on failure.

    except (
        requests.exceptions.RequestException
    ) as request_error:  # Catches request errors.
        logging.error(
            f"Error sending request for technical info: {request_error}"
        )  # Logs the error.
        return ""  # Returns an empty string on failure.


def execute_model_specific_download(
    session: requests.Session,
):  # Renamed function for the Primary Mode execution loop.
    """Runs the Input 1 logic: Scrape model list, get tokens, extract URL, and download."""  # Docstring for clarity.
    logging.info(
        "\n--- STARTING PRIMARY MODE (Model-Specific Manuals) ---"
    )  # Logs the mode start.
    car_models_list = fetch_all_model_years(
        session
    )  # Fetches the master list of models.
    if not car_models_list:  # Checks for critical failure in fetching the model list.
        logging.critical(
            "Program aborted due to failure to retrieve model list."
        )  # Logs fatal error.
        sys.exit(1)  # Exits the script.

    for car_model in car_models_list:  # Iterates through every model found.
        model_year = car_model.get("modelYear")  # Extracts the model year.
        model_name = car_model.get("modelName")  # Extracts the model name.
        if not model_year or not model_name:  # Skips invalid records.
            continue  # Continue to the next model.

        log_header = f"--- PROCESSING MODEL: Year {model_year}, Name {model_name} ---"  # Creates a clear log header.
        logging.info(f"\n{log_header}")  # Prints the model header.

        access_tokens_list = fetch_manual_access_tokens(
            session, model_year, model_name
        )  # Gets the list of access tokens for the model.
        if not access_tokens_list:  # Checks if any tokens were found.
            logging.warning(
                f"No access tokens found for {model_year} {model_name}. Skipping."
            )  # Logs a warning.
            continue  # Continues to the next model.

        for index, access_token in enumerate(
            access_tokens_list
        ):  # Iterates through each token.
            token_progress = f"Token {index + 1}/{len(access_tokens_list)}"  # String for logging progress.

            establish_technical_session_cookies(
                session
            )  # CRITICAL: Refreshes the session cookies before the token exchange.

            logging.info(
                f"Attempting to get PDF URL ({token_progress})"
            )  # Logs the attempt.

            pdf_download_url = resolve_pdf_url_from_token(
                session, access_token, model_year, model_name
            )  # Exchanges the token for the final PDF URL.

            if pdf_download_url:  # Checks if the PDF URL was successfully extracted.
                # Prepare directory and filename with Input 1 structure
                safe_model_name = (
                    re.sub(r"[^a-zA-Z0-9\s-]", "", model_name).strip().replace(" ", "_")
                )  # Cleans the model name for the directory path.
                output_directory_path = os.path.join(
                    ROOT_DOWNLOAD_DIRECTORY, str(model_year), safe_model_name
                )  # Constructs the hierarchical path.
                os.makedirs(
                    output_directory_path, exist_ok=True
                )  # Creates the nested directory if it doesn't exist.

                base_filename = sanitize_primary_mode_filename(
                    pdf_download_url
                )  # Gets the strictly cleaned filename.
                final_filename_with_index = (
                    f"{index+1:02d}_{base_filename}"  # Adds a two-digit index prefix.
                )
                full_file_path = os.path.join(
                    output_directory_path, final_filename_with_index
                )  # Constructs the final file path.

                download_file_to_disk(
                    session, pdf_download_url, full_file_path
                )  # Executes the file download.
            else:  # If the PDF URL was not extracted.
                logging.error(
                    f"Skipping download for {model_name} ({token_progress}): Failed to extract URL."
                )  # Logs the reason for skipping.


# --- KGIS Mode Functions (Input 2 Logic) ---


def scrape_static_page_html(
    session: requests.Session, target_url: str
) -> str:  # Renamed function for static HTML fetching.
    """Scrapes the static HTML content using the shared session."""  # Docstring for clarity.
    logging.info(f"Scraping static content from: {target_url}")  # Logs the target URL.
    try:  # Start error handling.
        response = session.get(target_url, timeout=15)  # Sends a standard GET request.
        response.raise_for_status()  # Raises an exception for HTTP errors.
        return response.text  # Returns the retrieved static HTML content.
    except (
        requests.exceptions.RequestException
    ) as request_error:  # Catches request errors.
        logging.error(
            f"Error during static scraping of {target_url}: {request_error}"
        )  # Logs the error.
        return ""  # Returns an empty string on failure.


def extract_static_pdf_paths(
    html_content: str,
) -> list[str]:  # Renamed function for regex extraction in KGIS mode.
    """Scans the provided HTML and returns a list of relative PDF file paths (Input 2 Regex)."""  # Docstring for clarity.
    pdf_link_regex = re.compile(
        r"\'(/FileServerRoot[^\']+\.pdf)\'"
    )  # Regex pattern to find relative PDF paths.
    matched_paths = pdf_link_regex.findall(
        html_content
    )  # Finds all matches in the HTML content.
    return matched_paths  # Returns the list of relative paths.


def execute_kgis_static_download(
    session: requests.Session,
):  # Renamed function for the KGIS Mode execution loop.
    """Runs the Input 2 logic: Scrape static KGIS pages and download links."""  # Docstring for clarity.
    logging.info(
        "\n--- STARTING KGIS MODE (Static SnapOn Pages) ---"
    )  # Logs the mode start.
    static_output_directory = os.path.join(
        ROOT_DOWNLOAD_DIRECTORY, "KGIS_Static"
    )  # Defines a specific sub-directory for static downloads.
    os.makedirs(
        static_output_directory, exist_ok=True
    )  # Creates the KGIS_Static directory.

    unique_target_urls = remove_duplicate_items(
        KGIS_STATIC_PAGE_URLS
    )  # Ensures the list of URLs is unique.

    for page_url in unique_target_urls:  # Iterates through each static target URL.
        if is_url_format_valid(page_url):  # Validates the URL format.
            html_content = scrape_static_page_html(
                session, page_url
            )  # Fetches the static HTML content.

            if not html_content:  # Checks if scraping failed.
                logging.error(
                    f"Skipping PDF extraction for {page_url} due to failed scraping."
                )  # Logs the error.
                continue  # Continues to the next URL.

            pdf_relative_paths = extract_static_pdf_paths(
                html_content
            )  # Extracts the relative PDF paths.

            if not pdf_relative_paths:  # Checks if any PDF links were found.
                logging.warning(  # Logs a warning if no links are found.
                    f"No PDF links found for {page_url}. The page is likely dynamic (JavaScript-rendered)."
                )

            for (
                pdf_relative_path
            ) in pdf_relative_paths:  # Iterates through each extracted path.
                full_pdf_url = (
                    KGIS_DOWNLOAD_BASE_URL + pdf_relative_path
                )  # Constructs the full download URL.

                # Prepare filename with Input 2 logic
                safe_filename = create_kgis_safe_filename(
                    full_pdf_url
                )  # Gets the KGIS-specific safe filename.
                full_file_path = os.path.join(
                    static_output_directory, safe_filename
                )  # Constructs the final file path.

                download_file_to_disk(
                    session, full_pdf_url, full_file_path
                )  # Executes the file download.


# --- Main Execution ---


def main():  # The main function to parse arguments and select the mode of execution.
    parser = argparse.ArgumentParser(  # Creates the command-line argument parser.
        description="Kia Technical Manual Downloader with dual modes."  # Sets the script description.
    )
    parser.add_argument(  # Adds the command-line flag.
        "--KGIS",  # The flag name.
        action="store_true",  # Stores True if the flag is present, False otherwise.
        help="Run in KGIS (static page scraping) mode from Input 2.",  # Help text for the flag.
    )
    script_arguments = parser.parse_args()  # Parses the arguments provided by the user.

    with requests.Session() as persistent_session:  # Creates a persistent session object to manage cookies and connections.

        os.makedirs(
            ROOT_DOWNLOAD_DIRECTORY, exist_ok=True
        )  # Ensures the root 'PDFs' directory exists before starting.

        if script_arguments.KGIS:  # Checks if the --KGIS flag was provided.
            execute_kgis_static_download(
                persistent_session
            )  # Runs the KGIS (Input 2) mode.
        else:  # If the --KGIS flag was NOT provided.
            execute_model_specific_download(
                persistent_session
            )  # Runs the Primary (Input 1) mode.

    logging.info("\nPROGRAM COMPLETE. ✅")  # Logs the final completion message.


if __name__ == "__main__":  # Standard Python entry point check.
    main()  # Executes the main function when the script is run.
