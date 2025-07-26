# Policy Issue Extraction System - Backup and Recovery Procedures

## Overview

This document outlines comprehensive backup strategies, recovery procedures, and disaster recovery protocols for the dual-level policy issue extraction system. The procedures ensure data integrity, system availability, and business continuity.

## Backup Strategy

### Data Classification

#### Critical Data (RTO: 1 hour, RPO: 15 minutes)
- **Issues Database**: PostgreSQL tables containing extracted policy issues
- **Airtable Records**: Human-reviewed issue classifications and statuses
- **Configuration Secrets**: API keys, webhook URLs, database credentials
- **Application Configuration**: Service configurations and environment settings

#### Important Data (RTO: 4 hours, RPO: 1 hour)
- **Application Logs**: System and application logs for troubleshooting
- **Metrics Data**: Prometheus time-series data
- **User Sessions**: Redis cache and session data

#### Standard Data (RTO: 24 hours, RPO: 24 hours)
- **Historical Reports**: Daily/weekly system reports
- **Backup Archives**: Compressed historical backups
- **Documentation**: System documentation and runbooks

### Backup Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   PostgreSQL    │───▶│  Daily Backup   │───▶│ Cloud Storage   │
│   Database      │    │   (pg_dump)     │    │  (GCS/S3)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐    ┌─────────────────┐
         │              │ Transaction Log │───▶│   Offsite       │
         │              │    Backup       │    │   Archive       │
         │              └─────────────────┘    └─────────────────┘
         │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Airtable      │───▶│   API Export    │───▶│  Versioned      │
│   Records       │    │   (JSON)        │    │  Storage        │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Configuration  │───▶│ Encrypted Vault │───▶│  Secure Cloud   │
│   & Secrets     │    │    Backup       │    │    Storage      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Database Backup Procedures

### 1. PostgreSQL Automated Backup

#### Daily Full Backup Script

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/postgres_backup.sh

set -euo pipefail

# Configuration
BACKUP_DIR="/opt/backups/postgres"
RETENTION_DAYS=30
DB_NAME="seiji_watch"
DB_USER="seiji_user"
DB_HOST="localhost"
DB_PORT="5432"
GCS_BUCKET="seiji-watch-backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="seiji_watch_${DATE}.sql"
LOG_FILE="/var/log/postgres_backup.log"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Create backup directory
mkdir -p "$BACKUP_DIR"

log "Starting PostgreSQL backup for $DB_NAME"

# Set password from environment
export PGPASSWORD="$POSTGRES_PASSWORD"

# Create full database dump
log "Creating database dump..."
pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
    --verbose --clean --if-exists --create \
    --format=custom --compress=9 \
    "$DB_NAME" > "$BACKUP_DIR/$BACKUP_FILE"

if [ $? -eq 0 ]; then
    log "Database dump completed successfully"
    
    # Compress backup
    log "Compressing backup file..."
    gzip "$BACKUP_DIR/$BACKUP_FILE"
    BACKUP_FILE_GZ="${BACKUP_FILE}.gz"
    
    # Calculate checksum
    CHECKSUM=$(sha256sum "$BACKUP_DIR/$BACKUP_FILE_GZ" | cut -d' ' -f1)
    echo "$CHECKSUM  $BACKUP_FILE_GZ" > "$BACKUP_DIR/${BACKUP_FILE_GZ}.sha256"
    
    # Upload to cloud storage
    log "Uploading to Google Cloud Storage..."
    gsutil cp "$BACKUP_DIR/$BACKUP_FILE_GZ" "gs://$GCS_BUCKET/postgres/daily/"
    gsutil cp "$BACKUP_DIR/${BACKUP_FILE_GZ}.sha256" "gs://$GCS_BUCKET/postgres/daily/"
    
    # Test backup integrity
    log "Testing backup integrity..."
    gunzip -t "$BACKUP_DIR/$BACKUP_FILE_GZ"
    if [ $? -eq 0 ]; then
        log "Backup integrity test passed"
        
        # Create backup metadata
        cat > "$BACKUP_DIR/${BACKUP_FILE_GZ}.meta" << EOF
{
  "backup_date": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "database": "$DB_NAME",
  "size_bytes": $(stat -c%s "$BACKUP_DIR/$BACKUP_FILE_GZ"),
  "checksum_sha256": "$CHECKSUM",
  "backup_type": "full",
  "pg_version": "$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -t -c 'SELECT version();' | head -1 | xargs)"
}
EOF
        gsutil cp "$BACKUP_DIR/${BACKUP_FILE_GZ}.meta" "gs://$GCS_BUCKET/postgres/daily/"
        
    else
        log "ERROR: Backup integrity test failed"
        exit 1
    fi
    
    # Cleanup old local backups
    log "Cleaning up old local backups..."
    find "$BACKUP_DIR" -name "seiji_watch_*.sql.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.sha256" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.meta" -mtime +$RETENTION_DAYS -delete
    
    log "Backup process completed successfully"
    
