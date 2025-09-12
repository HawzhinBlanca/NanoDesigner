#!/bin/bash

# NanoDesigner Secrets Setup Script
set -e

echo "🔐 Setting up NanoDesigner Secrets & Environment"
echo "==============================================="

NAMESPACE="nanodesigner"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_prompt() {
    echo -e "${BLUE}[INPUT]${NC} $1"
}

# Function to generate secure random string
generate_secret() {
    openssl rand -base64 32 | tr -d "=+/" | cut -c1-25
}

# Function to base64 encode
b64encode() {
    echo -n "$1" | base64 | tr -d '\n'
}

# Function to prompt for secret with default
prompt_secret() {
    local var_name="$1"
    local description="$2"
    local default_value="$3"
    local is_required="${4:-true}"
    
    if [ "$is_required" = "true" ] && [ -z "$default_value" ]; then
        while true; do
            log_prompt "Enter $description:"
            read -s value
            echo ""
            if [ -n "$value" ]; then
                echo "$value"
                return
            else
                log_error "$description is required!"
            fi
        done
    else
        log_prompt "Enter $description (press Enter for default: ${default_value}):"
        read -s value
        echo ""
        if [ -n "$value" ]; then
            echo "$value"
        else
            echo "$default_value"
        fi
    fi
}

# Check if kubectl is available
check_kubectl() {
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is not installed or not in PATH"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "kubectl connection verified ✓"
}

# Create namespace if it doesn't exist
ensure_namespace() {
    log_info "Ensuring namespace exists..."
    kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -
    log_info "Namespace ready ✓"
}

# Setup PostgreSQL secrets
setup_postgres_secrets() {
    log_info "Setting up PostgreSQL secrets..."
    
    POSTGRES_PASSWORD=$(prompt_secret "POSTGRES_PASSWORD" "PostgreSQL password" "$(generate_secret)")
    POSTGRES_USER=$(prompt_secret "POSTGRES_USER" "PostgreSQL username" "postgres" false)
    POSTGRES_DB=$(prompt_secret "POSTGRES_DB" "PostgreSQL database name" "nanodesigner" false)
    
    # Create PostgreSQL secret
    kubectl create secret generic postgres-secret \
        --from-literal=POSTGRES_DB="$POSTGRES_DB" \
        --from-literal=POSTGRES_USER="$POSTGRES_USER" \
        --from-literal=POSTGRES_PASSWORD="$POSTGRES_PASSWORD" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "PostgreSQL secrets configured ✓"
}

# Setup API secrets
setup_api_secrets() {
    log_info "Setting up API secrets..."
    
    OPENROUTER_API_KEY=$(prompt_secret "OPENROUTER_API_KEY" "OpenRouter API Key")
    GEMINI_API_KEY=$(prompt_secret "GEMINI_API_KEY" "Gemini API Key")
    LANGFUSE_PUBLIC_KEY=$(prompt_secret "LANGFUSE_PUBLIC_KEY" "Langfuse Public Key" "" false)
    LANGFUSE_SECRET_KEY=$(prompt_secret "LANGFUSE_SECRET_KEY" "Langfuse Secret Key" "" false)
    
    # Create API secret
    kubectl create secret generic api-secret \
        --from-literal=OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
        --from-literal=GEMINI_API_KEY="$GEMINI_API_KEY" \
        --from-literal=LANGFUSE_PUBLIC_KEY="$LANGFUSE_PUBLIC_KEY" \
        --from-literal=LANGFUSE_SECRET_KEY="$LANGFUSE_SECRET_KEY" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "API secrets configured ✓"
}

# Setup Web secrets
setup_web_secrets() {
    log_info "Setting up Web application secrets..."
    
    NEXTAUTH_SECRET=$(prompt_secret "NEXTAUTH_SECRET" "NextAuth Secret" "$(generate_secret)")
    POSTHOG_KEY=$(prompt_secret "POSTHOG_KEY" "PostHog API Key" "" false)
    SENTRY_DSN=$(prompt_secret "SENTRY_DSN" "Sentry DSN" "" false)
    
    # Create Web secret
    kubectl create secret generic web-secret \
        --from-literal=NEXTAUTH_SECRET="$NEXTAUTH_SECRET" \
        --from-literal=NEXT_PUBLIC_POSTHOG_KEY="$POSTHOG_KEY" \
        --from-literal=NEXT_PUBLIC_SENTRY_DSN="$SENTRY_DSN" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "Web secrets configured ✓"
}

