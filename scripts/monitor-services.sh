#!/bin/bash

# Service monitoring script
# Run this periodically to check service health

set -e

echo "🔍 SkillBridge Service Monitor"
echo "=============================="
echo "Timestamp: $(date)"
echo ""

# Check Docker services
echo "📦 Docker Services Status:"
docker-compose -f docker-compose.prod.yml ps
echo ""

# Check health endpoint
echo "🏥 Health Check:"
if curl -f -s -m 10 http://localhost/health > /dev/null 2>&1; then
    echo "✅ Health endpoint: OK"
else
    echo "❌ Health endpoint: FAILED"
    echo "🔧 Attempting to restart backend..."
    docker-compose -f docker-compose.prod.yml restart backend
fi
echo ""

# Check SSL certificate expiry
echo "🔐 SSL Certificate Status:"
if [ -f "nginx/ssl/fullchain.pem" ]; then
    EXPIRY=$(openssl x509 -in nginx/ssl/fullchain.pem -noout -enddate | cut -d= -f2)
    EXPIRY_EPOCH=$(date -d "$EXPIRY" +%s)
    CURRENT_EPOCH=$(date +%s)
    DAYS_LEFT=$(( (EXPIRY_EPOCH - CURRENT_EPOCH) / 86400 ))
    
    if [ $DAYS_LEFT -gt 30 ]; then
        echo "✅ SSL Certificate: Valid ($DAYS_LEFT days remaining)"
    elif [ $DAYS_LEFT -gt 7 ]; then
        echo "⚠️  SSL Certificate: Expires soon ($DAYS_LEFT days remaining)"
    else
        echo "❌ SSL Certificate: Expires very soon ($DAYS_LEFT days remaining)"
    fi
else
    echo "❌ SSL Certificate: Not found"
fi
echo ""

# Check disk space
echo "💾 Disk Usage:"
df -h / | tail -1 | awk '{
    if ($5+0 > 90) 
        print "❌ Disk usage: " $5 " (Critical)"
    else if ($5+0 > 80) 
        print "⚠️  Disk usage: " $5 " (Warning)"
    else 
        print "✅ Disk usage: " $5 " (OK)"
}'
echo ""

# Check memory usage
echo "🧠 Memory Usage:"
FREE_MEM=$(free | grep Mem | awk '{printf "%.1f", ($3/$2) * 100.0}')
if (( $(echo "$FREE_MEM > 90" | bc -l) )); then
    echo "❌ Memory usage: ${FREE_MEM}% (Critical)"
elif (( $(echo "$FREE_MEM > 80" | bc -l) )); then
    echo "⚠️  Memory usage: ${FREE_MEM}% (Warning)"
else
    echo "✅ Memory usage: ${FREE_MEM}% (OK)"
fi
echo ""

# Check recent errors in logs
echo "📋 Recent Errors (last 10 minutes):"
ERROR_COUNT=0

if [ -f "logs/nginx/skillbridge-server.error.log" ]; then
    NGINX_ERRORS=$(find logs/nginx/skillbridge-server.error.log -mmin -10 -exec grep -c "error\|crit\|alert\|emerg" {} \; 2>/dev/null || echo "0")
    ERROR_COUNT=$((ERROR_COUNT + NGINX_ERRORS))
fi

if [ -f "logs/app/gunicorn-error.log" ]; then
    APP_ERRORS=$(find logs/app/gunicorn-error.log -mmin -10 -exec grep -c "ERROR\|CRITICAL" {} \; 2>/dev/null || echo "0")
    ERROR_COUNT=$((ERROR_COUNT + APP_ERRORS))
fi

if [ $ERROR_COUNT -eq 0 ]; then
    echo "✅ No recent errors found"
else
    echo "⚠️  Found $ERROR_COUNT recent errors"
    echo "   Check logs: docker-compose -f docker-compose.prod.yml logs --tail=50"
fi
echo ""

# Check network connectivity
echo "🌐 Network Connectivity:"
if ping -c 1 8.8.8.8 > /dev/null 2>&1; then
    echo "✅ Internet connectivity: OK"
else
    echo "❌ Internet connectivity: FAILED"
fi
echo ""

# Summary
echo "📊 Summary:"
echo "   Services: $(docker-compose -f docker-compose.prod.yml ps --services --filter status=running | wc -l)/$(docker-compose -f docker-compose.prod.yml ps --services | wc -l) running"
echo "   Disk: $(df -h / | tail -1 | awk '{print $5}')"
echo "   Memory: ${FREE_MEM}%"
echo "   Errors: $ERROR_COUNT recent"
echo ""
echo "🔗 Useful commands:"
echo "   View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "   Restart:   docker-compose -f docker-compose.prod.yml restart"
echo "   Status:    docker-compose -f docker-compose.prod.yml ps"