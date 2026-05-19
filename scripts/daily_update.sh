#!/bin/bash
# Daily Investment Engine Update Script
# Run this with cron for automated daily updates
# Example cron: 0 9 * * 1-5 /path/to/this/script.sh

# Set environment
export PYTHONPATH="/Users/apoorvmehrotra/Code/Investment_Engine:$PYTHONPATH"
cd /Users/apoorvmehrotra/Code/Investment_Engine

# Log file
LOG_FILE="logs/daily_update_$(date +\%Y\%m\%d).log"

# Run the daily update
echo "$(date): Starting daily update" >> "$LOG_FILE"
python main.py daily-update --index NIFTY50 >> "$LOG_FILE" 2>&1
EXIT_CODE=$?
echo "$(date): Daily update completed with exit code $EXIT_CODE" >> "$LOG_FILE"

# Optional: Send email notification on failure
if [ $EXIT_CODE -ne 0 ]; then
    echo "Daily update failed. Check $LOG_FILE" | mail -s "Investment Engine Daily Update Failed" your-email@example.com
fi

exit $EXIT_CODE