else
    log "ERROR: Database dump failed"
    exit 1
fi

# Unset password
unset PGPASSWORD
```

#### Continuous WAL Archiving

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/wal_archive.sh

# WAL archiving script for continuous backup
WAL_FILE="$1"
WAL_PATH="$2"
GCS_BUCKET="seiji-watch-backups"

# Upload WAL file to cloud storage
gsutil cp "$WAL_PATH" "gs://$GCS_BUCKET/postgres/wal/"

# Log the archival
echo "$(date) - Archived WAL file: $WAL_FILE" >> /var/log/wal_archive.log
```

#### PostgreSQL Configuration for Archiving

```postgresql
# postgresql.conf settings for WAL archiving
wal_level = replica
archive_mode = on
archive_command = '/opt/seiji-watch/scripts/wal_archive.sh %f %p'
max_wal_senders = 3
wal_keep_segments = 32
checkpoint_completion_target = 0.9
```

### 2. Incremental Backup with pg_basebackup

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/postgres_incremental_backup.sh

set -euo pipefail

BACKUP_DIR="/opt/backups/postgres/incremental"
DATE=$(date +%Y%m%d_%H%M%S)
BASE_BACKUP_DIR="$BACKUP_DIR/base_$DATE"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting incremental backup..."

# Create base backup
mkdir -p "$BASE_BACKUP_DIR"
pg_basebackup -h localhost -D "$BASE_BACKUP_DIR" -Ft -z -P -U replication_user

if [ $? -eq 0 ]; then
    log "Base backup completed successfully"
    
    # Upload to cloud storage
    gsutil -m cp -r "$BASE_BACKUP_DIR" "gs://seiji-watch-backups/postgres/incremental/"
    
    log "Incremental backup uploaded to cloud storage"
else
    log "ERROR: Incremental backup failed"
    exit 1
fi
```

## Airtable Backup Procedures

### 1. Full Airtable Export

```python
#!/usr/bin/env python3
# /opt/seiji-watch/scripts/airtable_backup.py

import os
import json
import gzip
import hashlib
from datetime import datetime
from airtable import Airtable
from google.cloud import storage
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/var/log/airtable_backup.log'),
        logging.StreamHandler()
    ]
)

