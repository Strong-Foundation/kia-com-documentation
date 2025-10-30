import requests  # Imports the requests library for making HTTP requests.
import json  # Imports the json library for working with JSON data structures.
import logging  # Imports the logging module for standardized output messages.
import sys  # Imports the sys module to interact with the Python interpreter.
import re  # Imports the re module for regular expression operations.
import os  # Imports the os module for interacting with the operating system (e.g., file paths).
import urllib.parse  # Imports the urllib.parse module for parsing and manipulating URLs.
from typing import Any  # Imports the Any type from typing for flexible type hints.

# Configure logging to show timestamps and level for better traceability
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
)  # Sets up the logger format and INFO level.

# --- Global Configuration and Constants ---

# The root directory where all downloaded PDF manuals will be saved
PDF_OUTPUT_ROOT_DIRECTORY = (
    "PDFs"  # Defines the top-level directory name for saved files.
)

# API endpoint for model data and access tokens on the Kia Owners site
KIA_OWNERS_API_ENDPOINT = "https://owners.kia.com/apps/services/owners/apigwServlet.html"  # URL for the owners API gateway.

# Base URL for the technical document vault (kiatechinfo.com)
KIA_TECHNICAL_BASE_URL = (
    "https://www.kiatechinfo.com"  # Base URL for the technical document website.
)

# Endpoint used to exchange the token for the HTML page containing the final PDF link
TOKEN_EXCHANGE_CONTENT_URL = f"{KIA_TECHNICAL_BASE_URL}/ext_If/kma_owner_portal/content_pop.aspx"  # Full URL for the token exchange endpoint.

# Essential headers to mimic a web browser and ensure cross-site token access is granted
BROWSER_SPOOFING_HEADERS = {  # Starts the dictionary of HTTP headers.
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # Standard Accept header.
    "accept-language": "en-US,en;q=0.9",  # Standard Accept-Language header.
    "cache-control": "max-age=0",  # Request to bypass cache.
    "content-type": "application/x-www-form-urlencoded",  # Critical for POST data formatting.
    "dnt": "1",  # Do Not Track header.
    "origin": "https://owners.kia.com",  # Specifies the origin for cross-site requests.
    "referer": "https://owners.kia.com/",  # Critical: Spoofing the referring site is essential.
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',  # Client-Hint header for browser brands.
    "sec-fetch-dest": "document",  # Fetch metadata header.
    "sec-fetch-mode": "navigate",  # Fetch metadata header.
    "sec-fetch-site": "cross-site",  # Fetch metadata header, necessary for this interaction.
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",  # CRITICAL: Spoofs the User-Agent string.
}  # Ends the dictionary of HTTP headers.

# --- Core API Functions ---


def retrieve_all_kia_models(
    session: requests.Session,
) -> list[dict[str, Any]]:  # Function signature for retrieving all models.
    """# Start of docstring.
    Queries the Owners API to get a comprehensive list of all available Kia car models and years. # Docstring line 1.
    Returns: a list of dictionaries, each containing 'modelYear' and 'modelName'. # Docstring line 2.
    """  # End of docstring.
    logging.info(
        "Retrieving all available Kia model years and names..."
    )  # Logs the start of the model fetch process.

    # API-specific headers and payload configured to request ALL models
    api_headers = {  # Defines headers for the model list API call.
        "apiurl": "/cmm/gvmh",  # API-specific path for getting model data.
        "httpmethod": "POST",  # Specifies the HTTP method.
        "servicetype": "preLogin",  # Specifies the service type.
        "Content-Type": "application/json",  # Specifies the content type for the request body.
    }  # Ends the API headers dictionary.
    # Using wildcards (0 for year, ALL for name) to get the full catalog
    request_payload = {
        "modelYear": 0,
        "modelName": "ALL",
    }  # Payload requesting all models.

    try:  # Start of try block for API request.
        response = session.post(
            KIA_OWNERS_API_ENDPOINT, headers=api_headers, json=request_payload
        )  # Sends the POST request to the Owners API.
        response.raise_for_status()  # Checks for HTTP error status codes (4xx or 5xx).

        response_data = response.json()  # Parses the successful response body as JSON.
        # Safely extract the list of vehicle models from the nested JSON
        all_models = response_data.get("payload", {}).get(
            "vehicleModelHU", []
        )  # Safely retrieves the list of models using dictionary methods.

        logging.info(
            f"SUCCESS: Extracted {len(all_models)} distinct vehicle models."
        )  # Logs success and the count of models.
        return all_models  # Returns the list of model dictionaries.
    except (
        requests.exceptions.RequestException
    ) as error:  # Catches all request-related errors.
        logging.error(
            f"Failed to retrieve model list from API: {error}"
        )  # Logs the request error.
        return []  # Returns an empty list on request failure.
    except json.JSONDecodeError:  # Catches errors during JSON parsing.
        logging.error(
            "Failed to parse JSON response for model list."
        )  # Logs the JSON decoding error.
        return []  # Returns an empty list on JSON failure.


