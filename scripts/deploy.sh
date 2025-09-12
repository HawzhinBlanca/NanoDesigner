#!/bin/bash

# NanoDesigner Production Deployment Script
set -e

echo "🚀 Starting NanoDesigner Production Deployment"
echo "=============================================="

# Configuration
NAMESPACE="nanodesigner"
DOCKER_REGISTRY="${DOCKER_REGISTRY:-nanodesigner}"
VERSION="${VERSION:-$(git rev-parse --short HEAD)}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    command -v kubectl >/dev/null 2>&1 || { log_error "kubectl is required but not installed. Aborting."; exit 1; }
    command -v docker >/dev/null 2>&1 || { log_error "docker is required but not installed. Aborting."; exit 1; }
    
    # Check if kubectl can connect to cluster
    kubectl cluster-info >/dev/null 2>&1 || { log_error "Cannot connect to Kubernetes cluster. Aborting."; exit 1; }
    
    log_info "Prerequisites check passed ✓"
}

# Build Docker images
build_images() {
    log_info "Building Docker images..."
    
    # Build API image
    log_info "Building API image..."
    docker build -f docker/api.Dockerfile -t ${DOCKER_REGISTRY}/api:${VERSION} -t ${DOCKER_REGISTRY}/api:latest .
    
    # Build Web image
    log_info "Building Web image..."
    docker build -f docker/web.Dockerfile -t ${DOCKER_REGISTRY}/web:${VERSION} -t ${DOCKER_REGISTRY}/web:latest .
    
    log_info "Docker images built successfully ✓"
}

# Push images to registry
push_images() {
    log_info "Pushing images to registry..."
    
    docker push ${DOCKER_REGISTRY}/api:${VERSION}
    docker push ${DOCKER_REGISTRY}/api:latest
    docker push ${DOCKER_REGISTRY}/web:${VERSION}
    docker push ${DOCKER_REGISTRY}/web:latest
    
    log_info "Images pushed successfully ✓"
}

# Create namespace if it doesn't exist
create_namespace() {
    log_info "Creating namespace if it doesn't exist..."
    kubectl apply -f k8s/namespace.yaml
    log_info "Namespace ready ✓"
}

# Deploy infrastructure components
deploy_infrastructure() {
    log_info "Deploying infrastructure components..."
    
    # Deploy PostgreSQL
    log_info "Deploying PostgreSQL..."
    kubectl apply -f k8s/postgres.yaml
    
    # Deploy Redis
    log_info "Deploying Redis..."
    kubectl apply -f k8s/redis.yaml
    
    # Deploy Qdrant
    log_info "Deploying Qdrant..."
    kubectl apply -f k8s/qdrant.yaml
    
    log_info "Infrastructure components deployed ✓"
}

# Wait for infrastructure to be ready
wait_for_infrastructure() {
    log_info "Waiting for infrastructure to be ready..."
    
    kubectl wait --for=condition=ready pod -l app=postgres -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=ready pod -l app=redis -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=ready pod -l app=qdrant -n ${NAMESPACE} --timeout=300s
    
    log_info "Infrastructure is ready ✓"
}

# Deploy applications
deploy_applications() {
    log_info "Deploying applications..."
    
    # Update image tags in manifests
    sed -i.bak "s|image: nanodesigner/api:latest|image: ${DOCKER_REGISTRY}/api:${VERSION}|g" k8s/api.yaml
    sed -i.bak "s|image: nanodesigner/web:latest|image: ${DOCKER_REGISTRY}/web:${VERSION}|g" k8s/web.yaml
    
    # Deploy API
    log_info "Deploying API..."
    kubectl apply -f k8s/api.yaml
    
    # Deploy Web
    log_info "Deploying Web..."
    kubectl apply -f k8s/web.yaml
    
    # Restore original manifests
    mv k8s/api.yaml.bak k8s/api.yaml
    mv k8s/web.yaml.bak k8s/web.yaml
    
    log_info "Applications deployed ✓"
}