class AirtableBackup:
    def __init__(self):
        self.api_key = os.environ['AIRTABLE_PAT']
        self.base_id = os.environ['AIRTABLE_BASE_ID']
        self.backup_dir = '/opt/backups/airtable'
        self.gcs_bucket = 'seiji-watch-backups'
        
        # Initialize Airtable client
        self.airtable = Airtable(self.base_id, self.api_key)
        
        # Initialize GCS client
        self.storage_client = storage.Client()
        self.bucket = self.storage_client.bucket(self.gcs_bucket)
        
        # Create backup directory
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def backup_table(self, table_name):
        """Backup a single Airtable table."""
        logging.info(f"Starting backup of table: {table_name}")
        
        try:
            # Fetch all records
            records = self.airtable.get_all(table_name)
            
            # Create backup data structure
            backup_data = {
                "table_name": table_name,
                "backup_timestamp": datetime.utcnow().isoformat(),
                "record_count": len(records),
                "records": records
            }
            
            # Generate filename
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{table_name}_{date_str}.json"
            filepath = os.path.join(self.backup_dir, filename)
            
            # Write to file
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(backup_data, f, indent=2, ensure_ascii=False)
            
            # Compress the file
            compressed_filepath = f"{filepath}.gz"
            with open(filepath, 'rb') as f_in:
                with gzip.open(compressed_filepath, 'wb') as f_out:
                    f_out.writelines(f_in)
            
            # Remove uncompressed file
            os.remove(filepath)
            
            # Calculate checksum
            checksum = self.calculate_checksum(compressed_filepath)
            
            # Upload to cloud storage
            blob_name = f"airtable/{table_name}/{filename}.gz"
            blob = self.bucket.blob(blob_name)
            blob.upload_from_filename(compressed_filepath)
            
            # Upload checksum
            checksum_blob = self.bucket.blob(f"{blob_name}.sha256")
            checksum_blob.upload_from_string(f"{checksum}  {filename}.gz")
            
            # Create metadata
            metadata = {
                "table_name": table_name,
                "backup_timestamp": backup_data["backup_timestamp"],
                "record_count": len(records),
                "file_size": os.path.getsize(compressed_filepath),
                "checksum_sha256": checksum,
                "backup_type": "full"
            }
            
            metadata_blob = self.bucket.blob(f"{blob_name}.meta")
            metadata_blob.upload_from_string(json.dumps(metadata, indent=2))
            
            logging.info(f"Successfully backed up {len(records)} records from {table_name}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to backup table {table_name}: {str(e)}")
            return False
    
    def calculate_checksum(self, filepath):
        """Calculate SHA256 checksum of a file."""
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def backup_all_tables(self):
        """Backup all tables in the base."""
        tables = ['Issues', 'Reviews', 'Users']  # Add all table names
        
        success_count = 0
        for table in tables:
            if self.backup_table(table):
                success_count += 1
        
        logging.info(f"Backup completed: {success_count}/{len(tables)} tables successful")
        return success_count == len(tables)
    
    def cleanup_old_backups(self, retention_days=30):
        """Remove local backups older than retention period."""
        import time
        
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
        
        for filename in os.listdir(self.backup_dir):
            filepath = os.path.join(self.backup_dir, filename)
            if os.path.getctime(filepath) < cutoff_time:
                os.remove(filepath)
                logging.info(f"Removed old backup: {filename}")

if __name__ == "__main__":
    backup = AirtableBackup()
    
    if backup.backup_all_tables():
        logging.info("All Airtable backups completed successfully")
        backup.cleanup_old_backups()
    else:
        logging.error("Some Airtable backups failed")
        exit(1)
```

### 2. Schema Backup

```python
#!/usr/bin/env python3
# /opt/seiji-watch/scripts/airtable_schema_backup.py

import os
import json
import requests
from datetime import datetime
from google.cloud import storage

class AirtableSchemaBackup:
    def __init__(self):
        self.api_key = os.environ['AIRTABLE_PAT']
        self.base_id = os.environ['AIRTABLE_BASE_ID']
        self.headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
    
    def get_base_schema(self):
        """Retrieve the schema for the entire base."""
        url = f"https://api.airtable.com/v0/meta/bases/{self.base_id}/tables"
        
        response = requests.get(url, headers=self.headers)
        response.raise_for_status()
        
        return response.json()
    
    def backup_schema(self):
        """Backup the base schema to cloud storage."""
        try:
            schema = self.get_base_schema()
            
            # Add metadata
            backup_data = {
                "base_id": self.base_id,
                "backup_timestamp": datetime.utcnow().isoformat(),
                "schema": schema
            }
            
            # Save to local file
            date_str = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"airtable_schema_{date_str}.json"
            filepath = f"/opt/backups/airtable/{filename}"
            
            with open(filepath, 'w') as f:
                json.dump(backup_data, f, indent=2)
            
            # Upload to cloud storage
            storage_client = storage.Client()
            bucket = storage_client.bucket('seiji-watch-backups')
            blob = bucket.blob(f"airtable/schema/{filename}")
            blob.upload_from_filename(filepath)
            
            print(f"Schema backup completed: {filename}")
            return True
            
        except Exception as e:
            print(f"Schema backup failed: {str(e)}")
            return False

