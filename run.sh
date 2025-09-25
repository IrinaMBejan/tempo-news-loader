#!/bin/bash

rm -rf .venv

uv venv -p 3.12 .venv
uv pip install -e .
# Set default port if not provided
SYFTBOX_ASSIGNED_PORT=${SYFTBOX_ASSIGNED_PORT:-8080}

# Check if articles folder exists to determine fetch frequency
if [ -d "articles" ]; then
    SLEEP_TIME=3600  # 1 hour if articles folder exists
    SLEEP_MSG="1 hour"
    echo "Articles folder found - running every hour"
else
    SLEEP_TIME=10    # 10 seconds for first time fetching
    SLEEP_MSG="10 seconds"
    echo "Articles folder not found - running every 10 seconds until first fetch"
fi

# Run the news fetcher in a loop
while true; do  
    echo "$(date): Fetching news articles..."
    uv run tempo-news fetch --max-articles 25
    echo "$(date): Sleeping for $SLEEP_MSG..."
    sleep $SLEEP_TIME
    
    # Re-check if we need to switch from 10 seconds to 1 hour
    if [ $SLEEP_TIME -eq 10 ] && [ -d "articles" ]; then
        SLEEP_TIME=3600
        SLEEP_MSG="1 hour"
        echo "Articles folder created - switching to hourly schedule"
    fi
done

