#!/bin/bash

echo "Starting I NEMI Backend Server..."
echo ""

echo "Installing dependencies..."
pip install -r requirements.txt

echo ""
echo "Starting Flask server..."
python app.py 