if __name__ == "__main__":
    schema_backup = AirtableSchemaBackup()
    schema_backup.backup_schema()
```

## Configuration and Secrets Backup

### 1. Kubernetes Secrets Backup

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/k8s_config_backup.sh

set -euo pipefail

BACKUP_DIR="/opt/backups/kubernetes"
DATE=$(date +%Y%m%d_%H%M%S)
GCS_BUCKET="seiji-watch-backups"

# Create backup directory
mkdir -p "$BACKUP_DIR"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting Kubernetes configuration backup"

# Backup secrets
log "Backing up secrets..."
kubectl get secrets -o yaml > "$BACKUP_DIR/secrets_$DATE.yaml"

# Backup configmaps
log "Backing up configmaps..."
kubectl get configmaps -o yaml > "$BACKUP_DIR/configmaps_$DATE.yaml"

# Backup deployments
log "Backing up deployments..."
kubectl get deployments -o yaml > "$BACKUP_DIR/deployments_$DATE.yaml"

# Backup services
log "Backing up services..."
kubectl get services -o yaml > "$BACKUP_DIR/services_$DATE.yaml"

# Backup ingress
log "Backing up ingress..."
kubectl get ingress -o yaml > "$BACKUP_DIR/ingress_$DATE.yaml"

# Create archive
log "Creating backup archive..."
tar -czf "$BACKUP_DIR/k8s_config_$DATE.tar.gz" -C "$BACKUP_DIR" \
    secrets_$DATE.yaml \
    configmaps_$DATE.yaml \
    deployments_$DATE.yaml \
    services_$DATE.yaml \
    ingress_$DATE.yaml

# Upload to cloud storage
log "Uploading to cloud storage..."
gsutil cp "$BACKUP_DIR/k8s_config_$DATE.tar.gz" "gs://$GCS_BUCKET/kubernetes/"

# Cleanup
rm "$BACKUP_DIR"/*.yaml

log "Kubernetes configuration backup completed"
```

### 2. Environment Variables Backup

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/env_backup.sh

set -euo pipefail

BACKUP_DIR="/opt/backups/environment"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Export non-sensitive environment variables
env | grep -E '^(SEIJI_|API_|DATABASE_|REDIS_)' | grep -v -E '(PASSWORD|SECRET|KEY)' > "$BACKUP_DIR/env_vars_$DATE.txt"

# Create encrypted backup of sensitive variables
env | grep -E '(PASSWORD|SECRET|KEY)' | gpg --cipher-algo AES256 --compress-algo 1 --s2k-mode 3 --s2k-digest-algo SHA512 --s2k-count 65536 --symmetric --output "$BACKUP_DIR/env_secrets_$DATE.gpg"

# Upload to secure cloud storage
gsutil cp "$BACKUP_DIR/env_vars_$DATE.txt" "gs://seiji-watch-secure-backups/environment/"
gsutil cp "$BACKUP_DIR/env_secrets_$DATE.gpg" "gs://seiji-watch-secure-backups/environment/"

echo "Environment backup completed"
```

## Application Data Backup

### 1. Redis Backup

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/redis_backup.sh

set -euo pipefail

BACKUP_DIR="/opt/backups/redis"
DATE=$(date +%Y%m%d_%H%M%S)
REDIS_HOST="localhost"
REDIS_PORT="6379"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create Redis backup
redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" BGSAVE

# Wait for backup to complete
while [ "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" = "$(redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" LASTSAVE)" ]; do
    sleep 1
done

# Copy dump file
cp /var/lib/redis/dump.rdb "$BACKUP_DIR/redis_dump_$DATE.rdb"

# Compress backup
gzip "$BACKUP_DIR/redis_dump_$DATE.rdb"

# Upload to cloud storage
gsutil cp "$BACKUP_DIR/redis_dump_$DATE.rdb.gz" "gs://seiji-watch-backups/redis/"

echo "Redis backup completed"
```

