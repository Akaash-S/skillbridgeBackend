#!/bin/bash

# Helper script to find the application directory
# Run this if you're not sure where the application files are located

echo "🔍 Searching for SkillBridge application files..."
echo ""

# Check common locations
LOCATIONS=(
    "/opt/skillbridge"
    "/opt/skillbridge/backend"
    "/home/$(whoami)/skillbridge"
    "/home/$(whoami)/skillbridge/backend"
    "/home/$(whoami)/skillbridgeBackend"
    "/home/$(whoami)/skillbridgeBackend/backend"
    "$(pwd)"
    "$(pwd)/backend"
)

for location in "${LOCATIONS[@]}"; do
    if [ -d "$location" ] && [ -f "$location/Dockerfile" ] && [ -f "$location/docker-compose.yml" ]; then
        echo "✅ Found application files at: $location"
        echo ""
        echo "📋 Files found:"
        ls -la "$location" | grep -E "(Dockerfile|docker-compose|\.env|continue-deployment)"
        echo ""
        echo "🚀 To continue deployment:"
        echo "   cd $location"
        echo "   nano .env  # Configure your settings"
        echo "   ./continue-deployment.sh"
        echo ""
        exit 0
    fi
done

echo "❌ Could not find application files in common locations."
echo ""
echo "🔍 Let's search the entire system (this may take a moment)..."
find /opt /home -name "docker-compose.yml" -type f 2>/dev/null | while read file; do
    dir=$(dirname "$file")
    if [ -f "$dir/Dockerfile" ]; then
        echo "✅ Found potential application at: $dir"
    fi
done

echo ""
echo "💡 If you still can't find the files, try:"
echo "   find / -name 'continue-deployment.sh' 2>/dev/null"
echo "   find / -name 'docker-compose.yml' 2>/dev/null"