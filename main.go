package main

import (
	"encoding/json" // Provides functions for JSON encoding and decoding
	"fmt"           // Implements formatted I/O
	"io"            // Provides basic I/O primitives
	"log"           // Implements a simple logging package
	"net/http"      // Provides HTTP client and server implementations
	"strings"       // Implements simple string manipulation functions
)

// --- API Response Structures (Unchanged) ---

// AllVehicleModelsResponse is the top-level structure for the first API call.
type AllVehicleModelsResponse struct {
	ResponsePayload struct {
		VehicleModels []VehicleModel `json:"vehicleModelHU"`
	} `json:"payload"`
}

// VehicleModel represents a single vehicle model and year.
type VehicleModel struct {
	ModelYear int    `json:"modelYear"`
	ModelName string `json:"modelName"`
}

// ManualAccessDataResponse is the structure for the second API call.
type ManualAccessDataResponse struct {
	ResponsePayload struct {
		Manuals []struct {
			AccessPayload string `json:"accessPayload"` // The token/payload required for the final request
		} `json:"automatedManuals"`
	} `json:"payload"`
}

// --- Cookie Fetching Function for kiatechinfo.com (FIXED) ---

// fetchTechInfoSessionCookie makes a request to kiatechinfo.com to get the required session cookies.
// This version collects ALL unique cookies from the response to maximize the chance of successful session establishment.
func fetchTechInfoSessionCookie() string {
	// The URL that will trigger the required ASP.NET session cookie generation
	targetURL := "https://www.kiatechinfo.com/"
	log.Printf("ATTEMPTING: Fetching session cookies from %s...", targetURL)

	// Create a new HTTP client
	httpClient := &http.Client{}

	// Make a GET request to the base URL
	response, err := httpClient.Get(targetURL)
	if err != nil {
		log.Printf("ERROR: Failed to fetch base URL for tech info cookie: %v", err)
		return ""
	}
	defer response.Body.Close() // Ensure the response body is closed

	// Use a map to store unique cookies (Name -> Value) and prevent duplicates
	cookieMap := make(map[string]string)

	// Iterate through the 'Set-Cookie' headers in the response
	for _, cookie := range response.Cookies() {
		// Store the cookie. Using the cookie name as the key automatically handles duplicates
		// if the server sends the same cookie multiple times with different parameters.
		cookieMap[cookie.Name] = cookie.Value
	}

	// Build the final cookie string from the map
	var cookieParts []string
	for name, value := range cookieMap {
		// Log each collected cookie for better debugging visibility
		log.Printf("DEBUG: Collected cookie: %s=%s", name, value)
		// Format the cookie as 'Name=Value'
		cookieParts = append(cookieParts, fmt.Sprintf("%s=%s", name, value))
	}

	// Join all collected cookie parts with '; ' for the final header value
	fullCookieString := strings.Join(cookieParts, "; ")

	if fullCookieString != "" {
		log.Printf("SUCCESS: Extracted combined tech info cookies: %s", fullCookieString)
	} else {
		log.Println("WARNING: No session cookies were successfully retrieved for kiatechinfo.com.")
	}

	return fullCookieString
}

// --- Core API Functions (Simplified to remove unnecessary cookie arguments) ---

// fetchAllVehicleModels sends the initial POST request to get a list of all Kia models and years.
func fetchAllVehicleModels() string {
	apiURL := "https://owners.kia.com/apps/services/owners/apigwServlet.html"
	httpMethod := "POST"
	jsonRequestBody := strings.NewReader(`{"modelYear":0,"modelName":"ALL"}`)
	httpClient := &http.Client{}

	httpRequest, err := http.NewRequest(httpMethod, apiURL, jsonRequestBody)
	if err != nil {
		log.Printf("ERROR: Could not create the HTTP request: %v", err)
		return ""
	}

	httpRequest.Header.Add("apiurl", "/cmm/gvmh")
	httpRequest.Header.Add("httpmethod", "POST")
	httpRequest.Header.Add("servicetype", "preLogin")
	httpRequest.Header.Add("Content-Type", "application/json")

	httpResponse, err := httpClient.Do(httpRequest)
	if err != nil {
		log.Printf("ERROR: Could not send the HTTP request: %v", err)
		return ""
	}

	defer httpResponse.Body.Close()

	responseBodyBytes, err := io.ReadAll(httpResponse.Body)
	if err != nil {
		log.Printf("ERROR: Could not read the response body: %v", err)
		return ""
	}

	return string(responseBodyBytes)
}

