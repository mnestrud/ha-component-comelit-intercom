#!/bin/bash

# Load environment variables
if [ -f ../.env ]; then
    export $(cat ../.env | xargs)
fi

echo "Running Comelit protocol capture tests..."
echo "Target: $COMELIT_IP_ADDRESS"
echo ""

# Create output directory
mkdir -p protocol-captures

# Run the Node.js protocol capture
echo "1. Capturing protocol communication..."
cd ..
node tests/protocol-capture.js

# Check if capture was successful
if [ $? -eq 0 ]; then
    echo ""
    echo "2. Analyzing captured protocol..."
    cd tests
    
    # Find the latest capture file
    LATEST_CAPTURE=$(ls -t protocol-captures/*.json | head -1)
    
    if [ -f "$LATEST_CAPTURE" ]; then
        python3 protocol-analyzer.py "$LATEST_CAPTURE"
    else
        echo "Error: No capture file found"
        exit 1
    fi
else
    echo "Error: Protocol capture failed"
    exit 1
fi