### 2. Logs Backup

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/logs_backup.sh

set -euo pipefail

BACKUP_DIR="/opt/backups/logs"
DATE=$(date +%Y%m%d_%H%M%S)
LOG_DIRS="/var/log/seiji-watch /opt/seiji-watch/logs"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Archive logs
tar -czf "$BACKUP_DIR/logs_$DATE.tar.gz" $LOG_DIRS

# Upload to cloud storage
gsutil cp "$BACKUP_DIR/logs_$DATE.tar.gz" "gs://seiji-watch-backups/logs/"

# Cleanup old local log backups
find "$BACKUP_DIR" -name "logs_*.tar.gz" -mtime +7 -delete

echo "Logs backup completed"
```

## Recovery Procedures

### 1. Complete System Recovery

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/complete_system_recovery.sh

set -euo pipefail

RECOVERY_DATE="$1"  # Format: YYYYMMDD_HHMMSS
GCS_BUCKET="seiji-watch-backups"
RECOVERY_DIR="/opt/recovery"

if [ -z "$RECOVERY_DATE" ]; then
    echo "Usage: $0 <RECOVERY_DATE>"
    echo "Example: $0 20240115_140000"
    exit 1
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting complete system recovery for $RECOVERY_DATE"

# Create recovery directory
mkdir -p "$RECOVERY_DIR"

# 1. Stop all services
log "Stopping all services..."
kubectl scale deployment api-gateway --replicas=0
kubectl scale deployment ingest-worker --replicas=0

# 2. Download PostgreSQL backup
log "Downloading PostgreSQL backup..."
gsutil cp "gs://$GCS_BUCKET/postgres/daily/seiji_watch_${RECOVERY_DATE}.sql.gz" "$RECOVERY_DIR/"

# Verify backup integrity
log "Verifying backup integrity..."
gsutil cp "gs://$GCS_BUCKET/postgres/daily/seiji_watch_${RECOVERY_DATE}.sql.gz.sha256" "$RECOVERY_DIR/"
cd "$RECOVERY_DIR"
sha256sum -c "seiji_watch_${RECOVERY_DATE}.sql.gz.sha256"

if [ $? -ne 0 ]; then
    log "ERROR: Backup integrity check failed"
    exit 1
fi

# 3. Restore PostgreSQL database
log "Restoring PostgreSQL database..."
gunzip "seiji_watch_${RECOVERY_DATE}.sql.gz"

# Drop and recreate database
kubectl exec postgres-pod -- dropdb --if-exists seiji_watch
kubectl exec postgres-pod -- createdb seiji_watch

# Restore from backup
kubectl cp "$RECOVERY_DIR/seiji_watch_${RECOVERY_DATE}.sql" postgres-pod:/tmp/
kubectl exec postgres-pod -- psql -U seiji_user seiji_watch -f /tmp/seiji_watch_${RECOVERY_DATE}.sql

# 4. Restore Kubernetes configuration
log "Restoring Kubernetes configuration..."
gsutil cp "gs://$GCS_BUCKET/kubernetes/k8s_config_${RECOVERY_DATE}.tar.gz" "$RECOVERY_DIR/"
tar -xzf "$RECOVERY_DIR/k8s_config_${RECOVERY_DATE}.tar.gz" -C "$RECOVERY_DIR"

kubectl apply -f "$RECOVERY_DIR/secrets_${RECOVERY_DATE}.yaml"
kubectl apply -f "$RECOVERY_DIR/configmaps_${RECOVERY_DATE}.yaml"

# 5. Restore Redis data
log "Restoring Redis data..."
gsutil cp "gs://$GCS_BUCKET/redis/redis_dump_${RECOVERY_DATE}.rdb.gz" "$RECOVERY_DIR/"
gunzip "$RECOVERY_DIR/redis_dump_${RECOVERY_DATE}.rdb.gz"

kubectl cp "$RECOVERY_DIR/redis_dump_${RECOVERY_DATE}.rdb" redis-pod:/data/dump.rdb
kubectl delete pod redis-pod  # Restart Redis to load the dump

# 6. Wait for Redis to restart
log "Waiting for Redis to restart..."
sleep 30

# 7. Restart application services
log "Restarting application services..."
kubectl scale deployment api-gateway --replicas=3
kubectl scale deployment ingest-worker --replicas=2

# 8. Wait for services to be ready
log "Waiting for services to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/api-gateway
kubectl wait --for=condition=available --timeout=300s deployment/ingest-worker

# 9. Verify system health
log "Verifying system health..."
sleep 60

HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.seiji-watch.com/api/issues/health)
if [ "$HEALTH_STATUS" = "200" ]; then
    log "System recovery completed successfully"
    log "Health check passed"
else
    log "WARNING: Health check failed (HTTP $HEALTH_STATUS)"
    log "Manual intervention may be required"
fi

# 10. Send notification
curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"System recovery completed for date: $RECOVERY_DATE\"}"

log "Complete system recovery finished"
```

