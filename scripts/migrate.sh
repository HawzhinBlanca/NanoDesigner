#!/bin/bash

# NanoDesigner Database Migration Script
set -e

echo "🗄️ NanoDesigner Database Migration"
echo "=================================="

NAMESPACE="nanodesigner"
MIGRATION_DIR="infra/migrations"

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
    
    if ! command -v kubectl &> /dev/null; then
        log_error "kubectl is required but not installed"
        exit 1
    fi
    
    if ! kubectl cluster-info &> /dev/null; then
        log_error "Cannot connect to Kubernetes cluster"
        exit 1
    fi
    
    log_info "Prerequisites check passed ✓"
}

# Wait for PostgreSQL to be ready
wait_for_postgres() {
    log_info "Waiting for PostgreSQL to be ready..."
    
    kubectl wait --for=condition=ready pod -l app=postgres -n $NAMESPACE --timeout=300s
    
    log_info "PostgreSQL is ready ✓"
}

# Create migration job
create_migration_job() {
    local migration_type="$1"
    
    log_info "Creating migration job for: $migration_type"
    
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-migration-$(date +%s)
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: migration
        image: postgres:15-alpine
        command:
        - /bin/sh
        - -c
        - |
          set -e
          echo "Starting database migration..."
          
          # Wait for PostgreSQL to be ready
          until pg_isready -h postgres -p 5432 -U postgres; do
            echo "Waiting for PostgreSQL..."
            sleep 2
          done
          
          echo "PostgreSQL is ready, running migrations..."
          
          # Run initial schema if this is the first migration
          if [ "$migration_type" = "initial" ]; then
            psql -h postgres -U postgres -d nanodesigner -f /migrations/001_initial.sql
          fi
          
          echo "Migration completed successfully!"
        env:
        - name: PGPASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: migrations
          mountPath: /migrations
      volumes:
      - name: migrations
        configMap:
          name: db-migrations
EOF
    
    log_info "Migration job created ✓"
}

# Create migrations ConfigMap
create_migrations_configmap() {
    log_info "Creating migrations ConfigMap..."
    
    kubectl create configmap db-migrations \
        --from-file=$MIGRATION_DIR/ \
        --namespace=$NAMESPACE \
        --dry-run=client -o yaml | kubectl apply -f -
    
    log_info "Migrations ConfigMap created ✓"
}

# Run Alembic migrations (for Python/SQLAlchemy)
run_alembic_migrations() {
    log_info "Running Alembic migrations..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: alembic-migration-$(date +%s)
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: alembic
        image: nanodesigner/api:latest
        command:
        - /bin/sh
        - -c
        - |
          set -e
          echo "Running Alembic migrations..."
          
          # Wait for PostgreSQL
          until pg_isready -h postgres -p 5432 -U postgres; do
            echo "Waiting for PostgreSQL..."
            sleep 2
          done
          
          # Run Alembic upgrade
          cd /app
          alembic upgrade head
          
          echo "Alembic migrations completed!"
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: api-config
              key: DATABASE_URL
EOF
    
    log_info "Alembic migration job created ✓"
}

# Check migration status
check_migration_status() {
    log_info "Checking migration status..."
    
    # Get the latest migration job
    LATEST_JOB=$(kubectl get jobs -n $NAMESPACE --sort-by=.metadata.creationTimestamp -o name | grep migration | tail -1)
    
    if [ -n "$LATEST_JOB" ]; then
        kubectl wait --for=condition=complete $LATEST_JOB -n $NAMESPACE --timeout=300s
        
        if kubectl get $LATEST_JOB -n $NAMESPACE -o jsonpath='{.status.conditions[?(@.type=="Complete")].status}' | grep -q "True"; then
            log_info "Migration completed successfully ✓"
        else
            log_error "Migration failed ✗"
            kubectl logs -n $NAMESPACE job/$(basename $LATEST_JOB)
            exit 1
        fi
    else
        log_warn "No migration jobs found"
    fi
}

# Backup database before migration
backup_database() {
    log_info "Creating database backup..."
    
    BACKUP_NAME="backup-$(date +%Y%m%d-%H%M%S)"
    
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: db-backup-$(date +%s)
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: backup
        image: postgres:15-alpine
        command:
        - /bin/sh
        - -c
        - |
          set -e
          echo "Creating database backup: $BACKUP_NAME"
          
          pg_dump -h postgres -U postgres -d nanodesigner > /backup/$BACKUP_NAME.sql
          
          echo "Backup created successfully: $BACKUP_NAME.sql"
        env:
        - name: PGPASSWORD
          valueFrom:
            secretKeyRef:
              name: postgres-secret
              key: POSTGRES_PASSWORD
        volumeMounts:
        - name: backup-storage
          mountPath: /backup
      volumes:
      - name: backup-storage
        emptyDir: {}
EOF
    
    log_info "Database backup job created ✓"
}

# Seed demo data
seed_demo_data() {
    log_info "Seeding demo data..."
    
    cat <<EOF | kubectl apply -f -
apiVersion: batch/v1
kind: Job
metadata:
  name: seed-demo-$(date +%s)
  namespace: $NAMESPACE
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
      - name: seed
        image: nanodesigner/api:latest
        command:
        - /bin/sh
        - -c
        - |
          set -e
          echo "Seeding demo data..."
          
          # Wait for database
          until pg_isready -h postgres -p 5432 -U postgres; do
            echo "Waiting for PostgreSQL..."
            sleep 2
          done
          
          # Run seed script
          python -c "
          import asyncio
          from app.services.startup import seed_demo_data
          
          async def main():
              await seed_demo_data()
              print('Demo data seeded successfully!')
          
          asyncio.run(main())
          "
        env:
        - name: DATABASE_URL
          valueFrom:
            configMapKeyRef:
              name: api-config
              key: DATABASE_URL
        - name: REDIS_URL
          valueFrom:
            configMapKeyRef:
              name: api-config
              key: REDIS_URL
EOF
    
    log_info "Demo data seeding job created ✓"
}

# Main function
main() {
    case "${1:-migrate}" in
        "backup")
            check_prerequisites
            wait_for_postgres
            backup_database
            ;;
        "initial")
            check_prerequisites
            wait_for_postgres
            create_migrations_configmap
            create_migration_job "initial"
            check_migration_status
            ;;
        "alembic")
            check_prerequisites
            wait_for_postgres
            run_alembic_migrations
            check_migration_status
            ;;
        "seed")
            check_prerequisites
            wait_for_postgres
            seed_demo_data
            ;;
        "status")
            check_migration_status
            ;;
        "migrate")
            check_prerequisites
            wait_for_postgres
            backup_database
            create_migrations_configmap
            run_alembic_migrations
            check_migration_status
            log_info "🎉 Database migration completed successfully!"
            ;;
        *)
            echo "Usage: $0 {backup|initial|alembic|seed|status|migrate}"
            echo ""
            echo "Commands:"
            echo "  backup   - Create database backup"
            echo "  initial  - Run initial schema migration"
            echo "  alembic  - Run Alembic migrations"
            echo "  seed     - Seed demo data"
            echo "  status   - Check migration status"
            echo "  migrate  - Run full migration (default)"
            exit 1
            ;;
    esac
}

# Run main function
main "$@"
