# 🚀 NanoDesigner Production Deployment Guide

This guide provides step-by-step instructions for deploying NanoDesigner to production using Kubernetes.

## 📋 Prerequisites

### Required Tools
- `kubectl` (Kubernetes CLI)
- `docker` (Container runtime)
- `openssl` (For generating secrets)
- `curl` and `jq` (For testing)

### Required Services
- Kubernetes cluster (1.20+)
- Container registry (Docker Hub, ECR, etc.)
- Domain name with DNS control
- SSL certificate (or cert-manager for automatic certificates)

### Required API Keys
- OpenRouter API key (for AI models)
- Gemini API key (for Google AI)
- Langfuse keys (optional, for monitoring)
- PostHog key (optional, for analytics)
- Sentry DSN (optional, for error tracking)

## 🏗️ Infrastructure Requirements

### Minimum Resources
- **CPU**: 4 cores total
- **Memory**: 8GB RAM total
- **Storage**: 50GB persistent storage
- **Network**: Load balancer support

### Recommended Production Resources
- **CPU**: 8+ cores
- **Memory**: 16GB+ RAM
- **Storage**: 100GB+ SSD storage
- **Network**: CDN integration

## 🔧 Step-by-Step Deployment

### Step 1: Prepare Your Environment

1. **Clone the repository**:
   ```bash
   git clone <your-repo-url>
   cd NanoDesigner
   ```

2. **Configure kubectl**:
   ```bash
   kubectl config current-context
   # Ensure you're connected to the correct cluster
   ```

3. **Update domain configuration**:
   ```bash
   # Edit k8s/ingress.yaml
   # Replace 'yourdomain.com' and 'api.yourdomain.com' with your domains
   # Replace 'admin@yourdomain.com' with your email for Let's Encrypt
   ```

### Step 2: Set Up Secrets and Configuration

1. **Run the secrets setup script**:
   ```bash
   ./scripts/setup-secrets.sh
   ```
   
   This will prompt you for:
   - Database credentials
   - API keys (OpenRouter, Gemini)
   - Monitoring keys (Langfuse, PostHog, Sentry)
   - Domain configuration

2. **Verify secrets were created**:
   ```bash
   kubectl get secrets -n nanodesigner
   kubectl get configmaps -n nanodesigner
   ```

### Step 3: Build and Push Docker Images

1. **Set your container registry**:
   ```bash
   export DOCKER_REGISTRY="your-registry.com/nanodesigner"
   # Or use Docker Hub: export DOCKER_REGISTRY="your-dockerhub-username"
   ```

2. **Build and push images**:
   ```bash
   ./scripts/deploy.sh build
   ./scripts/deploy.sh push
   ```

### Step 4: Deploy Infrastructure

1. **Deploy database and caching services**:
   ```bash
   ./scripts/deploy.sh infra
   ```

2. **Wait for infrastructure to be ready**:
   ```bash
   kubectl get pods -n nanodesigner -w
   # Wait until all pods show "Running" status
   ```

### Step 5: Run Database Migrations

1. **Run initial migrations**:
   ```bash
   ./scripts/migrate.sh migrate
   ```

2. **Optionally seed demo data**:
   ```bash
   ./scripts/migrate.sh seed
   ```

### Step 6: Deploy Applications

1. **Deploy API and Web applications**:
   ```bash
   ./scripts/deploy.sh apps
   ```

2. **Deploy ingress controller**:
   ```bash
   ./scripts/deploy.sh ingress
   ```

### Step 7: Configure DNS

1. **Get the load balancer IP**:
   ```bash
   kubectl get ingress -n nanodesigner
   ```

2. **Update your DNS records**:
   - Point `yourdomain.com` to the load balancer IP
   - Point `api.yourdomain.com` to the load balancer IP

### Step 8: Verify Deployment

1. **Run smoke tests**:
   ```bash
   ./scripts/smoke-test.sh all
   ```

2. **Check application status**:
   ```bash
   kubectl get all -n nanodesigner
   ```

3. **Test in browser**:
   - Visit `https://yourdomain.com`
   - Verify API at `https://api.yourdomain.com/docs`

## 🔍 Monitoring and Maintenance

