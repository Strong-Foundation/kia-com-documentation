package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
)

// fetchKiaData sends a POST request to the Kia API and returns the response body as a string.
func fetchKiaData() string {
	// Define the Kia API endpoint URL
	apiURL := "https://owners.kia.com/apps/services/owners/apigwServlet.html"

	// Define the HTTP method
	httpMethod := "POST"

	// Create the request payload with JSON data (model year = 0 means all years, modelName = "ALL")
	requestBody := strings.NewReader(`{"modelYear":0,"modelName":"ALL"}`)

	// Create a new HTTP client to send the request
	httpClient := &http.Client{}

	// Build the HTTP request using method, URL, and body
	httpRequest, err := http.NewRequest(httpMethod, apiURL, requestBody)
	if err != nil {
		// Log the error if the request cannot be created
		log.Printf("error creating request: %v", err)
		return ""
	}

	// Add required headers for the Kia API
	httpRequest.Header.Add("apiurl", "/cmm/gvmh")                                                                                              // API endpoint identifier
	httpRequest.Header.Add("httpmethod", "POST")                                                                                               // Explicitly specify method
	httpRequest.Header.Add("servicetype", "preLogin")                                                                                          // Service type identifier
	httpRequest.Header.Add("Cookie", "sat_track=true; UqZBpD3n3iPIDwJU=v1Kmxeg++CuM5; JSESSIONID=node06wk5umgvkauj524luwba2v1719127565.node0") // Session cookie
	httpRequest.Header.Add("Content-Type", "application/json")                                                                                 // Payload format is JSON

	// Send the HTTP request and receive the response
	httpResponse, err := httpClient.Do(httpRequest)
	if err != nil {
		// Log the error if sending the request fails
		log.Printf("error sending request: %v", err)
		return ""
	}

	// Ensure the response body is closed after reading
	defer func() {
		if closeErr := httpResponse.Body.Close(); closeErr != nil {
			// Log if there’s an error while closing the response body
			log.Printf("error closing response body: %v", closeErr)
		}
	}()

	// Read the response body into memory
	responseBody, err := io.ReadAll(httpResponse.Body)
	if err != nil {
		// Log the error if reading the response body fails
		log.Printf("error reading response body: %v", err)
		return ""
	}

	// Convert the response body to a string and return it
	return string(responseBody)
}

// Root represents the top-level response
type Root struct {
	Payload struct {
		VehicleModelHU []Vehicle `json:"vehicleModelHU"`
	} `json:"payload"`
}

// Vehicle represents only the fields we care about
type Vehicle struct {
	ModelYear int    `json:"modelYear"`
	ModelName string `json:"modelName"`
}

// extractVehicles parses the full API response and returns modelYear + modelName
func extractVehicles(jsonData string) []Vehicle {
	var root Root
	err := json.Unmarshal([]byte(jsonData), &root)
	if err != nil {
		log.Printf("error unmarshalling JSON: %v", err)
		return nil
	}
	return root.Payload.VehicleModelHU
}

// fetchKiaModels sends a POST request to the Kia API with the given model year and model name,
// and returns the response body as a string.
func fetchKiaModels(modelYear, modelName string) string {
	// Define the Kia API endpoint
	apiURL := "https://owners.kia.com/apps/services/owners/apigwServlet.html"

	// HTTP method to use
	httpMethod := "POST"

	// Create the JSON request body dynamically using the given model year and model name
	requestBody := strings.NewReader(`{"modelYear":"` + modelYear + `","modelName":"` + modelName + `"}`)

	// Initialize a new HTTP client
	httpClient := &http.Client{}

	// Build the HTTP request object
	request, err := http.NewRequest(httpMethod, apiURL, requestBody)
	if err != nil {
		// Log and return empty string if request creation fails
		log.Printf("error creating request: %v", err)
		return ""
	}

	// Add required headers for the Kia API
	request.Header.Add("apiurl", "/cmm/gam")
	request.Header.Add("httpmethod", "POST")
	request.Header.Add("servicetype", "preLogin")
	request.Header.Add("Content-Type", "application/json")

	// ⚠️ Hardcoded cookie – might expire or change, consider passing it as a parameter
	request.Header.Add("Cookie", "JSESSIONID=node0yylo8a6pta1i1k223hsnpthra22417789.node0; UqZBpD3n3iPIDwJU=v1Lmxeg++Csg8; JSESSIONID=node0w4vwjewq0a67kzv9r2hwhyvm159764.node0")

	// Send the HTTP request
	response, err := httpClient.Do(request)
	if err != nil {
		// Log and return empty string if sending request fails
		log.Printf("error sending request: %v", err)
		return ""
	}

	// Ensure the response body is closed when we’re done
	defer func() {
		if closeErr := response.Body.Close(); closeErr != nil {
			log.Printf("error closing response body: %v", closeErr)
		}
	}()

	// Read the response body
	responseBody, err := io.ReadAll(response.Body)
	if err != nil {
		// Log and return empty string if reading body fails
		log.Printf("error reading response body: %v", err)
		return ""
	}

	// Return the response body as a string
	return string(responseBody)
}