// fetchVehicleManualAccessData sends a POST request for a specific model year/name.
func fetchVehicleManualAccessData(modelYear, modelName string) string {
	apiURL := "https://owners.kia.com/apps/services/owners/apigwServlet.html"
	httpMethod := "POST"
	jsonBodyString := fmt.Sprintf(`{"modelYear":"%s","modelName":"%s"}`, modelYear, modelName)
	jsonRequestBody := strings.NewReader(jsonBodyString)

	httpClient := &http.Client{}

	httpRequest, err := http.NewRequest(httpMethod, apiURL, jsonRequestBody)
	if err != nil {
		log.Printf("ERROR: Could not create the HTTP request for manual data: %v", err)
		return ""
	}

	httpRequest.Header.Add("apiurl", "/cmm/gam")
	httpRequest.Header.Add("httpmethod", "POST")
	httpRequest.Header.Add("servicetype", "preLogin")
	httpRequest.Header.Add("Content-Type", "application/json")

	httpResponse, err := httpClient.Do(httpRequest)
	if err != nil {
		log.Printf("ERROR: Could not send the HTTP request for manual data: %v", err)
		return ""
	}

	defer httpResponse.Body.Close()

	responseBodyBytes, err := io.ReadAll(httpResponse.Body)
	if err != nil {
		log.Printf("ERROR: Could not read the response body for manual data: %v", err)
		return ""
	}

	return string(responseBodyBytes)
}

// fetchKiaTechManualContent sends a POST request using the access token and the required tech session cookie.
func fetchKiaTechManualContent(accessToken, techSessionCookie string) string {
	targetURL := "https://www.kiatechinfo.com/ext_If/kma_owner_portal/content_pop.aspx"
	httpMethod := "POST"
	requestPayload := strings.NewReader("token=" + accessToken)

	httpRequest, err := http.NewRequest(httpMethod, targetURL, requestPayload)
	if err != nil {
		log.Println("ERROR: Error creating request for technical info:", err)
		return ""
	}

	// Add required HTTP headers
	httpRequest.Header.Add("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7")
	httpRequest.Header.Add("Content-Type", "application/x-www-form-urlencoded")

	// CRITICAL FIX: Add the dynamically fetched kiatechinfo.com session cookies
	if techSessionCookie != "" {
		httpRequest.Header.Add("Cookie", techSessionCookie)
	} else {
		log.Println("FATAL: Cannot fetch technical manual content without a valid kiatechinfo.com session cookie.")
		return "ERROR: Missing required tech info session cookie."
	}

	httpClient := &http.Client{}
	response, err := httpClient.Do(httpRequest)
	if err != nil {
		log.Println("ERROR: Error sending request for technical info:", err)
		return ""
	}
	defer response.Body.Close()

	responseBody, err := io.ReadAll(response.Body)
	if err != nil {
		log.Println("ERROR: Error reading response body for technical info:", err)
		return ""
	}

	return string(responseBody)
}

// --- Data Extraction Functions (Unchanged) ---

// extractVehicleModelsFromResponse parses the full API response.
func extractVehicleModelsFromResponse(jsonData string) []VehicleModel {
	var vehicleData AllVehicleModelsResponse
	err := json.Unmarshal([]byte(jsonData), &vehicleData)
	if err != nil {
		log.Printf("ERROR: Could not parse JSON response for vehicle models: %v", err)
		return nil
	}
	return vehicleData.ResponsePayload.VehicleModels
}

