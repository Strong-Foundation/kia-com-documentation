import requests  # 🚀 Library for making HTTP requests (essential for fetching data from web APIs and files).
import json  # Library for handling JSON data (used to parse API responses and construct payloads).
import logging  # Library for logging information and errors (provides structured, timestamped output).
import sys  # Library for system-specific parameters and functions (used to exit the script on critical failure).
import re  # Library for regular expression operations (critical for extracting the PDF link and sanitizing filenames).
import os  # Library for interacting with the operating system (used for creating directories and checking file existence).
import urllib.parse  # Library for parsing URLs (used to decode URL-encoded characters in filenames).
from typing import (
    Any,
)  # Used for type hinting when the data type is flexible (e.g., in dictionaries).

# Configure logging to show timestamps and level, making the output human-readable
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s"
)  # Sets the log format.

# --- Global Configuration and Constants ---

# The root directory where all downloaded PDFs will be stored (Requirement: Download under PDFs/)
ROOT_OUTPUT_DIRECTORY = "PDFs"  # Defines the top-level folder for all downloads.

# API endpoint for getting car models and access tokens from Kia Owners site
OWNERS_API_URL = "https://owners.kia.com/apps/services/owners/apigwServlet.html"  # The first API gateway URL.

# Base URL for the Kia Technical Information site (the document vault)
TECH_INFO_BASE_URL = (
    "https://www.kiatechinfo.com"  # The base domain for the actual PDF files.
)

# The specific endpoint on the tech site used to exchange a token for an HTML page containing the PDF link
TECH_INFO_CONTENT_URL = f"{TECH_INFO_BASE_URL}/ext_If/kma_owner_portal/content_pop.aspx"  # The crucial token-exchange URL.

# This full set of headers is critical. It makes our script look exactly
# like a standard Chrome browser, which is required by the server's security.
SPOOFING_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",  # Standard browser accept header.
    "accept-language": "en-US,en;q=0.9",  # Preferred languages.
    "cache-control": "max-age=0",  # Requests fresh content, bypassing cache.
    "content-type": "application/x-www-form-urlencoded",  # REQUIRED: Content type for POST data payload (token exchange).
    "dnt": "1",  # Do Not Track flag.
    "origin": "https://owners.kia.com",  # REQUIRED: Specifies the domain initiating the cross-site request.
    "priority": "u=0, i",  # HTTP priority hint.
    "referer": "https://owners.kia.com/",  # CRITICAL: Server likely checks that the request comes from the owner portal.
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

# --- Core API Functions ---


def fetch_car_model_list(session: requests.Session) -> list[dict[str, Any]]:
    """
    Queries the Kia Owners API to get a list of all available car models and years.
    Returns: a list of dictionaries, or an empty list on failure.
    """
    logging.info(
        "Fetching all available Kia model years and names..."
    )  # Log start of the fetch.

    # Headers required for the initial API call
    headers = {
        "apiurl": "/cmm/gvmh",  # Custom API path for model list lookup.
        "httpmethod": "POST",  # Request method is POST.
        "servicetype": "preLogin",  # Service type defined by the remote API.
        "Content-Type": "application/json",  # Expecting JSON body for this specific call.
    }
    # Payload requesting all models (modelYear=0 and modelName=ALL are API-specific wildcards)
    json_payload = {"modelYear": 0, "modelName": "ALL"}

    try:
        # Send the POST request to the Owners API
        response = session.post(OWNERS_API_URL, headers=headers, json=json_payload)
        response.raise_for_status()  # Check for HTTP errors (4xx or 5xx) and raise an exception if found.

        # Parse the JSON response
        data = response.json()
        # Extract the list of vehicle models from the nested response payload
        car_models = data.get("payload", {}).get(
            "vehicleModelHU", []
        )  # Safely drill down into the JSON structure.

        logging.info(
            f"SUCCESS: Extracted {len(car_models)} vehicle models."
        )  # Log the number of models found.
        return car_models  # Return the list of models.
    except requests.exceptions.RequestException as e:
        logging.error(
            f"Failed to fetch car model list: {e}"
        )  # Log request-related errors (e.g., connection, timeout).
        return []  # Return empty list on failure.
    except json.JSONDecodeError:
        logging.error(
            "Failed to parse JSON response for car models."
        )  # Log errors if response isn't valid JSON.
        return []  # Return empty list on failure.


