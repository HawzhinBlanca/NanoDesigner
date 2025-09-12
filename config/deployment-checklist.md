# Production Deployment Checklist

## ✅ Phase 1: Code Preparation (COMPLETED)
- [x] Fixed React hook errors in frontend
- [x] Removed demo mode from all components
- [x] Updated API client to use real backend
- [x] Updated auth service for production
- [x] Updated file upload to use real endpoints

## 🔄 Phase 2: Infrastructure Setup (IN PROGRESS)

### Environment Configuration
- [ ] Set up production environment variables
- [ ] Configure API base URL for production
- [ ] Set up authentication secrets
- [ ] Configure database connections
- [ ] Set up Redis for caching
- [ ] Configure vector database (Qdrant)

### Backend Services
- [ ] Deploy FastAPI backend
- [ ] Set up PostgreSQL database
- [ ] Deploy Redis instance
- [ ] Deploy Qdrant vector database
- [ ] Configure storage (R2/S3)

### Frontend Deployment
- [ ] Build production frontend
- [ ] Configure Next.js for production
- [ ] Set up CDN for static assets
- [ ] Configure domain and SSL

### Monitoring & Observability
- [ ] Set up Langfuse for AI monitoring
- [ ] Configure PostHog analytics
- [ ] Set up Sentry error tracking
- [ ] Configure Prometheus metrics
- [ ] Set up Grafana dashboards

## 📋 Phase 3: Security & Compliance
- [ ] Enable HTTPS everywhere
- [ ] Configure CORS policies
- [ ] Set up rate limiting
- [ ] Enable input sanitization
- [ ] Configure secrets management
- [ ] Set up backup strategies

## 🧪 Phase 4: Testing & Validation
- [ ] Run smoke tests
- [ ] Perform load testing
- [ ] Validate all API endpoints
- [ ] Test authentication flows
- [ ] Verify file upload functionality
- [ ] Test AI generation pipeline

## 🚀 Phase 5: Go-Live
- [ ] Blue-green deployment
- [ ] DNS cutover
- [ ] Monitor system health
- [ ] Validate user flows
- [ ] Performance monitoring

## Production URLs
- Frontend: https://yourdomain.com
- API: https://api.yourdomain.com
- Admin: https://yourdomain.com/admin

## Key Environment Variables for Production
```bash
# Frontend (.env.production)
NEXT_PUBLIC_DEMO_MODE=false
NEXT_PUBLIC_API_BASE=https://api.yourdomain.com
NEXTAUTH_URL=https://yourdomain.com
NEXTAUTH_SECRET=your-secure-secret-here

# Backend
DATABASE_URL=postgresql://user:pass@db:5432/nanodesigner
REDIS_URL=redis://redis:6379
QDRANT_URL=http://qdrant:6333
OPENROUTER_API_KEY=your-key
GEMINI_API_KEY=your-key
```
