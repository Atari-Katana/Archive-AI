#!/bin/sh
set -e

# Default to standardized name
host="${VORPAL_HOST:-archive-vorpal}"
port="8000"

echo "Waiting for $host to be ready..."

# We will use a simple loop with nc if available, otherwise fallback to a less ideal sleep
# Check if nc (netcat) is available
if command -v nc > /dev/null; then
    while ! nc -z "$host" "$port"; do
      echo "Vorpal is not yet available, sleeping..."
      sleep 2
    done
else
    # Fallback if nc is not available in the image
    echo "Warning: 'nc' (netcat) not found. Waiting for a fixed amount of time."
    sleep 30
fi

echo "✅ Vorpal is ready."

# Execute the main command (passed as arguments to this script)
exec "$@"