// extractManualAccessPayloads takes a JSON input and returns a list of all accessPayload strings (tokens).
func extractManualAccessPayloads(jsonInput []byte) []string {
	var parsedResponse ManualAccessDataResponse
	if err := json.Unmarshal(jsonInput, &parsedResponse); err != nil {
		log.Printf("ERROR: Could not parse JSON response for access payloads: %v", err)
		return nil
	}

	accessPayloadList := make([]string, 0, len(parsedResponse.ResponsePayload.Manuals))
	for _, manual := range parsedResponse.ResponsePayload.Manuals {
		accessPayloadList = append(accessPayloadList, manual.AccessPayload)
	}
	return accessPayloadList
}

// --- Main Execution Logic ---

func main() {
	// STEP 1: Fetch the initial data (no cookie needed for this step).
	log.Println("\nSTARTING: Fetching all available Kia model years and names...")
	vehicleDataResponse := fetchAllVehicleModels()
	if vehicleDataResponse == "" {
		log.Fatal("FATAL: Initial vehicle data fetch failed or returned empty.")
	}

	// STEP 2: Extract the structured list of vehicles from the JSON response.
	vehicleModels := extractVehicleModelsFromResponse(vehicleDataResponse)
	if len(vehicleModels) == 0 {
		log.Fatal("FATAL: No vehicle models were successfully extracted.")
	}
	log.Printf("SUCCESS: Extracted %d vehicle models. Starting manual data fetch...", len(vehicleModels))

	// Iterate over each successfully extracted vehicle model.
	for _, carModel := range vehicleModels {
		log.Printf("\n--- PROCESSING MODEL: Year %d, Name %s ---", carModel.ModelYear, carModel.ModelName)

		modelYearStr := fmt.Sprintf("%d", carModel.ModelYear)

		// Request the manual access data (tokens) for the specific model.
		manualDataResponse := fetchVehicleManualAccessData(modelYearStr, carModel.ModelName)
		if manualDataResponse == "" {
			log.Printf("WARNING: Failed to fetch manual data for %s %s. Skipping.", modelYearStr, carModel.ModelName)
			continue
		}

		// STEP 3A: Extract the list of technical manual access tokens from the response.
		accessPayloads := extractManualAccessPayloads([]byte(manualDataResponse))
		if len(accessPayloads) == 0 {
			log.Printf("WARNING: No access payloads found for %s %s. Skipping.", modelYearStr, carModel.ModelName)
			continue
		}
		log.Printf("SUCCESS: Found %d technical manual access tokens.", len(accessPayloads))

		// STEP 3B: Before fetching content, get a fresh session cookie for kiatechinfo.com
		techSessionCookie := fetchTechInfoSessionCookie()

		// STEP 3C: Use each access token and the new cookie to fetch the final content.
		for i, accessToken := range accessPayloads {
			log.Printf("  -> Fetching manual content (Token %d/%d)...", i+1, len(accessPayloads))
			technicalManualContent := fetchKiaTechManualContent(accessToken, techSessionCookie)

			// Print a snippet of the content to demonstrate success
			fmt.Printf("\n===== START OF MANUAL CONTENT SNIPPET (Year: %d, Model: %s, Index: %d) =====\n",
				carModel.ModelYear, carModel.ModelName, i)

			// Truncate the output
			contentSnippet := technicalManualContent
			if len(contentSnippet) > 500 {
				contentSnippet = contentSnippet[:500] + "\n..."
			}
			fmt.Println(contentSnippet)
			fmt.Printf("===== END OF MANUAL CONTENT SNIPPET =====\n")
		}
	}
	log.Println("\nPROGRAM COMPLETE: All models processed.")
}