# Wait for applications to be ready
wait_for_applications() {
    log_info "Waiting for applications to be ready..."
    
    kubectl wait --for=condition=ready pod -l app=api -n ${NAMESPACE} --timeout=300s
    kubectl wait --for=condition=ready pod -l app=web -n ${NAMESPACE} --timeout=300s
    
    log_info "Applications are ready ✓"
}

# Deploy ingress
deploy_ingress() {
    log_info "Deploying ingress..."
    kubectl apply -f k8s/ingress.yaml
    log_info "Ingress deployed ✓"
}

# Run smoke tests
run_smoke_tests() {
    log_info "Running smoke tests..."
    
    # Get API service URL
    API_URL=$(kubectl get svc api -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$API_URL" ]; then
        API_URL="localhost"
        kubectl port-forward svc/api 8000:8000 -n ${NAMESPACE} &
        PORT_FORWARD_PID=$!
        sleep 5
    fi
    
    # Test API health
    if curl -f http://${API_URL}:8000/health >/dev/null 2>&1; then
        log_info "API health check passed ✓"
    else
        log_error "API health check failed ✗"
        [ ! -z "$PORT_FORWARD_PID" ] && kill $PORT_FORWARD_PID
        exit 1
    fi
    
    # Test Web health
    WEB_URL=$(kubectl get svc web -n ${NAMESPACE} -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
    if [ -z "$WEB_URL" ]; then
        WEB_URL="localhost"
        kubectl port-forward svc/web 3000:3000 -n ${NAMESPACE} &
        WEB_PORT_FORWARD_PID=$!
        sleep 5
    fi
    
    if curl -f http://${WEB_URL}:3000/ >/dev/null 2>&1; then
        log_info "Web health check passed ✓"
    else
        log_error "Web health check failed ✗"
        [ ! -z "$WEB_PORT_FORWARD_PID" ] && kill $WEB_PORT_FORWARD_PID
        exit 1
    fi
    
    # Cleanup port forwards
    [ ! -z "$PORT_FORWARD_PID" ] && kill $PORT_FORWARD_PID
    [ ! -z "$WEB_PORT_FORWARD_PID" ] && kill $WEB_PORT_FORWARD_PID
    
    log_info "Smoke tests passed ✓"
}

# Display deployment status
show_status() {
    log_info "Deployment Status:"
    echo "=================="
    
    kubectl get pods -n ${NAMESPACE}
    echo ""
    kubectl get services -n ${NAMESPACE}
    echo ""
    kubectl get ingress -n ${NAMESPACE}
    
    echo ""
    log_info "🎉 Deployment completed successfully!"
    log_info "Frontend: https://yourdomain.com"
    log_info "API: https://api.yourdomain.com"
    log_info "Version: ${VERSION}"
}

# Main deployment flow
main() {
    case "${1:-all}" in
        "build")
            check_prerequisites
            build_images
            ;;
        "push")
            push_images
            ;;
        "infra")
            create_namespace
            deploy_infrastructure
            wait_for_infrastructure
            ;;
        "apps")
            deploy_applications
            wait_for_applications
            ;;
        "ingress")
            deploy_ingress
            ;;
        "test")
            run_smoke_tests
            ;;
        "all")
            check_prerequisites
            build_images
            push_images
            create_namespace
            deploy_infrastructure
            wait_for_infrastructure
            deploy_applications
            wait_for_applications
            deploy_ingress
            run_smoke_tests
            show_status
            ;;
        *)
            echo "Usage: $0 {build|push|infra|apps|ingress|test|all}"
            echo ""
            echo "Commands:"
            echo "  build   - Build Docker images"
            echo "  push    - Push images to registry"
            echo "  infra   - Deploy infrastructure (DB, Redis, Qdrant)"
            echo "  apps    - Deploy applications (API, Web)"
            echo "  ingress - Deploy ingress controller"
            echo "  test    - Run smoke tests"
            echo "  all     - Run complete deployment (default)"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"
