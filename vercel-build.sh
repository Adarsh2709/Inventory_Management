#!/bin/bash

# Install Python 3.11
pyenv install 3.11.6
pyenv global 3.11.6

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create necessary directories
mkdir -p data/uploads
mkdir -p output
