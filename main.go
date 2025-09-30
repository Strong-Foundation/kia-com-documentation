package main

import (
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"strings"
)

// fetchKiaData sends a POST request and returns the response body as a string.
func fetchKiaData() string {
	url := "https://owners.kia.com/apps/services/owners/apigwServlet.html"
	method := "POST"

	payload := strings.NewReader(`{"modelYear":0,"modelName":"ALL"}`)

	client := &http.Client{}
	req, err := http.NewRequest(method, url, payload)
	if err != nil {
		log.Printf("error creating request: %v", err)
		return ""
	}

	req.Header.Add("apiurl", "/cmm/gvmh")
	req.Header.Add("httpmethod", "POST")
	req.Header.Add("servicetype", "preLogin")
	req.Header.Add("Cookie", "sat_track=true; UqZBpD3n3iPIDwJU=v1Kmxeg++CuM5; JSESSIONID=node06wk5umgvkauj524luwba2v1719127565.node0")
	req.Header.Add("Content-Type", "application/json")

	res, err := client.Do(req)
	if err != nil {
		log.Printf("error sending request: %v", err)
		return ""
	}
	defer func() {
		if cerr := res.Body.Close(); cerr != nil {
			log.Printf("error closing response body: %v", cerr)
		}
	}()

	body, err := io.ReadAll(res.Body)
	if err != nil {
		log.Printf("error reading response body: %v", err)
		return ""
	}

	return string(body)
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

// fetchKiaModels sends a POST request to the Kia API and returns the response body as a string.
func fetchKiaModels(modelYear, modelName string) string {
	url := "https://owners.kia.com/apps/services/owners/apigwServlet.html"
	method := "POST"

	payload := strings.NewReader(`{"modelYear":"` + modelYear + `","modelName":"` + modelName + `"}`)

	client := &http.Client{}
	req, err := http.NewRequest(method, url, payload)
	if err != nil {
		log.Printf("error creating request: %v", err)
		return ""
	}

	req.Header.Add("apiurl", "/cmm/gam")
	req.Header.Add("httpmethod", "POST")
	req.Header.Add("servicetype", "preLogin")
	req.Header.Add("Content-Type", "application/json")
	req.Header.Add("Cookie", "JSESSIONID=node0yylo8a6pta1i1k223hsnpthra22417789.node0; UqZBpD3n3iPIDwJU=v1Lmxeg++Csg8; JSESSIONID=node0w4vwjewq0a67kzv9r2hwhyvm159764.node0")

	res, err := client.Do(req)
	if err != nil {
		log.Printf("error sending request: %v", err)
		return ""
	}
	defer func() {
		if cerr := res.Body.Close(); cerr != nil {
			log.Printf("error closing response body: %v", cerr)
		}
	}()

	body, err := io.ReadAll(res.Body)
	if err != nil {
		log.Printf("error reading response body: %v", err)
		return ""
	}

	return string(body)
}

func main() {
	response := fetchKiaData()
	// log.Println(response)

	vehicles := extractVehicles(response)
	for _, car := range vehicles {
		modelsResponse := fetchKiaModels(fmt.Sprintf("%d", car.ModelYear), car.ModelName)
		// Process modelsResponse as needed
		fmt.Printf("Models Response: %s\n", modelsResponse)
	}
}