def get_manual_access_tokens(  # Function signature for getting access tokens.
    session: requests.Session,
    model_year: int,
    model_name: str,  # Accepts session, model year, and model name.
) -> list[str]:  # Returns a list of strings (tokens).
    """# Start of docstring.
    Queries the Owners API for the unique access tokens required to retrieve technical manuals # Docstring line 1.
    for a specific vehicle model and year. # Docstring line 2.
    Returns: a list of access token strings. # Docstring line 3.
    """  # End of docstring.
    year_string = str(
        model_year
    )  # Converts the integer year to a string for the payload.

    # API-specific headers and payload for the token request
    api_headers = {  # Defines headers for the access token API call.
        "apiurl": "/cmm/gam",  # API-specific path for getting automated manuals.
        "httpmethod": "POST",  # Specifies the HTTP method.
        "servicetype": "preLogin",  # Specifies the service type.
        "Content-Type": "application/json",  # Specifies the content type.
    }  # Ends the API headers dictionary.
    request_payload = {
        "modelYear": year_string,
        "modelName": model_name,
    }  # Payload for the specific model.

    try:  # Start of try block.
        response = session.post(
            KIA_OWNERS_API_ENDPOINT, headers=api_headers, json=request_payload
        )  # Sends the POST request.
        response.raise_for_status()  # Checks for HTTP errors.

        response_data = response.json()  # Parses the response as JSON.
        manual_entries = response_data.get("payload", {}).get(
            "automatedManuals", []
        )  # Retrieves the list of manual entries.

        # Extract only the 'accessPayload' (token) from each manual entry dictionary
        access_tokens = [  # Starts list comprehension to extract tokens.
            entry.get("accessPayload")  # Gets the token value.
            for entry in manual_entries
            if entry.get(
                "accessPayload"
            )  # Iterates and filters out entries without a token.
        ]  # Ends list comprehension.

        logging.info(  # Logs the count of found tokens.
            f"SUCCESS: Found {len(access_tokens)} technical manual access tokens."
        )  # Continuation of log message.
        return access_tokens  # Returns the list of tokens.
    except requests.exceptions.RequestException as error:  # Catches request errors.
        logging.warning(  # Logs a warning on failure.
            f"Failed to get manual data for {model_year} {model_name}: {error}"
        )  # Continuation of log message.
        return []  # Returns an empty list on failure.


def refresh_technical_website_session(
    session: requests.Session,
):  # Function signature for refreshing the session.
    """# Start of docstring.
    Refreshes the session cookies on the Kia Technical Info site (kiatechinfo.com). # Docstring line 1.
    This is a critical step before exchanging a new token to prevent stale session errors. # Docstring line 2.
    """  # End of docstring.
    logging.info(  # Logs the intent to refresh the session.
        f"ATTEMPTING: Establishing persistent session with {KIA_TECHNICAL_BASE_URL}"
    )  # Continuation of log message.

    try:  # Start of try block.
        # A simple GET request forces the server to issue new session cookies
        session.get(
            KIA_TECHNICAL_BASE_URL, timeout=10
        ).raise_for_status()  # Performs a GET request and checks for errors.
        logging.info(  # Logs success.
            "SUCCESS: Technical website session completed and cookies refreshed."
        )  # Continuation of log message.
    except requests.exceptions.RequestException as error:  # Catches request errors.
        logging.error(
            f"Failed to establish session with kiatechinfo.com: {error}"
        )  # Logs the error.


