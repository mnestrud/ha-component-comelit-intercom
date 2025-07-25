#!/bin/bash

echo "Comelit Client Implementation Test with Mock Server"
echo "=================================================="
echo ""

# Start mock server in background
echo "Starting mock server..."
python3 mock-comelit-server.py &
MOCK_PID=$!

# Wait for server to start
sleep 2

# Set environment to use localhost
export COMELIT_IP_ADDRESS=127.0.0.1
export COMELIT_TOKEN=9943a85362467c53586e3553d34f8a8d

echo ""
echo "Testing Python implementation..."
echo "--------------------------------"
python3 comelit_client_python.py

echo ""
echo "Testing JavaScript implementation comparison..."
echo "---------------------------------------------"
node compare-implementations.js

# Kill mock server
echo ""
echo "Stopping mock server..."
kill $MOCK_PID 2>/dev/null

echo ""
echo "Test complete!"