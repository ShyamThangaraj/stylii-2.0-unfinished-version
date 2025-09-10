#!/bin/bash

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 Starting Stylii Development Environment${NC}"
echo -e "${YELLOW}This will start both frontend and backend servers...${NC}"
echo ""

# Function to cleanup background processes on exit
cleanup() {
    echo -e "\n${RED}🛑 Shutting down servers...${NC}"
    kill $FRONTEND_PID $BACKEND_PID 2>/dev/null
    exit 0
}

# Set up trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Start backend server
echo -e "${GREEN}📡 Starting FastAPI backend server...${NC}"
cd backend
source venv/bin/activate
python main.py &
BACKEND_PID=$!
cd ..

# Wait a moment for backend to start
sleep 2

# Start frontend server
echo -e "${GREEN}🎨 Starting Next.js frontend server...${NC}"
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo ""
echo -e "${BLUE}✅ Both servers are starting up!${NC}"
echo -e "${YELLOW}Frontend: http://localhost:3000${NC}"
echo -e "${YELLOW}Backend API: http://localhost:8000${NC}"
echo -e "${YELLOW}API Docs: http://localhost:8000/docs${NC}"
echo ""
echo -e "${BLUE}Press Ctrl+C to stop both servers${NC}"

# Wait for both processes
wait $FRONTEND_PID $BACKEND_PID