### 2. Database-Only Recovery

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/database_recovery.sh

set -euo pipefail

BACKUP_DATE="$1"
TARGET_DB="${2:-seiji_watch_recovery}"

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <BACKUP_DATE> [TARGET_DB]"
    exit 1
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting database recovery for $BACKUP_DATE"

# Download backup
gsutil cp "gs://seiji-watch-backups/postgres/daily/seiji_watch_${BACKUP_DATE}.sql.gz" /tmp/

# Verify integrity
gsutil cp "gs://seiji-watch-backups/postgres/daily/seiji_watch_${BACKUP_DATE}.sql.gz.sha256" /tmp/
cd /tmp
sha256sum -c "seiji_watch_${BACKUP_DATE}.sql.gz.sha256"

# Extract backup
gunzip "seiji_watch_${BACKUP_DATE}.sql.gz"

# Create recovery database
kubectl exec postgres-pod -- createdb "$TARGET_DB"

# Restore data
kubectl cp "/tmp/seiji_watch_${BACKUP_DATE}.sql" postgres-pod:/tmp/
kubectl exec postgres-pod -- psql -U seiji_user "$TARGET_DB" -f "/tmp/seiji_watch_${BACKUP_DATE}.sql"

log "Database recovery completed: $TARGET_DB"
```

### 3. Point-in-Time Recovery

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/point_in_time_recovery.sh

set -euo pipefail

BASE_BACKUP_DATE="$1"
RECOVERY_TARGET_TIME="$2"  # Format: YYYY-MM-DD HH:MM:SS

if [ -z "$BASE_BACKUP_DATE" ] || [ -z "$RECOVERY_TARGET_TIME" ]; then
    echo "Usage: $0 <BASE_BACKUP_DATE> '<RECOVERY_TARGET_TIME>'"
    echo "Example: $0 20240115_020000 '2024-01-15 14:30:00'"
    exit 1
fi

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting point-in-time recovery to $RECOVERY_TARGET_TIME"

RECOVERY_DIR="/opt/recovery/pitr"
mkdir -p "$RECOVERY_DIR"

# 1. Download base backup
log "Downloading base backup..."
gsutil -m cp -r "gs://seiji-watch-backups/postgres/incremental/base_$BASE_BACKUP_DATE" "$RECOVERY_DIR/"

# 2. Download WAL files
log "Downloading WAL files..."
gsutil -m cp "gs://seiji-watch-backups/postgres/wal/*" "$RECOVERY_DIR/wal/"

# 3. Configure recovery
cat > "$RECOVERY_DIR/recovery.conf" << EOF
restore_command = 'cp $RECOVERY_DIR/wal/%f %p'
recovery_target_time = '$RECOVERY_TARGET_TIME'
recovery_target_action = 'promote'
EOF

# 4. Stop PostgreSQL
kubectl scale statefulset postgres --replicas=0

# 5. Replace data directory
kubectl exec postgres-pod -- rm -rf /var/lib/postgresql/data/*
kubectl cp "$RECOVERY_DIR/base_$BASE_BACKUP_DATE/*" postgres-pod:/var/lib/postgresql/data/
kubectl cp "$RECOVERY_DIR/recovery.conf" postgres-pod:/var/lib/postgresql/data/

# 6. Start PostgreSQL
kubectl scale statefulset postgres --replicas=1

# 7. Monitor recovery
log "Monitoring recovery progress..."
while true; do
    RECOVERY_STATUS=$(kubectl exec postgres-pod -- psql -U seiji_user -t -c "SELECT pg_is_in_recovery();" 2>/dev/null || echo "error")
    
    if [ "$RECOVERY_STATUS" = " f" ]; then
        log "Point-in-time recovery completed successfully"
        break
    elif [ "$RECOVERY_STATUS" = "error" ]; then
        log "Waiting for PostgreSQL to start..."
    else
        log "Recovery in progress..."
    fi
    
    sleep 10
done

log "Point-in-time recovery finished"
```

