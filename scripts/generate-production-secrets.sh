#!/bin/bash

# Production Secrets Generator
# This script helps generate secure secrets for production deployment

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "🔐 Production Secrets Generator"
echo "================================================"
echo ""

# Function to generate secure random strings
generate_secret() {
    local length=${1:-32}
    openssl rand -hex "$length"
}

generate_password() {
    local length=${1:-16}
    openssl rand -base64 "$length" | tr -d "=+/" | cut -c1-"$length"
}

# Check if .env.production exists
if [ -f ".env.production" ]; then
    echo -e "${YELLOW}⚠️  Warning: .env.production already exists${NC}"
    read -p "Do you want to backup existing file? (y/n): " backup_choice
    if [ "$backup_choice" = "y" ]; then
        backup_file=".env.production.backup.$(date +%Y%m%d_%H%M%S)"
        cp .env.production "$backup_file"
        echo -e "${GREEN}✅ Backup created: $backup_file${NC}"
    fi
    echo ""
fi

# Generate secrets
echo "Generating secure secrets..."
echo ""

SECRET_KEY=$(generate_secret 32)
echo -e "${GREEN}✅ SECRET_KEY generated${NC}"

POSTGRES_PASSWORD=$(generate_password 20)
echo -e "${GREEN}✅ PostgreSQL password generated${NC}"

REDIS_PASSWORD=$(generate_password 20)
echo -e "${GREEN}✅ Redis password generated${NC}"

QDRANT_API_KEY=$(generate_secret 32)
echo -e "${GREEN}✅ Qdrant API key generated${NC}"

NEXTAUTH_SECRET=$(openssl rand -base64 32)
echo -e "${GREEN}✅ NextAuth secret generated${NC}"

KONG_ADMIN_TOKEN=$(generate_secret 24)
echo -e "${GREEN}✅ Kong admin token generated${NC}"

echo ""
echo "================================================"
echo "📝 Generated Secrets (Save these securely!)"
echo "================================================"
echo ""

# Create secrets file (not .env, for security)
SECRETS_FILE="production-secrets-$(date +%Y%m%d_%H%M%S).txt"

cat > "$SECRETS_FILE" << EOF
# Generated Production Secrets
# Date: $(date)
# IMPORTANT: Store these securely and delete this file after use

SECRET_KEY=$SECRET_KEY
POSTGRES_PASSWORD=$POSTGRES_PASSWORD
REDIS_PASSWORD=$REDIS_PASSWORD
QDRANT_API_KEY=$QDRANT_API_KEY
NEXTAUTH_SECRET=$NEXTAUTH_SECRET
KONG_ADMIN_TOKEN=$KONG_ADMIN_TOKEN

# Database URL with strong password:
DATABASE_URL=postgresql://sgd_prod_user:$POSTGRES_PASSWORD@postgres:5432/sgd_production_db

# Redis URL with password:
REDIS_URL=redis://:$REDIS_PASSWORD@redis:6379/0
EOF

echo -e "${GREEN}✅ Secrets saved to: $SECRETS_FILE${NC}"
echo ""

# Provide instructions
echo "================================================"
echo "📋 Next Steps:"
echo "================================================"
echo ""
echo "1. Copy these values to your secrets management system:"
echo "   - AWS Secrets Manager"
echo "   - HashiCorp Vault"
echo "   - Azure Key Vault"
echo "   - Or your preferred solution"
echo ""
echo "2. Update your .env.production with these values"
echo ""
echo "3. Delete the generated secrets file:"
echo -e "   ${YELLOW}rm $SECRETS_FILE${NC}"
echo ""
echo "4. Never commit .env.production to git:"
echo "   git add .gitignore"
echo "   echo '.env.production' >> .gitignore"
echo ""
echo -e "${RED}⚠️  SECURITY REMINDER:${NC}"
echo "- Never share these secrets"
echo "- Never commit them to version control"
echo "- Rotate them regularly (every 90 days)"
echo "- Use different secrets for each environment"
echo ""

# Optional: Display secrets (can be disabled in production)
read -p "Display generated secrets? (y/n): " show_secrets
if [ "$show_secrets" = "y" ]; then
    echo ""
    cat "$SECRETS_FILE"
    echo ""
fi

echo "================================================"
echo -e "${GREEN}✅ Secret generation complete!${NC}"
echo "================================================"