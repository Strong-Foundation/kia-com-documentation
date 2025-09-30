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

func main() {
	response := fetchKiaData()
	// log.Println(response)

	vehicles := extractVehicles(response)
	for _, car := range vehicles {
		fmt.Printf("Model Year: %d, Model Name: %s\n", car.ModelYear, car.ModelName)
	}
}