## Disaster Recovery

### 1. Cross-Region Replication Setup

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/setup_cross_region_replication.sh

set -euo pipefail

PRIMARY_REGION="us-central1"
DR_REGION="us-east1"
PROJECT_ID="seiji-watch-prod"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Setting up cross-region disaster recovery"

# 1. Create DR Cloud SQL instance
log "Creating DR database instance..."
gcloud sql instances create seiji-watch-dr \
    --database-version=POSTGRES_14 \
    --tier=db-custom-2-4096 \
    --region="$DR_REGION" \
    --availability-type=REGIONAL \
    --backup-start-time=03:00 \
    --enable-bin-log \
    --replica-type=READ

# 2. Create read replica
log "Creating read replica..."
gcloud sql instances create seiji-watch-replica \
    --master-instance-name=seiji-watch-primary \
    --tier=db-custom-2-4096 \
    --region="$DR_REGION" \
    --replica-type=READ

# 3. Set up Cloud Storage replication
log "Setting up storage replication..."
gsutil mb -p "$PROJECT_ID" -c REGIONAL -l "$DR_REGION" gs://seiji-watch-backups-dr

# Configure replication
gsutil rewrite -r gs://seiji-watch-backups/* gs://seiji-watch-backups-dr/

# 4. Deploy DR Kubernetes cluster
log "Creating DR Kubernetes cluster..."
gcloud container clusters create seiji-watch-dr \
    --zone="$DR_REGION-a" \
    --num-nodes=3 \
    --machine-type=e2-standard-2 \
    --enable-autorepair \
    --enable-autoupgrade

# 5. Deploy applications to DR cluster
log "Deploying applications to DR cluster..."
gcloud container clusters get-credentials seiji-watch-dr --zone="$DR_REGION-a"

# Apply configurations (read-only mode)
kubectl apply -f k8s/dr-deployment.yaml

log "Cross-region disaster recovery setup completed"
```

### 2. Failover Procedure

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/disaster_failover.sh

set -euo pipefail

DR_REGION="us-east1"
PRIMARY_REGION="us-central1"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting disaster recovery failover"

# 1. Promote read replica to master
log "Promoting read replica to master..."
gcloud sql instances promote-replica seiji-watch-replica

# 2. Update DNS to point to DR region
log "Updating DNS configuration..."
gcloud dns record-sets transaction start --zone=seiji-watch-zone
gcloud dns record-sets transaction remove --zone=seiji-watch-zone \
    --name=api.seiji-watch.com. --type=A --ttl=300 \
    --data=CURRENT_PRIMARY_IP
gcloud dns record-sets transaction add --zone=seiji-watch-zone \
    --name=api.seiji-watch.com. --type=A --ttl=300 \
    --data=DR_INSTANCE_IP
gcloud dns record-sets transaction execute --zone=seiji-watch-zone

# 3. Switch to DR Kubernetes cluster
log "Switching to DR cluster..."
gcloud container clusters get-credentials seiji-watch-dr --zone="$DR_REGION-a"

# 4. Scale up DR applications
log "Scaling up DR applications..."
kubectl scale deployment api-gateway --replicas=3
kubectl scale deployment ingest-worker --replicas=2

# 5. Update application configuration
log "Updating application configuration..."
kubectl patch configmap app-config -p '{"data":{"DATABASE_HOST":"seiji-watch-replica"}}'

# 6. Verify system health
log "Verifying system health..."
sleep 60

for i in {1..10}; do
    HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://api.seiji-watch.com/api/issues/health || echo "000")
    if [ "$HEALTH_STATUS" = "200" ]; then
        log "DR system is healthy"
        break
    else
        log "Health check attempt $i failed (HTTP $HEALTH_STATUS)"
        sleep 30
    fi
done

# 7. Send notifications
curl -X POST "$SLACK_WEBHOOK_URL" -d "{\"text\":\"🚨 DISASTER RECOVERY ACTIVATED - System failed over to $DR_REGION\"}"
curl -X POST "$EMAIL_WEBHOOK_URL" -d "{\"subject\":\"DR Activated\",\"body\":\"System failed over to DR region\"}"

log "Disaster recovery failover completed"
```

