# Stage 1: Build the binary
FROM golang:1.26-alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies and security patches
RUN apk add --no-cache git ca-certificates && \
    apk update && apk upgrade

# Copy go mod files and download dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy all source code (including the schema folder)
COPY . .

# Build with optimizations and static linking
# -ldflags="-w -s" removes debug info to make the file smaller
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build \
    -ldflags="-w -s" \
    -a \
    -installsuffix cgo \
    -o gateway .

# Stage 2: Minimal runtime image (distroless static)
# Using 'latest' ensures we have the most recent security patches
FROM gcr.io/distroless/static-debian12:nonroot

# Set working directory to /app
WORKDIR /app

# 1. Copy the compiled binary from the builder stage
COPY --from=builder /app/gateway .

# 2. IMPORTANT: Copy the schema folder from the builder stage
# Without this, the Go app cannot find your .json file
COPY --from=builder /app/schema ./schema

# Expose the gateway port
EXPOSE 3000

# Run the application
# Since we are in WORKDIR /app, it will find ./gateway and ./schema
CMD ["./gateway"]