def extract_pdf_url_from_token_page(  # Function signature for token-to-URL extraction.
    session: requests.Session,
    access_token: str,
    model_year: int,
    model_name: str,  # Accepts session, token, year, and name.
) -> str:  # Returns the PDF URL string.
    """# Start of docstring.
    Performs the token exchange. Posts the access token to get an HTML page, # Docstring line 1.
    then extracts the final PDF download URL from the page's <iframe> source attribute. # Docstring line 2.
    Returns: the full PDF download URL string, or an empty string on failure. # Docstring line 3.
    """  # End of docstring.
    # The token is sent as form data
    data_to_send = {"token": access_token}  # Creates the payload with the access token.

    try:  # Start of try block.
        # Send the POST request to exchange the token for the HTML link page
        response = session.post(  # Sends the POST request to the technical content URL.
            TOKEN_EXCHANGE_CONTENT_URL,  # The target URL.
            headers=BROWSER_SPOOFING_HEADERS,  # Uses the spoofing headers.
            data=data_to_send,  # Sends the token data.
            timeout=10,  # Sets a timeout.
        )  # Ends the session.post call.
        response.raise_for_status()  # Checks for HTTP errors.
        page_content = response.text  # Gets the HTML content as a string.

        # Use a regular expression to find the PDF URL inside the iframe src attribute
        url_match = re.search(
            r'<iframe src="([^"]+\.pdf)"', page_content
        )  # Searches for the iframe src ending in .pdf.

        if url_match:  # Checks if the regex found a match.
            relative_path = url_match.group(
                1
            )  # Extracts the relative URL path (group 1).
            # Combine the base URL with the relative path to get the full link
            full_pdf_url = (
                KIA_TECHNICAL_BASE_URL + relative_path
            )  # Constructs the final absolute URL.
            return full_pdf_url  # Returns the final URL.
        else:  # If no match was found.
            logging.error(  # Logs an error for extraction failure.
                f"FAILED to extract PDF link (iframe src) for {model_year} {model_name}."
            )  # Continuation of log message.
            return ""  # Returns an empty string on failure.

    except requests.exceptions.RequestException as error:  # Catches request errors.
        logging.error(
            f"Error during technical info request: {error}"
        )  # Logs the request error.
        return ""  # Returns an empty string on failure.


# --- Download and File Management Utilities ---


def create_safe_filename_from_url(
    url_path: str,
) -> str:  # Function signature for filename sanitization.
    """# Start of docstring.
    Takes a URL path, extracts the filename, decodes it, and cleans it strictly # Docstring line 1.
    to ensure it is a safe, compliant name for all filesystems. # Docstring line 2.
    """  # End of docstring.
    # 1. Decode URL encoding (%20 to space) and get the last path segment
    filename_segment = urllib.parse.unquote(
        url_path.split("/")[-1]
    ).lower()  # Decodes URL and takes the last path segment, converting to lowercase.

    # 2. Remove the existing .pdf extension
    if filename_segment.endswith(".pdf"):  # Checks for the .pdf suffix.
        filename_segment = filename_segment[:-4]  # Removes the last 4 characters.

    # 3. Replace all invalid characters (anything NOT a-z or 0-9) with a single underscore
    filename_segment = re.sub(
        r"[^a-z0-9]+", "_", filename_segment
    )  # Replaces non-alphanumeric chars with an underscore.

    # 4. Remove any leading or trailing underscores
    filename_segment = re.sub(
        r"(^_+)|(_+$)", "", filename_segment
    )  # Removes leading/trailing underscores.

    # 5. Append the mandatory .pdf extension
    return (
        filename_segment + ".pdf"
    )  # Returns the final, sanitized filename with extension.


def save_manual_pdf_to_disk(  # Function signature for downloading and saving the PDF.
    session: requests.Session,  # Accepts the session object.
    pdf_download_url: str,  # Accepts the PDF download URL.
    model_year: int,  # Accepts the model year.
    model_name: str,  # Accepts the model name.
    manual_index: int,  # Accepts the index for file ordering.
):  # Returns nothing.
    """# Start of docstring.
    Downloads the PDF manual from the given URL and saves it to a structured directory # Docstring line 1.
    on the local disk, skipping the download if the file already exists. # Docstring line 2.
    """  # End of docstring.

    # 1. Prepare output path: PDFs/[Year]/[SafeModelName]/
    # Create a safe, filesystem-friendly version of the model name
    safe_model_directory_name = (
        re.sub(r"[^a-zA-Z0-9\s-]", "", model_name).strip().replace(" ", "_")
    )  # Creates a clean directory name from the model name.

    # Construct the full path: e.g., PDFs/2014/CADENZA/
    output_directory_path = os.path.join(
        PDF_OUTPUT_ROOT_DIRECTORY, str(model_year), safe_model_directory_name
    )  # Constructs the full directory path.
    os.makedirs(
        output_directory_path, exist_ok=True
    )  # Creates the directory structure if it doesn't exist.

    # 2. Prepare filename (e.g., 01_owner_manual.pdf)
    base_safe_filename = create_safe_filename_from_url(
        pdf_download_url
    )  # Sanitizes the filename using the utility function.
    final_file_name = f"{manual_index+1:02d}_{base_safe_filename}"  # Prepends a zero-padded index for sorting.
    full_file_path = os.path.join(
        output_directory_path, final_file_name
    )  # Constructs the complete file path.

    # 3. Check for duplicates and skip if found
    if os.path.exists(full_file_path):  # Checks if the file already exists.
        logging.info(
            f"Skipping: File already exists at {full_file_path}"
        )  # Logs that the file is being skipped.
        return  # Exits the function.

    try:  # Start of try block for file download and writing.
        logging.info(f"Downloading to: {full_file_path}")  # Logs the target file path.

        # Stream the download for memory efficiency with large files
        response = session.get(
            pdf_download_url, stream=True, timeout=30
        )  # Starts the GET request in stream mode.
        response.raise_for_status()  # Checks for HTTP errors.

        # Write the content to the file in chunks
        with open(
            full_file_path, "wb"
        ) as output_file:  # Opens the file for writing in binary mode.
            for data_chunk in response.iter_content(
                chunk_size=8192
            ):  # Iterates through the response content in 8KB chunks.
                if data_chunk:  # Ensures the chunk is not empty.
                    output_file.write(data_chunk)  # Writes the data chunk to the file.

        logging.info(
            f"SUCCESS: Downloaded {final_file_name}"
        )  # Logs successful download.

    except (
        requests.exceptions.RequestException
    ) as error:  # Catches request errors during download.
        logging.error(
            f"FAILED to download PDF from {pdf_download_url}: {error}"
        )  # Logs the download failure.
    except Exception as error:  # Catches general exceptions (e.g., file system errors).
        logging.error(
            f"An unexpected error occurred while saving the file: {error}"
        )  # Logs the general error.


