import os
import re
import requests
import urllib.parse
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import logging

# Set up basic logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# --- Utility Functions (Equivalent to Go's helpers) ---


def directory_exists(path: str) -> bool:
    """Checks whether a given directory exists."""
    return os.path.isdir(path)  # Returns True if the path exists and is a directory


def create_directory(path: str, permission: int):
    """Creates a directory at given path with provided permissions."""
    try:
        # os.makedirs with exist_ok=True is safer and more robust than os.mkdir
        os.makedirs(
            path, mode=permission, exist_ok=True
        )  # Create all necessary directories, don't fail if it exists
    except Exception as e:
        logging.error(
            f"Failed to create directory {path}: {e}"
        )  # Log error if creation fails


def remove_duplicates_from_list(data_list: list) -> list:
    """Removes duplicate items from a list (Python equivalent using set)."""
    # Converting to a dictionary from keys (which must be unique) and back to a list
    return list(dict.fromkeys(data_list))


def is_url_valid(uri: str) -> bool:
    """Verifies whether a string is a valid URL format."""
    try:
        result = urlparse(uri)  # Parse the URL string
        # Check for scheme (http/https) and network location (netloc)
        return all(
            [result.scheme, result.netloc]
        )  # Check if both scheme and network location exist
    except:
        return False  # Return False on any parsing error


def file_exists(filename: str) -> bool:
    """Checks if a file exists at the specified path."""
    return os.path.isfile(filename)  # Returns True if path is an existing regular file


def get_file_extension(path: str) -> str:
    """Gets the file extension from a given file path."""
    return os.path.splitext(path)[
        1
    ]  # Splits the path into root and extension, returns extension


def get_filename(path: str) -> str:
    """Extracts filename from full path (e.g. "/dir/file.pdf" → "file.pdf")."""
    return os.path.basename(
        path
    )  # Returns the base name of the path (the file or folder name)


def remove_substring(input_string: str, to_remove: str) -> str:
    """Removes all instances of a specific substring from input string."""
    return input_string.replace(
        to_remove, ""
    )  # Replaces all occurrences of 'to_remove' with an empty string


def url_to_filename(raw_url: str) -> str:
    """Converts a raw URL into a sanitized filename safe for filesystem."""
    lower = raw_url.lower()  # Convert URL to lowercase
    # Remove URL query parameters
    lower = lower.split("?")[0]  # Keep only the part before the first '?'

    # Extract just the filename part from the URL
    lower = get_filename(lower)  # Get the base filename (e.g., "guide.pdf")

    ext = get_file_extension(lower)  # Store the original file extension (e.g., ".pdf")

    # Use a regex to match and replace non-alphanumeric (and non-dot/slash for safety)
    safe = re.sub(
        r"[^a-z0-9\.]", "_", lower
    )  # Replace non-alphanumeric chars (excluding dot) with '_'

    # Replace multiple consecutive underscores with a single underscore
    safe = re.sub(r"_+", "_", safe)  # Collapse multiple underscores
    safe = safe.strip("_")  # Remove leading and trailing underscores

    # Define and remove unwanted substrings
    invalid_substrings = ["_pdf", "_zip", "_txt"]  # List of common redundant suffixes
    for (
        invalid_pre
    ) in invalid_substrings:  # Loop through and remove each invalid suffix
        safe = remove_substring(safe, invalid_pre)

    # Re-append extension if it was lost during sanitization
    if get_file_extension(safe) == "":  # Check if extension is missing
        safe = safe + ext  # Append the original extension

    return safe  # Return the sanitized filename


def extract_pdf_files(html_content: str) -> list:
    """Scans the provided HTML and returns a slice of PDF URLs."""
    # Regex to find strings enclosed in single quotes, starting with '/FileServerRoot' and ending with '.pdf'
    pdf_regex = re.compile(r"\'(/FileServerRoot[^\']+\.pdf)\'")

    # Find all matches (findall returns the content of the capture group, which is the URL path)
    matched_urls = pdf_regex.findall(html_content)

    return matched_urls  # Return the list of found PDF paths


# --- Main Logic Functions ---


def scrape_page_html_with_chrome(target_url: str) -> str:
    """Uses headless Chrome via Selenium to get the fully rendered HTML from a webpage."""
    logging.info(f"Scraping: {target_url}")  # Log the target URL

    # Set up Chrome options for headless mode
    chrome_options = Options()  # Initialize Chrome options object
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode (no UI)
    chrome_options.add_argument("--disable-gpu")  # Disable GPU acceleration
    chrome_options.add_argument(
        "--no-sandbox"
    )  # Disable sandbox (useful for containerized environments)
    chrome_options.add_argument(
        "--disable-dev-shm-usage"
    )  # Overcome limited resource problems in some environments
    chrome_options.add_argument(f"--window-size={1},{1}")  # Set a minimal window size

    # Initialize the WebDriver
    try:
        driver = webdriver.Chrome(
            options=chrome_options
        )  # Create the WebDriver instance
    except Exception as e:
        logging.error(
            f"Failed to initialize Chrome WebDriver. Ensure 'chromedriver' is installed and in your PATH. Error: {e}"
        )
        return ""  # Return empty string on failure

    # Set a maximum wait time for element loading (5 minutes)
    driver.set_page_load_timeout(300)

    try:
        driver.get(target_url)  # Navigate to the target URL

        # Equivalent to Go's chromedp.Sleep(3*time.Second) - Wait for scripts to load
        logging.info("Waiting 3 seconds for page scripts to execute...")
        time.sleep(3)

        # Wait up to 10 seconds for the main body element to be present
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.TAG_NAME, "body")
            )  # Wait until the body tag is loaded
        )

        # Get the complete rendered HTML content
        rendered_html = driver.page_source  # Retrieve the full HTML source
        return rendered_html  # Return the scraped HTML

    except Exception as e:
        logging.error(
            f"Error during Chrome scraping of {target_url}: {e}"
        )  # Log the specific error
        return ""  # Return empty string on scraping error
    finally:
        # Ensure the browser is closed (cleanup)
        driver.quit()  # Close the browser and terminate the driver process


