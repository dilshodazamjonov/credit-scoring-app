package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"
	"time"

	"github.com/gofiber/fiber/v2"
	"github.com/gofiber/fiber/v2/middleware/cors"
	"github.com/gofiber/fiber/v2/middleware/logger"
	"github.com/gofiber/fiber/v2/middleware/recover"
)

// --- Configuration and Data Schemas ---

type FeatureConfig struct {
	Name string `json:"name"`
	Type string `json:"type"`
}

type ModelConfig struct {
	Threshold float64         `json:"threshold"`
	Features  []FeatureConfig `json:"features"`
}

type MLServiceRequest struct {
	Data map[string]interface{} `json:"data"`
}

type MLServiceResponse struct {
	Probability float64 `json:"probability"`
	IsHighRisk  bool    `json:"is_high_risk"`
	Threshold   float64 `json:"threshold"`
	Status      string  `json:"status"`
}

type AppResponse struct {
	Probability float64 `json:"probability"`
	Decision    string  `json:"decision"`
	Threshold   float64 `json:"threshold"`
	Status      string  `json:"status"`
}

type Gateway struct {
	MLServiceURL string
	Config       ModelConfig
	HTTPClient   *http.Client
}

func main() {
	gw := &Gateway{
		MLServiceURL: getEnv("ML_SERVICE_URL", "http://ml-service:8000/predict"),
		HTTPClient: &http.Client{
			Timeout: 15 * time.Second,
		},
	}

	// Load Schema
	if err := gw.loadModelConfig("schema/catboost_production_bundle.json"); err != nil {
		log.Fatalf("Configuration Error: %v", err)
	}

	app := fiber.New(fiber.Config{
		DisableStartupMessage: true,
		ReadTimeout:           10 * time.Second,
	})

	// Middleware
	app.Use(recover.New())
	app.Use(logger.New(logger.Config{
		Format: "[${time}] ${status} - ${latency} ${method} ${path}\n",
	}))
	app.Use(cors.New(cors.Config{
		AllowOrigins: "*",
		AllowHeaders: "Origin, Content-Type, Accept",
		AllowMethods: "GET, POST, OPTIONS",
	}))

	// Routes
	app.Get("/health", gw.handleHealth)
	app.Get("/config", gw.handleConfig) // NEW: Endpoint for frontend to auto-generate forms
	app.Post("/apply", gw.handleApplication)

	port := getEnv("GATEWAY_PORT", "3000")
	log.Printf("Gateway service starting on port %s", port)
	if err := app.Listen(fmt.Sprintf(":%s", port)); err != nil {
		log.Fatal(err)
	}
}

// --- Handlers ---

func (gw *Gateway) handleHealth(c *fiber.Ctx) error {
	return c.Status(http.StatusOK).JSON(fiber.Map{
		"status": "healthy",
		"time":   time.Now().Format(time.RFC3339),
	})
}

func (gw *Gateway) handleConfig(c *fiber.Ctx) error {
	// Send the model features and threshold to the frontend
	return c.Status(http.StatusOK).JSON(gw.Config)
}

func (gw *Gateway) handleApplication(c *fiber.Ctx) error {
	var userInput map[string]interface{}
	if err := c.BodyParser(&userInput); err != nil {
		return c.Status(http.StatusBadRequest).JSON(fiber.Map{"error": "Invalid request payload"})
	}

	mlReq := MLServiceRequest{Data: userInput}
	payload, err := json.Marshal(mlReq)
	if err != nil {
		return c.Status(http.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to serialize internal request"})
	}

	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()

	req, _ := http.NewRequestWithContext(ctx, "POST", gw.MLServiceURL, bytes.NewBuffer(payload))
	req.Header.Set("Content-Type", "application/json")

	resp, err := gw.HTTPClient.Do(req)
	if err != nil {
		log.Printf("Upstream Service Error: %v", err)
		return c.Status(http.StatusServiceUnavailable).JSON(fiber.Map{"error": "Inference engine unreachable"})
	}
	defer resp.Body.Close()

	body, _ := io.ReadAll(resp.Body)
	if resp.StatusCode != http.StatusOK {
		log.Printf("Upstream Service Failure: Status %d", resp.StatusCode)
		return c.Status(resp.StatusCode).Send(body)
	}

	var mlRes MLServiceResponse
	if err := json.Unmarshal(body, &mlRes); err != nil {
		return c.Status(http.StatusInternalServerError).JSON(fiber.Map{"error": "Failed to parse inference response"})
	}

	decision := "APPROVED"
	if mlRes.IsHighRisk {
		decision = "REJECTED"
	}

	return c.Status(http.StatusOK).JSON(AppResponse{
		Probability: mlRes.Probability,
		Decision:    decision,
		Threshold:   mlRes.Threshold,
		Status:      "success",
	})
}

// --- Utilities ---

func (gw *Gateway) loadModelConfig(path string) error {
	data, err := os.ReadFile(path)
	if err != nil {
		return fmt.Errorf("could not read schema file: %w", err)
	}
	if err := json.Unmarshal(data, &gw.Config); err != nil {
		return fmt.Errorf("could not unmarshal schema: %w", err)
	}
	return nil
}

func getEnv(key, fallback string) string {
	if value, ok := os.LookupEnv(key); ok {
		return value
	}
	return fallback
}