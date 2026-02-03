#!/bin/bash

# RWD IE Optimizer Startup Script

echo "╔══════════════════════════════════════════════════════════╗"
echo "║                                                          ║"
echo "║           RWD IE Optimizer - Startup Script             ║"
echo "║                                                          ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Creating virtual environment..."
    python3 -m venv venv
    echo "✅ Virtual environment created"
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "   Copying from .env.example..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "✅ .env file created"
        echo "⚠️  Please edit .env and add your API keys!"
        echo ""
        read -p "Press Enter to continue..."
    else
        echo "❌ .env.example not found!"
        exit 1
    fi
fi

# Install/upgrade dependencies
echo "📦 Installing dependencies..."
pip install -q --upgrade pip
pip install -q -r requirements.txt

# Check database
if [ ! -f "data/rwd_claims.db" ]; then
    echo "⚠️  Database not found at data/rwd_claims.db"
    echo "   Run setup/create_database.py first"
fi

echo ""
echo "🚀 Starting RWD IE Optimizer..."
echo ""

# Start the server
python main.py