### Health Checks
- API Health: `https://api.yourdomain.com/health`
- API Metrics: `https://api.yourdomain.com/metrics`
- Kubernetes Dashboard: `kubectl proxy`

### Log Monitoring
```bash
# View API logs
kubectl logs -f deployment/api -n nanodesigner

# View Web logs
kubectl logs -f deployment/web -n nanodesigner

# View database logs
kubectl logs -f deployment/postgres -n nanodesigner
```

### Scaling
```bash
# Scale API horizontally
kubectl scale deployment api --replicas=5 -n nanodesigner

# Scale Web horizontally
kubectl scale deployment web --replicas=3 -n nanodesigner
```

### Updates
```bash
# Build new images with version tag
export VERSION="v1.1.0"
./scripts/deploy.sh build

# Rolling update
kubectl set image deployment/api api=your-registry/api:v1.1.0 -n nanodesigner
kubectl set image deployment/web web=your-registry/web:v1.1.0 -n nanodesigner
```

## 🛡️ Security Considerations

### SSL/TLS
- Certificates are automatically managed by cert-manager
- All traffic is redirected to HTTPS
- HSTS headers are enabled

### Network Security
- Rate limiting is configured in nginx
- CORS policies are enforced
- Security headers are set

### Secrets Management
- All secrets are stored in Kubernetes secrets
- Database passwords are auto-generated
- API keys are encrypted at rest

### Input Validation
- All user inputs are sanitized
- Request size limits are enforced
- SQL injection protection is active

## 🚨 Troubleshooting

### Common Issues

1. **Pods not starting**:
   ```bash
   kubectl describe pod <pod-name> -n nanodesigner
   kubectl logs <pod-name> -n nanodesigner
   ```

2. **Database connection issues**:
   ```bash
   kubectl exec -it deployment/postgres -n nanodesigner -- psql -U postgres -d nanodesigner
   ```

3. **SSL certificate issues**:
   ```bash
   kubectl get certificates -n nanodesigner
   kubectl describe certificate nanodesigner-tls -n nanodesigner
   ```

4. **Ingress not working**:
   ```bash
   kubectl get ingress -n nanodesigner
   kubectl describe ingress nanodesigner-ingress -n nanodesigner
   ```

### Performance Issues
- Check resource usage: `kubectl top pods -n nanodesigner`
- Review HPA status: `kubectl get hpa -n nanodesigner`
- Monitor metrics: Access Prometheus/Grafana dashboards

### Backup and Recovery
```bash
# Create database backup
./scripts/migrate.sh backup

# Restore from backup (manual process)
kubectl exec -it deployment/postgres -n nanodesigner -- psql -U postgres -d nanodesigner < backup.sql
```

## 📊 Production Checklist

### Pre-Launch
- [ ] All secrets configured
- [ ] DNS records updated
- [ ] SSL certificates valid
- [ ] Smoke tests passing
- [ ] Performance tests completed
- [ ] Security scan passed
- [ ] Backup strategy in place
- [ ] Monitoring configured
- [ ] Team trained on operations

### Post-Launch
- [ ] Monitor error rates
- [ ] Check performance metrics
- [ ] Verify user flows
- [ ] Monitor resource usage
- [ ] Review logs for issues
- [ ] Test backup/restore procedures

## 🆘 Emergency Procedures

### Rollback Deployment
```bash
# Rollback to previous version
kubectl rollout undo deployment/api -n nanodesigner
kubectl rollout undo deployment/web -n nanodesigner
```

### Scale Down for Maintenance
```bash
# Scale to zero for maintenance
kubectl scale deployment api --replicas=0 -n nanodesigner
kubectl scale deployment web --replicas=0 -n nanodesigner
```

### Emergency Database Access
```bash
# Direct database access
kubectl port-forward svc/postgres 5432:5432 -n nanodesigner
psql -h localhost -U postgres -d nanodesigner
```

## 📞 Support

For deployment issues:
1. Check this guide first
2. Review application logs
3. Check Kubernetes events
4. Consult the troubleshooting section
5. Contact the development team

---

**🎉 Congratulations! Your NanoDesigner production deployment is complete!**
