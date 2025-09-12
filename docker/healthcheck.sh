#!/bin/sh
# Health check script for container

# Check if the service is responding
curl -f http://localhost:8000/health/liveness || exit 1

# Check if critical dependencies are accessible
curl -f http://localhost:8000/health/readiness || exit 1

exit 0