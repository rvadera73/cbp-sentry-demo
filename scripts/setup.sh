#!/bin/bash

# Sentry CBP Setup Script

echo "🔧 Setting up Sentry CBP..."

# Create .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "📝 Creating .env from .env.example..."
    cp .env.example .env
else
    echo "✓ .env already exists"
fi

# Install API dependencies
echo "📦 Installing API dependencies..."
cd api
pip install -r requirements.txt
cd ..

# Install UI dependencies
echo "📦 Installing UI dependencies..."
cd ui
npm install
cd ..

echo "✓ Setup complete!"
echo ""
echo "Next steps:"
echo "1. docker-compose up   # Start all services"
echo "2. Open http://localhost:3000 in your browser"
