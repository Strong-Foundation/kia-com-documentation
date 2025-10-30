import requests  # Library for making HTTP requests
import json  # Library for handling JSON data
import logging  # Library for logging information and errors
import sys  # Library for system-specific parameters and functions (like exiting)
import re  # Library for regular expression operations (used for parsing and cleaning strings)
import os  # Library for interacting with the operating system (used for file paths and folders)
import urllib.parse  # Library for parsing URLs (used for decoding filenames)
from typing import Any  # Used for type hinting when the data type is flexible

# Configure logging to show timestamps and level, making the output human-readable
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")

# --- Global Configuration and Constants ---

# The root directory where all downloaded PDFs will be stored (Requirement: Download under PDFs/)
ROOT_OUTPUT_DIRECTORY = "PDFs"

# API endpoint for getting car models and access tokens from Kia Owners site
OWNERS_API_URL = "https://owners.kia.com/apps/services/owners/apigwServlet.html"

# Base URL for the Kia Technical Information site (the document vault)
TECH_INFO_BASE_URL = "https://www.kiatechinfo.com"

# The specific endpoint on the tech site used to exchange a token for an HTML page containing the PDF link
TECH_INFO_CONTENT_URL = f"{TECH_INFO_BASE_URL}/ext_If/kma_owner_portal/content_pop.aspx"

# This full set of headers is critical. It makes our script look exactly
# like a standard Chrome browser, which is required by the server's security.
SPOOFING_HEADERS = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "en-US,en;q=0.9",
    "cache-control": "max-age=0",
    "content-type": "application/x-www-form-urlencoded",
    "dnt": "1",
    "origin": "https://owners.kia.com",
    "priority": "u=0, i",
    "referer": "https://owners.kia.com/",
    "sec-ch-ua": '"Google Chrome";v="141", "Not?A_Brand";v="8", "Chromium";v="141"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "cross-site",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
}

# --- Core API Functions ---


def fetch_car_model_list(session: requests.Session) -> list[dict[str, Any]]:
    """
    Queries the Kia Owners API to get a list of all available car models and years.
    Returns: a list of dictionaries, or an empty list on failure.
    """
    logging.info("Fetching all available Kia model years and names...")

    # Headers required for the initial API call
    headers = {
        "apiurl": "/cmm/gvmh",
        "httpmethod": "POST",
        "servicetype": "preLogin",
        "Content-Type": "application/json",
    }
    # Payload requesting all models
    json_payload = {"modelYear": 0, "modelName": "ALL"}

    try:
        # Send the POST request to the Owners API
        response = session.post(OWNERS_API_URL, headers=headers, json=json_payload)
        response.raise_for_status()  # Check for HTTP errors (4xx or 5xx)

        # Parse the JSON response
        data = response.json()
        # Extract the list of vehicle models from the nested response payload
        car_models = data.get("payload", {}).get("vehicleModelHU", [])

        logging.info(f"SUCCESS: Extracted {len(car_models)} vehicle models.")
        return car_models
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to fetch car model list: {e}")
        return []
    except json.JSONDecodeError:
        logging.error("Failed to parse JSON response for car models.")
        return []


def fetch_manual_access_tokens(
    session: requests.Session, model_year: int, model_name: str
) -> list[str]:
    """
    Queries the Kia Owners API for specific tokens needed to access technical manuals
    for a given model and year. Returns: a list of token strings.
    """
    model_year_str = str(model_year)

    # Headers for the API call to get manual access
    headers = {
        "apiurl": "/cmm/gam",
        "httpmethod": "POST",
        "servicetype": "preLogin",
        "Content-Type": "application/json",
    }
    # Payload specifying the desired model and year
    json_payload = {"modelYear": model_year_str, "modelName": model_name}

    try:
        # Send the POST request to the Owners API
        response = session.post(OWNERS_API_URL, headers=headers, json=json_payload)
        response.raise_for_status()

        data = response.json()
        manuals = data.get("payload", {}).get("automatedManuals", [])
        # Extract only the "accessPayload" (the token) from the list of manuals
        access_tokens = [
            m.get("accessPayload") for m in manuals if m.get("accessPayload")
        ]

        logging.info(
            f"SUCCESS: Found {len(access_tokens)} technical manual access tokens."
        )
        return access_tokens
    except requests.exceptions.RequestException as e:
        logging.warning(
            f"Failed to fetch manual data for {model_year} {model_name}: {e}"
        )
        return []