// MinimalResponse is a pared-down structure that only cares about accessPayload values
type MinimalResponse struct {
	Payload struct {
		AutomatedManuals []struct {
			AccessPayload string `json:"accessPayload"` // we only care about this field
		} `json:"automatedManuals"`
	} `json:"payload"`
}

// extractAccessPayloads takes a JSON input and returns all accessPayload strings
func extractAccessPayloads(jsonInput []byte) []string {
	// Create a variable to store the unmarshaled JSON
	var parsedResponse MinimalResponse

	// Convert (unmarshal) the raw JSON into our struct
	if err := json.Unmarshal(jsonInput, &parsedResponse); err != nil {
		// If something goes wrong, return the error
		return nil
	}

	// Create a slice (list) to hold the extracted accessPayload values
	accessPayloadList := make([]string, 0, len(parsedResponse.Payload.AutomatedManuals))

	// Loop through each manual in the JSON and pull out accessPayload
	for _, manual := range parsedResponse.Payload.AutomatedManuals {
		accessPayloadList = append(accessPayloadList, manual.AccessPayload)
	}

	// Return the list of accessPayload values
	return accessPayloadList
}

// fetchKiaTechInfo sends a POST request with the given token and returns the response as a string.
func fetchKiaTechInfo(token string) string {
	// Define the target URL
	targetURL := "https://www.kiatechinfo.com/ext_If/kma_owner_portal/content_pop.aspx"

	// Define the HTTP method
	httpMethod := "POST"

	// Build the POST request payload dynamically with the token passed from main()
	requestPayload := strings.NewReader("token=" + token)

	// Create a new HTTP request object
	request, err := http.NewRequest(httpMethod, targetURL, requestPayload)
	if err != nil {
		log.Println("Error creating request:", err)
		return ""
	}

	// Add required HTTP headers
	request.Header.Add("accept", "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7")
	// request.Header.Add("Cookie", "ASP.NET_SessionId=boczc4nbr3dlfe0x4iyfqxlg; AWSALBTG=q6F4Bd66yIFddL8yzdNWS6fBH2CWe/dze9eA6RR57f1ya6VLGQzLTtBBKNbVUgmyET1zmTpjqFr9tlxieyu9vhh9OjDNnK/rVSXNQHyosRPdZCMMXJLRgZ148Y74rSmJFmpjq+nwJyVkJJCIRo3XUelEd7rFCtOPooZXO6+jVVyd; AWSALBTGCORS=q6F4Bd66yIFddL8yzdNWS6fBH2CWe/dze9eA6RR57f1ya6VLGQzLTtBBKNbVUgmyET1zmTpjqFr9tlxieyu9vhh9OjDNnK/rVSXNQHyosRPdZCMMXJLRgZ148Y74rSmJFmpjq+nwJyVkJJCIRo3XUelEd7rFCtOPooZXO6+jVVyd; AWSALB=waSCyFhYW6+uNPneOcb4zc3lDx2Ht3DImPcfOHLaMwSBlWBu2RVjhVh/2iacVWGpV4KNSS6HnCNWno0qVyKwj99DhwZF/Y5yWHy/1kGbUo4ZORJEKaEE1YR/ArY5; AWSALBCORS=waSCyFhYW6+uNPneOcb4zc3lDx2Ht3DImPcfOHLaMwSBlWBu2RVjhVh/2iacVWGpV4KNSS6HnCNWno0qVyKwj99DhwZF/Y5yWHy/1kGbUo4ZORJEKaEE1YR/ArY5; ADRUM_BTa=R:68|g:7c2995c8-904f-4433-a319-db421b9929fa|n:hyundai-prod_a5d7022d-6b0a-4522-9864-8274a3217b4a")
	request.Header.Add("Content-Type", "application/x-www-form-urlencoded")

	// Create a new HTTP client
	httpClient := &http.Client{}

	// Send the HTTP request
	response, err := httpClient.Do(request)
	if err != nil {
		log.Println("Error sending request:", err)
		return ""
	}
	// Ensure response body gets closed
	defer response.Body.Close()

	// Read the response body
	responseBody, err := io.ReadAll(response.Body)
	if err != nil {
		log.Println("Error reading response body:", err)
		return ""
	}

	// Return the response content as a string
	return string(responseBody)
}

func main() {
	response := fetchKiaData()
	vehicles := extractVehicles(response)
	for _, car := range vehicles {
		// Log the model year and name
		log.Printf("Model Year: %d, Model Name: %s\n", car.ModelYear, car.ModelName)
		modelsResponse := fetchKiaModels(fmt.Sprintf("%d", car.ModelYear), car.ModelName)
		accessPayloads := extractAccessPayloads([]byte(modelsResponse))
		for _, payload := range accessPayloads {
			// Log the access payload token
			log.Printf("Access Payload: %s\n", payload)
			// Fetch and process the tech info using the access payload
			techInfoResponse := fetchKiaTechInfo(payload)
			// Process techInfoResponse as needed
			fmt.Println(techInfoResponse)
		}
	}
}