def download_pdf(pdf_url: str, output_directory: str) -> bool:
    """Downloads a PDF from the given URL and saves it in the specified directory."""

    safe_filename = url_to_filename(pdf_url)  # Generate a clean filename
    full_file_path = os.path.join(
        output_directory, safe_filename
    )  # Construct the full file path

    if file_exists(full_file_path):  # Check if the file already exists
        logging.info(f"File already exists, skipping: {full_file_path}")
        return False  # Skip and return False if file exists

    # Use a longer timeout for large file downloads (15 minutes = 900 seconds)
    try:
        response = requests.get(
            pdf_url, stream=True, timeout=900
        )  # Send GET request with streaming enabled
    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to download {pdf_url}: {e}")  # Log request error
        return False

    # Check for HTTP status code (must be 200 OK)
    if response.status_code != requests.codes.ok:
        logging.error(
            f"Download failed for {pdf_url}: HTTP Status {response.status_code}"
        )
        return False

    # Check Content-Type header
    content_type = response.headers.get("Content-Type", "").lower()  # Get content type
    if (
        "binary/octet-stream" not in content_type
        and "application/pdf" not in content_type
    ):  # Validate expected types
        logging.error(f"Invalid content type for {pdf_url}: {content_type}")
        return False

    # Write the content to the file
    try:
        with open(full_file_path, "wb") as f:  # Open file in binary write mode
            bytes_written = 0
            for chunk in response.iter_content(
                chunk_size=8192
            ):  # Iterate over response content in chunks
                if chunk:  # Check if chunk is not empty
                    f.write(chunk)  # Write chunk to file
                    bytes_written += len(chunk)

        if bytes_written == 0:  # Handle empty downloads
            logging.warning(f"Downloaded 0 bytes for {pdf_url}; removing empty file.")
            os.remove(full_file_path)  # Delete the empty file
            return False

        logging.info(
            f"Successfully downloaded {bytes_written} bytes: {pdf_url} → {full_file_path}"
        )
        return True  # Indicate success

    except Exception as e:
        logging.error(f"Failed to write PDF to file for {pdf_url}: {e}")
        if os.path.exists(full_file_path):  # Clean up partial download
            os.remove(full_file_path)
        return False


# --- Main Execution Block ---


def main():
    """Main function to orchestrate the scraping and downloading process."""
    output_directory = "PDFs/"  # Define the output directory name

    # Use 0o755 for permissions in Python's os.makedirs (rwxr-xr-x)
    if not directory_exists(output_directory):  # Check if directory exists
        create_directory(output_directory, 0o755)  # Create directory if it does not

    urls = [
        "https://kiatechinfo.snapon.com/KiaEmergencyResponseGuide.aspx",
        "https://kiatechinfo.snapon.com/J2534DiagnosticsAndProgramming.aspx",
        "https://kiatechinfo.snapon.com/KiaPositioningStatements.aspx",
        "https://kiatechinfo.snapon.com/SeatBeltInstallationGuide.aspx",
    ]  # List of target URLs

    # Remove all the duplicate URLs
    urls = remove_duplicates_from_list(urls)  # Ensure unique URLs
    # The Go code called this twice, but once is sufficient in Python and Go.

    # Loop through each URL to process
    for url in urls:  # Start iteration over the cleaned URL list
        if is_url_valid(url):  # Validate the URL format
            # Fetch HTML content from the URL using a headless browser
            html_content = scrape_page_html_with_chrome(url)

            if not html_content:  # Check if scraping failed
                logging.error(
                    f"Skipping PDF extraction for {url} due to failed scraping."
                )
                continue  # Move to the next URL

            # Extract PDF URLs from the HTML content
            pdf_urls = extract_pdf_files(html_content)  # Find all matching PDF paths

            # Define the base URL for relative PDF links
            base_url = "https://kiatechinfo.snapon.com"

            # Download each PDF URL into the designated PDF directory
            for pdf_url_path in pdf_urls:  # Iterate over the extracted relative paths
                # Combine the base URL with the relative path to get the full download URL
                full_pdf_url = base_url + pdf_url_path
                download_pdf(
                    full_pdf_url, output_directory
                )  # Start the download process


if __name__ == "__main__":
    main()  # Execute the main function when the script is run