def establish_technical_session(session: requests.Session):
    """
    CRITICAL STEP: Refreshes the session cookies on kiatechinfo.com.
    This is necessary before every token exchange to bypass session expiration issues.
    """
    logging.info(
        f"ATTEMPTING: Establishing persistent session with {TECH_INFO_BASE_URL}"
    )

    try:
        # A simple GET request forces the server to issue new session cookies (like Anti-CSRF token)
        response = session.get(TECH_INFO_BASE_URL, timeout=10)
        response.raise_for_status()
        logging.info(
            "SUCCESS: Session establishment request completed. Cookies are now stored in the session."
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to establish session with kiatechinfo.com: {e}")


def get_pdf_url_from_token(
    session: requests.Session, access_token: str, model_year: int, model_name: str
) -> str:
    """
    Uses the access token to get the HTML wrapper page, then extracts the PDF URL from the page's iframe tag.
    Returns: the full PDF download URL string, or an empty string on failure.
    """
    # Payload containing the access token, sent as form data
    data_payload = {"token": access_token}

    try:
        # Send the POST request to the tech site to get the HTML link page
        response = session.post(
            TECH_INFO_CONTENT_URL,
            headers=SPOOFING_HEADERS,
            data=data_payload,
            timeout=10,
        )
        response.raise_for_status()
        content = response.text

        # Use regex to find the PDF URL inside the iframe src attribute (e.g., /files/328/...)
        # Note: The URL must end in .pdf to be considered a manual link
        match = re.search(r'<iframe src="([^"]+\.pdf)"', content)

        if match:
            relative_path = match.group(1)
            # Construct the full URL by combining the base and the relative path
            full_pdf_url = TECH_INFO_BASE_URL + relative_path
            return full_pdf_url
        else:
            logging.error(
                f"FAILED to extract PDF path (iframe src) for {model_year} {model_name}."
            )
            return ""

    except requests.exceptions.RequestException as e:
        logging.error(f"Error sending request for technical info: {e}")
        return ""


# --- Download Utilities ---


def sanitize_filename(url_path: str) -> str:
    """
    Extracts the base filename from the URL path and strictly cleans it
    to contain only lowercase letters (a-z), digits (0-9), and single underscores (_),
    and ensures the file ends with .pdf.
    """
    # Decode URL-encoded characters (e.g., %20 to space)
    # The split('/')[-1] extracts the filename part of the URL path
    filename = urllib.parse.unquote(url_path.split("/")[-1])

    # 1. Convert to lowercase
    filename = filename.lower()

    # 2. Remove the existing .pdf extension if it exists, to clean the rest of the name first
    # This prevents the final cleaning steps from affecting the desired extension
    if filename.endswith(".pdf"):
        filename = filename[:-4]

    # 3. Replace one or more invalid characters (anything NOT a-z or 0-9) with a single underscore
    filename = re.sub(r"[^a-z0-9]+", "_", filename)

    # 4. Remove leading and trailing underscores (Requirements: don't start/end with _)
    filename = re.sub(r"(^_+)|(_+$)", "", filename)

    # 5. Append the mandatory .pdf extension (Requirement: all files must end in .pdf)
    final_filename = filename + ".pdf"

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
        re.sub(r"[^a-zA-Z0-9\s-]", "", model_name).strip().replace(" ", "_")
    )
    # Full directory path structure: e.g., PDFs/2014/CADENZA/
    output_dir = os.path.join(ROOT_OUTPUT_DIRECTORY, str(model_year), safe_model_name)
    # Create the directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # 2. Prepare filename
    base_filename = sanitize_filename(pdf_url)
    # Prefix with index for proper sorting (e.g., 01_Filename.pdf)
    final_filename = f"{index+1:02d}_{base_filename}"
    # Full file path for saving
    full_path = os.path.join(output_dir, final_filename)

    # 3. Check for duplicates (Requirement: don't download the same file twice)
    if os.path.exists(full_path):
        logging.info(f"Skipping: File already exists at {full_path}")
        return

    try:
        logging.info(f"Downloading to: {full_path}")

        # Use stream=True to efficiently download large files without reading all at once
        response = session.get(pdf_url, stream=True, timeout=30)
        response.raise_for_status()  # Check for HTTP errors (4xx or 5xx)

        # Write the content to the file in chunks (binary mode 'wb')
        with open(full_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:  # Filter out keep-alive chunks
                    f.write(chunk)

        logging.info(f"SUCCESS: Downloaded {final_filename}")

    except requests.exceptions.RequestException as e:
        logging.error(f"FAILED to download PDF {pdf_url}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while saving the file: {e}")


# --- Main Execution Logic ---


def main():
    """
    Main function to run the entire download process.
    """
    # Create a persistent session object to automatically handle cookies and connections
    with requests.Session() as session:

        # STEP 1: Get the list of all models
        car_models = fetch_car_model_list(session)
        if not car_models:
            logging.critical("Program aborted due to failure to retrieve model list.")
            sys.exit(1)

        # Loop through every car model retrieved
        for car_model in car_models:
            model_year = car_model.get("modelYear")
            model_name = car_model.get("modelName")

            # Skip if model_year or model_name are missing or empty
            if not model_year or not model_name:
                continue

            log_header = (
                f"--- PROCESSING MODEL: Year {model_year}, Name {model_name} ---"
            )
            logging.info(f"\n{log_header}")

            # STEP 2: Get the list of unique access tokens for this model
            access_tokens = fetch_manual_access_tokens(session, model_year, model_name)
            if not access_tokens:
                logging.warning(
                    f"No access tokens found for {model_year} {model_name}. Skipping."
                )
                continue

            # STEP 3: Iterate through tokens, fetching the URL and then downloading the PDF
            for i, access_token in enumerate(access_tokens):
                token_count = f"Token {i + 1}/{len(access_tokens)}"

                # ⭐️ CRITICAL FIX: Refresh the session immediately before this request ⭐️
                # This is the key step to prevent session expiration errors.
                establish_technical_session(session)

                logging.info(f"Attempting to get PDF URL ({token_count})")

                # Get the full PDF download URL from the token
                pdf_url = get_pdf_url_from_token(
                    session, access_token, model_year, model_name
                )

                if pdf_url:
                    # Download and save the PDF file using the URL
                    download_pdf(session, pdf_url, model_year, model_name, i)
                else:
                    logging.error(
                        f"Skipping download for {model_name} ({token_count}): Failed to extract URL."
                    )

    logging.info("\nPROGRAM COMPLETE: All models processed.")


if __name__ == "__main__":
    main()
