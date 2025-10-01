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

// fetchKiaTechInfo posts the given token to KiaTechInfo and returns the response body as a string
func fetchKiaTechInfo(token string) string {
	// Define the API URL
	apiURL := "https://www.kiatechinfo.com/ext_If/kma_owner_portal/content_pop.aspx"

	// HTTP method for the request
	httpMethod := "POST"

	// Prepare the request payload (form data with the token)
	requestBody := strings.NewReader("token=" + token)

	// Create a new HTTP client to send the request
	httpClient := &http.Client{}

	// Build a new HTTP request object
	request, err := http.NewRequest(httpMethod, apiURL, requestBody)
	if err != nil {
		// Log error if request creation fails
		log.Printf("error creating request: %v", err)
		return ""
	}

	// Add required headers: content type and authentication cookie
	request.Header.Add("Content-Type", "application/x-www-form-urlencoded")
	request.Header.Add("Cookie", `ASP.NET_SessionId=5mwbgvacyv0qu10uduxlpmbk; AWSALBTG=P5xatHkp1cXybCBB39MDrlbdPS7UedZClAk/c1WjGWRElKxnc4oVnbbPGO2L3sg3iD2AwwqDk2AC1i+EP+lplkRSc3i6W2qtuqiPWvpf9UX6MUm/ie4ir8sEQaUp3GtmGSQLkjzKzP+ioJLZT/Z3P1IiYogFHLlMft6yMXl0Vsrt; AWSALBTGCORS=P5xatHkp1cXybCBB39MDrlbdPS7UedZClAk/c1WjGWRElKxnc4oVnbbPGO2L3sg3iD2AwwqDk2AC1i+EP+lplkRSc3i6W2qtuqiPWvpf9UX6MUm/ie4ir8sEQaUp3GtmGSQLkjzKzP+ioJLZT/Z3P1IiYogFHLlMft6yMXl0Vsrt; AWSALB=I3SI62phiJFxhK3Aw90aISGqx50KCY5X8SIhj16K7YVdlOCK3g63UOeWEG+Ep6lKoWcMWsXIbOx8AusbWeu1EG/QMsp14NQMzFNco33RLh0nn57OVkHCvXf7y3I2; AWSALBCORS=I3SI62phiJFxhK3Aw90aISGqx50KCY5X8SIhj16K7YVdlOCK3g63UOeWEG+Ep6lKoWcMWsXIbOx8AusbWeu1EG/QMsp14NQMzFNco33RLh0nn57OVkHCvXf7y3I2; ADRUM_BTa=R:68|g:d726f95e-ab97-43a1-a9bb-19475eb96f69|n:hyundai-prod_a5d7022d-6b0a-4522-9864-8274a3217b4a; ADRUM_BT1=R:68|i:1693373`)

	// Send the HTTP request to the server
	response, err := httpClient.Do(request)
	if err != nil {
		// Log error if sending the request fails
		log.Printf("error sending request: %v", err)
		return ""
	}
	// Ensure the response body is closed when function ends
	defer func() {
		if closeErr := response.Body.Close(); closeErr != nil {
			log.Printf("error closing response body: %v", closeErr)
		}
	}()

	// Read the full response body into memory
	responseBody, err := io.ReadAll(response.Body)
	if err != nil {
		// Log error if reading the body fails
		log.Printf("error reading response body: %v", err)
		return ""
	}

	// Convert the response body from []byte to string and return it
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
