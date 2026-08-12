#!/bin/bash

set -e

echo "🚀 Starting College Social infrastructure..."

docker compose up -d

echo ""
echo "⏳ Waiting for services..."

until docker inspect --format='{{.State.Health.Status}}' college-social-postgres 2>/dev/null | grep -q healthy
do
    sleep 1
done

until docker inspect --format='{{.State.Health.Status}}' college-social-redis 2>/dev/null | grep -q healthy
do
    sleep 1
done

echo ""
echo "✅ PostgreSQL is ready"
echo "✅ Redis is ready"

echo ""
docker compose ps

echo ""
echo "🎉 Infrastructure is ready!"