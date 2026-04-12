package main

import (
	"bytes"
	"encoding/json"
	"io"
	"log"
	"net/http"
	"os"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors" // Import CORS
	"github.com/gofiber/fiber/v2/middleware/logger"
)

type Feature struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type ModelConfig struct {
	Threshold float64   `json:"threshold"`
	Features  []Feature `json:"features"`
}

func main() {
	app := fiber.New()

	// 1. ADD CORS MIDDLEWARE (Crucial for the Frontend)
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*", // Allows any website to call this API
		AllowHeaders: "Origin, Content-Type, Accept",
		AllowMethods: "GET, POST, OPTIONS", 
	}))

	app.Use(logger.New())

	mlServiceURL := os.Getenv("ML_SERVICE_URL")
	if mlServiceURL == "" {
		mlServiceURL = "http://127.0.0.1:8000/predict"
	}

	configFile, err := os.ReadFile("schema/catboost_production_bundle.json")
	if err != nil {
		log.Fatalf("Could not read JSON file: %v", err)
	}

	var config ModelConfig
	if err := json.Unmarshal(configFile, &config); err != nil {
		log.Fatalf("Could not parse JSON: %v", err)
	}

	log.Printf("✅ Gateway loaded. Threshold: %v", config.Threshold)

	app.Get("/health", func(c *fiber.Ctx) error {
		return c.SendString("Gateway is up and running!")
	})

	// This is the endpoint for the frontend
	app.Post("/apply", func(c *fiber.Ctx) error {
		var userInput map[string]interface{}
		if err := c.BodyParser(&userInput); err != nil {
			return c.Status(400).JSON(fiber.Map{"error": "Invalid JSON format"})
		}

		pythonPayload, _ := json.Marshal(map[string]interface{}{
			"data": userInput,
		})

		resp, err := http.Post(mlServiceURL, "application/json", bytes.NewBuffer(pythonPayload))
		if err != nil {
			return c.Status(500).JSON(fiber.Map{"error": "ML Service is down"})
		}
		defer resp.Body.Close()

		pythonBody, _ := io.ReadAll(resp.Body)
		var pythonResult map[string]interface{}
		json.Unmarshal(pythonBody, &pythonResult)

		// Check if Python returned an error (like a 400 or 500)
		if resp.StatusCode != 200 {
			return c.Status(resp.StatusCode).JSON(pythonResult)
		}

		// Safely extract probability
		probVal, ok := pythonResult["probability"].(float64)
		if !ok {
			return c.Status(500).JSON(fiber.Map{"error": "Invalid response from ML service"})
		}

		decision := "APPROVED"
		if probVal > config.Threshold {
			decision = "REJECTED"
		}

		return c.JSON(fiber.Map{
			"probability": probVal,
			"decision":    decision,
			"threshold":   config.Threshold,
			"status":      "success",
		})
	})

	// Start server
	port := os.Getenv("GATEWAY_PORT")
	if port == "" {
		port = "3000"
	}
	log.Fatal(app.Listen(":" + port))
}