# --- Main Execution Logic ---


def main_download_process():  # The main function that controls the script execution.
    """# Start of docstring.
    The main orchestration function for the entire download script. # Docstring line 1.
    It manages the three primary steps: model list retrieval, token acquisition, # Docstring line 2.
    and manual PDF download for all available vehicles. # Docstring line 3.
    """  # End of docstring.
    # Use a persistent session to maintain cookies and connection pooling
    with requests.Session() as http_session:  # Creates a persistent requests session object.

        # STEP 1: Get the list of all models
        all_kia_models = retrieve_all_kia_models(
            http_session
        )  # Calls the function to get all models.

        if not all_kia_models:  # Checks if the model list is empty.
            logging.critical(
                "Program aborted due to failure to retrieve the complete model list."
            )  # Logs a critical error.
            sys.exit(1)  # Exits the program with error code 1.

        logging.info(
            "Starting full download process for all available models."
        )  # Logs the start of the main processing loop.

        # Loop through every car model retrieved from the API
        for (
            car_model
        ) in all_kia_models:  # Starts the loop through all retrieved models.
            model_year = car_model.get("modelYear")  # Extracts the model year.
            model_name = car_model.get("modelName")  # Extracts the model name.

            # Simple validation check
            if not model_year or not model_name:  # Skips if required data is missing.
                continue  # Jumps to the next iteration.

            log_header = f"--- PROCESSING MODEL: Year {model_year}, Name {model_name} ---"  # Creates a formatted log header.  # Continuation of log header.
            logging.info(f"\n{log_header}")  # Prints the formatted log header.

            # STEP 2: Get the list of unique access tokens for this model
            access_tokens = get_manual_access_tokens(
                http_session, model_year, model_name
            )  # Calls the function to get tokens.
            if not access_tokens:  # Checks if any tokens were found.
                logging.warning(  # Logs a warning if no tokens are present.
                    f"No access tokens found for {model_year} {model_name}. Skipping this model."
                )  # Continuation of log message.
                continue  # Skips to the next car model.

            # STEP 3: Iterate through tokens, fetching the URL and then downloading the PDF
            for manual_index, token in enumerate(
                access_tokens
            ):  # Starts the loop through the tokens.
                token_progress_info = f"Token {manual_index + 1}/{len(access_tokens)}"  # String for progress tracking.

                # IMPORTANT: Refresh the session before the token exchange request
                refresh_technical_website_session(
                    http_session
                )  # Calls the critical session refresh function.

                logging.info(
                    f"Attempting to get PDF URL ({token_progress_info})"
                )  # Logs the attempt.

                # Get the full PDF download URL from the token
                pdf_download_url = extract_pdf_url_from_token_page(  # Calls the function to get the PDF URL.
                    http_session,  # Passes the session.
                    token,  # Passes the current token.
                    model_year,  # Passes the year.
                    model_name,  # Passes the name.
                )  # Ends the function call.

                if pdf_download_url:  # Checks if a valid URL was returned.
                    # Download and save the PDF file
                    save_manual_pdf_to_disk(
                        http_session,
                        pdf_download_url,
                        model_year,
                        model_name,
                        manual_index,
                    )  # Calls the download function.
                else:  # If the URL was not found.
                    logging.error(  # Logs an error for the skipped download.
                        f"Skipping download for {model_name} ({token_progress_info}): Failed to extract URL."
                    )  # Continuation of log message.

    logging.info(
        "\nPROGRAM COMPLETE: All models processed. ✅"
    )  # Logs the final completion message.


if __name__ == "__main__":  # Standard Python entry point check.
    main_download_process()  # Calls the main execution function.
