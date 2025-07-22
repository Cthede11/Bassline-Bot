#!/bin/bash

echo "🎵 BasslineBot Pro Setup Script"
echo "==============================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if Python 3.8+ is installed
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ Python 3 is not installed. Please install Python 3.8 or higher.${NC}"
    exit 1
fi

# Check Python version
if python3 -c "import sys; exit(0 if sys.version_info >= (3,8) else 1)"; then
    echo -e "${GREEN}✅ Found Python $python_version${NC}"
else
    echo -e "${RED}❌ Python 3.8+ required. Found Python $python_version${NC}"
    exit 1
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${BLUE}📦 Creating virtual environment...${NC}"
    python3 -m venv venv
    if [[ $? -ne 0 ]]; then
        echo -e "${RED}❌ Failed to create virtual environment${NC}"
        exit 1
    fi
fi

# Activate virtual environment
echo -e "${BLUE}🔧 Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "${BLUE}📥 Upgrading pip...${NC}"
pip install --upgrade pip

# Install requirements
echo -e "${BLUE}📥 Installing requirements...${NC}"
pip install -r requirements.txt
if [[ $? -ne 0 ]]; then
    echo -e "${RED}❌ Failed to install requirements${NC}"
    exit 1
fi

# Check FFmpeg installation
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}⚠️  FFmpeg not found. Installing FFmpeg...${NC}"
    
    # Detect OS and install FFmpeg
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        if command -v apt-get &> /dev/null; then
            sudo apt update && sudo apt install -y ffmpeg
        elif command -v yum &> /dev/null; then
            sudo yum install -y ffmpeg
        elif command -v pacman &> /dev/null; then
            sudo pacman -S ffmpeg
        else
            echo -e "${YELLOW}Please install FFmpeg manually for your Linux distribution${NC}"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        if command -v brew &> /dev/null; then
            brew install ffmpeg
        else
            echo -e "${YELLOW}Please install Homebrew and run: brew install ffmpeg${NC}"
        fi
    else
        echo -e "${YELLOW}Please install FFmpeg manually: https://ffmpeg.org/download.html${NC}"
    fi
else
    echo -e "${GREEN}✅ FFmpeg found${NC}"
fi

# Create .env file if it doesn't exist
if [ ! -f ".env" ]; then
    echo -e "${BLUE}📝 Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please edit .env file and add your Discord bot token!${NC}"
else
    echo -e "${GREEN}✅ .env file already exists${NC}"
fi

# Create necessary directories
echo -e "${BLUE}📁 Creating directories...${NC}"
mkdir -p logs data downloads static

# Initialize database
echo -e "${BLUE}🗄️  Initializing database...${NC}"
python scripts/migrate.py
if [[ $? -ne 0 ]]; then
    echo -e "${YELLOW}⚠️  Database initialization had issues, but continuing...${NC}"
fi

# Set executable permissions for scripts
chmod +x scripts/*.sh

echo ""
echo -e "${GREEN}✅ Setup complete!${NC}"
echo ""
echo -e "${BLUE}Next steps:${NC}"
echo "1. Edit .env file and add your Discord bot token"
echo "2. Run the bot: python -m src.bot"
echo "3. View dashboard: http://localhost:8000"
echo ""
echo -e "${BLUE}For Docker setup:${NC} docker-compose up -d"
echo -e "${BLUE}For production:${NC} See docs/deployment.md"
echo ""
echo -e "${GREEN}🎵 Happy music botting!${NC}"