# Setup ConfigMaps
setup_configmaps() {
    log_info "Setting up ConfigMaps..."
    
    API_DOMAIN=$(prompt_secret "API_DOMAIN" "API Domain (e.g., api.yourdomain.com)" "api.yourdomain.com" false)
    WEB_DOMAIN=$(prompt_secret "WEB_DOMAIN" "Web Domain (e.g., yourdomain.com)" "yourdomain.com" false)
    
    # API ConfigMap
    kubectl create configmap api-config \
        --from-literal=DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}" \
        --from-literal=REDIS_URL="redis://redis:6379" \
        --from-literal=QDRANT_URL="http://qdrant:6333" \
        --from-literal=LANGFUSE_HOST="https://cloud.langfuse.com" \
        --from-literal=PYTECTOR_MODE="strict" \
        --from-literal=STORAGE_TYPE="local" \
        --from-literal=LOG_LEVEL="INFO" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    # Web ConfigMap
    kubectl create configmap web-config \
        --from-literal=NEXT_PUBLIC_DEMO_MODE="false" \
        --from-literal=NEXT_PUBLIC_API_BASE="https://$API_DOMAIN" \
        --from-literal=NEXT_PUBLIC_ENABLE_TEMPLATES="true" \
        --from-literal=NEXT_PUBLIC_ENABLE_COLLABORATION="true" \
        --from-literal=NEXT_PUBLIC_ENABLE_ANALYTICS="true" \
        --from-literal=NODE_ENV="production" \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "ConfigMaps configured ✓"
}

# Setup TLS certificates (placeholder)
setup_tls() {
    log_info "Setting up TLS certificates..."
    
    log_warn "TLS certificate setup requires cert-manager to be installed in your cluster"
    log_warn "Make sure to update the email in k8s/ingress.yaml before deploying"
    
    # Check if cert-manager is installed
    if kubectl get crd certificates.cert-manager.io &> /dev/null; then
        log_info "cert-manager detected ✓"
    else
        log_warn "cert-manager not found. Install it with:"
        echo "kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml"
    fi
}

# Generate environment file template
generate_env_template() {
    log_info "Generating environment file template..."
    
    cat > .env.production.template << EOF
# Production Environment Template
# Copy this to .env.production and fill in the values

# Database
POSTGRES_PASSWORD=${POSTGRES_PASSWORD}
POSTGRES_USER=${POSTGRES_USER}
POSTGRES_DB=${POSTGRES_DB}

# API Keys
OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
GEMINI_API_KEY=${GEMINI_API_KEY}
LANGFUSE_PUBLIC_KEY=${LANGFUSE_PUBLIC_KEY}
LANGFUSE_SECRET_KEY=${LANGFUSE_SECRET_KEY}

# Web App
NEXTAUTH_SECRET=${NEXTAUTH_SECRET}
NEXT_PUBLIC_POSTHOG_KEY=${POSTHOG_KEY}
NEXT_PUBLIC_SENTRY_DSN=${SENTRY_DSN}

# Domains
NEXT_PUBLIC_API_BASE=https://${API_DOMAIN}
WEB_DOMAIN=${WEB_DOMAIN}
API_DOMAIN=${API_DOMAIN}
EOF
    
    log_info "Environment template created: .env.production.template ✓"
}

# Display summary
show_summary() {
    log_info "🎉 Secrets setup completed!"
    echo "=========================="
    echo ""
    echo "Created secrets in namespace: $NAMESPACE"
    echo "- postgres-secret (Database credentials)"
    echo "- api-secret (API keys and tokens)"
    echo "- web-secret (Web app secrets)"
    echo ""
    echo "Created ConfigMaps:"
    echo "- api-config (API configuration)"
    echo "- web-config (Web app configuration)"
    echo ""
    echo "Next steps:"
    echo "1. Review and update k8s/ingress.yaml with your domain and email"
    echo "2. Install cert-manager if not already installed"
    echo "3. Run the deployment script: ./scripts/deploy.sh"
    echo ""
    log_warn "Keep the generated .env.production.template file secure!"
}

# Main function
main() {
    case "${1:-all}" in
        "postgres")
            check_kubectl
            ensure_namespace
            setup_postgres_secrets
            ;;
        "api")
            check_kubectl
            ensure_namespace
            setup_api_secrets
            ;;
        "web")
            check_kubectl
            ensure_namespace
            setup_web_secrets
            ;;
        "config")
            check_kubectl
            ensure_namespace
            setup_configmaps
            ;;
        "tls")
            check_kubectl
            setup_tls
            ;;
        "all")
            check_kubectl
            ensure_namespace
            setup_postgres_secrets
            setup_api_secrets
            setup_web_secrets
            setup_configmaps
            setup_tls
            generate_env_template
            show_summary
            ;;
        *)
            echo "Usage: $0 {postgres|api|web|config|tls|all}"
            echo ""
            echo "Commands:"
            echo "  postgres - Setup PostgreSQL secrets"
            echo "  api      - Setup API secrets"
            echo "  web      - Setup Web app secrets"
            echo "  config   - Setup ConfigMaps"
            echo "  tls      - Setup TLS certificates"
            echo "  all      - Setup everything (default)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