def fetch_manual_access_tokens(
    session: requests.Session, model_year: int, model_name: str
) -> list[str]:
    """
    Queries the Kia Owners API for specific tokens needed to access technical manuals
    for a given model and year. Returns: a list of token strings.
    """
    model_year_str = str(model_year)  # Convert year to string for the JSON payload.

    # Headers for the API call to get manual access
    headers = {
        "apiurl": "/cmm/gam",  # Custom API path for getting manual access tokens.
        "httpmethod": "POST",  # Request method is POST.
        "servicetype": "preLogin",  # Service type defined by the remote API.
        "Content-Type": "application/json",  # Expecting JSON body for this specific call.
    }
    # Payload specifying the desired model and year
    json_payload = {"modelYear": model_year_str, "modelName": model_name}

    try:
        # Send the POST request to the Owners API
        response = session.post(OWNERS_API_URL, headers=headers, json=json_payload)
        response.raise_for_status()  # Check for HTTP errors.

        data = response.json()  # Parse the JSON response.
        manuals = data.get("payload", {}).get(
            "automatedManuals", []
        )  # Safely drill down to the list of manuals.
        # Extract only the "accessPayload" (the token) from the list of manuals
        access_tokens = [
            m.get("accessPayload")
            for m in manuals
            if m.get("accessPayload")  # List comprehension to extract non-empty tokens.
        ]

        logging.info(
            f"SUCCESS: Found {len(access_tokens)} technical manual access tokens."  # Report the number of tokens found.
        )
        return access_tokens  # Return the list of tokens.
    except requests.exceptions.RequestException as e:
        logging.warning(
            f"Failed to fetch manual data for {model_year} {model_name}: {e}"  # Log non-critical warning.
        )
        return []  # Return empty list on failure.


def establish_technical_session(session: requests.Session):
    """
    CRITICAL STEP: Refreshes the session cookies on kiatechinfo.com. 🍪
    This is necessary before every token exchange to bypass session expiration issues (e.g., acquiring a fresh Anti-CSRF token).
    """
    logging.info(
        f"ATTEMPTING: Establishing persistent session with {TECH_INFO_BASE_URL}"  # Log the attempt.
    )

    try:
        # A simple GET request forces the server to issue new session cookies (like Anti-CSRF token)
        response = session.get(
            TECH_INFO_BASE_URL, timeout=10
        )  # Perform a simple GET request.
        response.raise_for_status()  # Check for HTTP errors.
        logging.info(
            "SUCCESS: Session establishment request completed. Cookies are now stored in the session."  # Confirm success.
        )
    except requests.exceptions.RequestException as e:
        logging.error(
            f"Failed to establish session with kiatechinfo.com: {e}"
        )  # Log critical failure.