## Monitoring and Validation

### 1. Backup Validation Script

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/validate_backups.sh

set -euo pipefail

GCS_BUCKET="seiji-watch-backups"
VALIDATION_DB="backup_validation_test"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

# Get latest backup
LATEST_BACKUP=$(gsutil ls gs://$GCS_BUCKET/postgres/daily/ | grep "\.sql\.gz$" | sort | tail -1)
BACKUP_FILE=$(basename "$LATEST_BACKUP")

log "Validating backup: $BACKUP_FILE"

# Download and extract
gsutil cp "$LATEST_BACKUP" /tmp/
gsutil cp "${LATEST_BACKUP}.sha256" /tmp/

cd /tmp
sha256sum -c "${BACKUP_FILE}.sha256"

if [ $? -ne 0 ]; then
    log "ERROR: Backup integrity check failed"
    exit 1
fi

# Test restore
gunzip "$BACKUP_FILE"
BACKUP_SQL="${BACKUP_FILE%.gz}"

# Create test database and restore
kubectl exec postgres-pod -- createdb "$VALIDATION_DB"
kubectl cp "/tmp/$BACKUP_SQL" postgres-pod:/tmp/
kubectl exec postgres-pod -- psql -U seiji_user "$VALIDATION_DB" -f "/tmp/$BACKUP_SQL"

# Validate data
RECORD_COUNT=$(kubectl exec postgres-pod -- psql -U seiji_user "$VALIDATION_DB" -t -c "SELECT COUNT(*) FROM issues;")

if [ "$RECORD_COUNT" -gt 0 ]; then
    log "Backup validation successful: $RECORD_COUNT records restored"
else
    log "ERROR: Backup validation failed: No records found"
    exit 1
fi

# Cleanup
kubectl exec postgres-pod -- dropdb "$VALIDATION_DB"
rm "/tmp/$BACKUP_SQL"

log "Backup validation completed successfully"
```

### 2. Recovery Testing

```bash
#!/bin/bash
# /opt/seiji-watch/scripts/test_recovery.sh

set -euo pipefail

TEST_NAMESPACE="recovery-test"
TEST_DB="recovery_test_db"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1"
}

log "Starting recovery test"

# Create test namespace
kubectl create namespace "$TEST_NAMESPACE"

# Deploy test PostgreSQL instance
kubectl apply -n "$TEST_NAMESPACE" -f - << EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-test
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-test
  template:
    metadata:
      labels:
        app: postgres-test
    spec:
      containers:
      - name: postgres
        image: postgres:14
        env:
        - name: POSTGRES_DB
          value: "$TEST_DB"
        - name: POSTGRES_USER
          value: "test_user"
        - name: POSTGRES_PASSWORD
          value: "test_password"
EOF

# Wait for deployment
kubectl wait -n "$TEST_NAMESPACE" --for=condition=available --timeout=300s deployment/postgres-test

# Test complete recovery procedure
./complete_system_recovery.sh "$(date -d '1 day ago' +%Y%m%d_%H%M%S)" "$TEST_NAMESPACE"

# Validate recovery
# ... validation logic ...

# Cleanup
kubectl delete namespace "$TEST_NAMESPACE"

log "Recovery test completed"
```

This comprehensive backup and recovery documentation ensures robust data protection and system resilience for the policy issue extraction system.