def get_pdf_url_from_token(
    session: requests.Session, access_token: str, model_year: int, model_name: str
) -> str:
    """
    Uses the access token to get the HTML wrapper page, then extracts the PDF URL from the page's iframe tag.
    Returns: the full PDF download URL string, or an empty string on failure.
    """
    # Payload containing the access token, sent as form data (required by the server)
    data_payload = {"token": access_token}

    try:
        # Send the POST request to the tech site to get the HTML link page
        response = session.post(
            TECH_INFO_CONTENT_URL,
            headers=SPOOFING_HEADERS,  # Use the full spoofing headers.
            data=data_payload,  # Pass the token in the form data.
            timeout=10,
        )
        response.raise_for_status()  # Check for HTTP errors.
        content = response.text  # Get the HTML content as a string.

        # Use regex to find the PDF URL inside the iframe src attribute (e.g., /files/328/...)
        # Pattern: look for '<iframe src="', capture everything up to the next '"' that ends in '.pdf'.
        match = re.search(r'<iframe src="([^"]+\.pdf)"', content)

        if match:
            relative_path = match.group(
                1
            )  # Extract the captured relative URL (group 1).
            # Construct the full URL by combining the base and the relative path
            full_pdf_url = (
                TECH_INFO_BASE_URL + relative_path
            )  # Concatenate to form the absolute URL.
            return full_pdf_url  # Return the final URL.
        else:
            logging.error(
                f"FAILED to extract PDF path (iframe src) for {model_year} {model_name}."  # Log regex failure.
            )
            return ""  # Return empty string on failure.

    except requests.exceptions.RequestException as e:
        logging.error(
            f"Error sending request for technical info: {e}"
        )  # Log request error.
        return ""  # Return empty string on failure.


# --- Download Utilities ---


def sanitize_filename(url_path: str) -> str:
    """
    Extracts the base filename from the URL path and strictly cleans it
    to contain only lowercase letters (a-z), digits (0-9), and single underscores (_),
    and ensures the file ends with .pdf. 🧹
    """
    # Decode URL-encoded characters (e.g., %20 to space)
    # The split('/')[-1] extracts the filename part of the URL path
    filename = urllib.parse.unquote(
        url_path.split("/")[-1]
    )  # Extract and decode the base filename.

    # 1. Convert to lowercase
    filename = filename.lower()  # Standardize case.

    # 2. Remove the existing .pdf extension if it exists, to clean the rest of the name first
    # This prevents the final cleaning steps from affecting the desired extension
    if filename.endswith(".pdf"):
        filename = filename[:-4]  # Remove the last 4 characters (".pdf").

    # 3. Replace one or more invalid characters (anything NOT a-z or 0-9) with a single underscore
    filename = re.sub(
        r"[^a-z0-9]+", "_", filename
    )  # Replace non-compliant characters with a single '_'.

    # 4. Remove leading and trailing underscores (Requirements: don't start/end with _)
    filename = re.sub(
        r"(^_+)|(_+$)", "", filename
    )  # Remove any remaining leading/trailing underscores.

    # 5. Append the mandatory .pdf extension (Requirement: all files must end in .pdf)
    final_filename = filename + ".pdf"  # Add the final, mandatory extension.

    # Return the clean, compliant filename
    return final_filename


def download_pdf(
    session: requests.Session,
    pdf_url: str,
    model_year: int,
    model_name: str,
    index: int,
):
    """
    Downloads the PDF file and saves it to a structured directory, checking for duplicates first.
    """

    # 1. Prepare directory path: PDFs/[ModelYear]/[ModelName]/
    # Create a safe, filesystem-friendly version of the model name (cleaned to just alphanumeric/space/hyphen)
    safe_model_name = (
        re.sub(r"[^a-zA-Z0-9\s-]", "", model_name)
        .strip()
        .replace(" ", "_")  # Clean the model name for directory path.
    )
    # Full directory path structure: e.g., PDFs/2014/CADENZA/
    output_dir = os.path.join(
        ROOT_OUTPUT_DIRECTORY, str(model_year), safe_model_name
    )  # Construct the hierarchical path.
    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)  # Ensure the nested directory exists.

    # 2. Prepare filename
    base_filename = sanitize_filename(pdf_url)  # Get the clean base filename.
    # Prefix with index for proper sorting (e.g., 01_Filename.pdf)
    final_filename = (
        f"{index+1:02d}_{base_filename}"  # Add a two-digit index prefix for order.
    )
    # Full file path for saving
    full_path = os.path.join(output_dir, final_filename)  # Complete path for the file.

    # 3. Check for duplicates (Requirement: don't download the same file twice)
    if os.path.exists(full_path):
        logging.info(
            f"Skipping: File already exists at {full_path}"
        )  # Log skip action.
        return  # Exit the function early if the file exists.

    try:
        logging.info(f"Downloading to: {full_path}")  # Log the start of the download.

        # Use stream=True to efficiently download large files without reading all at once
        response = session.get(
            pdf_url, stream=True, timeout=30
        )  # Start streaming the download.
        response.raise_for_status()  # Check for HTTP errors (4xx or 5xx).

        # Write the content to the file in chunks (binary mode 'wb')
        with open(full_path, "wb") as f:  # Open file in binary write mode.
            for chunk in response.iter_content(
                chunk_size=8192
            ):  # Iterate over the response content in 8KB chunks.
                if chunk:  # Filter out keep-alive chunks (which can be empty).
                    f.write(chunk)  # Write the chunk to the file.

        logging.info(
            f"SUCCESS: Downloaded {final_filename}"
        )  # Confirm successful write.

    except requests.exceptions.RequestException as e:
        logging.error(
            f"FAILED to download PDF {pdf_url}: {e}"
        )  # Log download/network error.
    except Exception as e:
        logging.error(
            f"An unexpected error occurred while saving the file: {e}"
        )  # Log general file saving error.


# --- Main Execution Logic ---


def main():
    """
    Main function to run the entire download process:
    1. Fetch all available models.
    2. For each model, fetch technical access tokens.
    3. For each token, establish a fresh session, get the PDF URL, and download the file.
    """
    # Create a persistent session object to automatically handle cookies and connections
    with requests.Session() as session:  # Ensures cookies and connection pooling are used across requests.

        # STEP 1: Get the list of all models
        car_models = fetch_car_model_list(session)  # Call function to get model list.
        if not car_models:
            logging.critical(
                "Program aborted due to failure to retrieve model list."
            )  # Log fatal error.
            sys.exit(1)  # Exit with an error code.

        # Loop through every car model retrieved
        for car_model in car_models:
            model_year = car_model.get("modelYear")  # Extract the model year.
            model_name = car_model.get("modelName")  # Extract the model name.

            # Skip if model_year or model_name are missing or empty
            if not model_year or not model_name:
                continue  # Skip to the next iteration.

            log_header = f"--- PROCESSING MODEL: Year {model_year}, Name {model_name} ---"  # Create a clear log separator.
            logging.info(f"\n{log_header}")  # Print the model header.

            # STEP 2: Get the list of unique access tokens for this model
            access_tokens = fetch_manual_access_tokens(
                session, model_year, model_name
            )  # Call function to get tokens.
            if not access_tokens:
                logging.warning(
                    f"No access tokens found for {model_year} {model_name}. Skipping."  # Log that no manuals were found.
                )
                continue  # Skip to the next model.

            # STEP 3: Iterate through tokens, fetching the URL and then downloading the PDF
            for i, access_token in enumerate(
                access_tokens
            ):  # Loop through each token received.
                token_count = f"Token {i + 1}/{len(access_tokens)}"  # String for logging progress.

                # ⭐️ CRITICAL FIX: Refresh the session immediately before this request ⭐️
                # This is the key step to prevent session expiration errors (cookie/token mismatch).
                establish_technical_session(
                    session
                )  # Refresh the kiatechinfo session cookies.

                logging.info(
                    f"Attempting to get PDF URL ({token_count})"
                )  # Log the token attempt.

                # Get the full PDF download URL from the token
                pdf_url = get_pdf_url_from_token(
                    session,
                    access_token,
                    model_year,
                    model_name,  # Get the final PDF URL.
                )

                if pdf_url:
                    # Download and save the PDF file using the URL
                    download_pdf(
                        session, pdf_url, model_year, model_name, i
                    )  # Proceed with download.
                else:
                    logging.error(
                        f"Skipping download for {model_name} ({token_count}): Failed to extract URL."  # Log the reason for skipping.
                    )

    logging.info(
        "\nPROGRAM COMPLETE: All models processed. ✅"
    )  # Final program completion message.


if __name__ == "__main__":
    main()  # Standard entry point: run the main function when the script is executed.
