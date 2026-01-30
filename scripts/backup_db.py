#!/usr/bin/env python3
"""
Database Backup Script for Cerberus CTF Platform
Dumps PostgreSQL -> Compresses with gzip -> Uploads to S3 (MinIO)
"""

import os
import sys
import gzip
import shutil
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import boto3
from botocore.exceptions import ClientError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/cerberus/backup.log')
    ]
)
logger = logging.getLogger(__name__)


class DatabaseBackup:
    """Handles database backup operations."""
    
    def __init__(self):
        self.db_host = os.getenv('POSTGRES_HOST', 'localhost')
        self.db_port = os.getenv('POSTGRES_PORT', '5432')
        self.db_name = os.getenv('POSTGRES_DB', 'cerberus')
        self.db_user = os.getenv('POSTGRES_USER', 'cerberus')
        self.db_password = os.getenv('POSTGRES_PASSWORD', '')
        
        self.s3_endpoint = os.getenv('S3_ENDPOINT', 'http://localhost:9000')
        self.s3_access_key = os.getenv('S3_ACCESS_KEY', '')
        self.s3_secret_key = os.getenv('S3_SECRET_KEY', '')
        self.s3_bucket = os.getenv('S3_BUCKET', 'cerberus-backups')
        self.s3_secure = os.getenv('S3_SECURE', 'false').lower() == 'true'
        
        self.backup_dir = Path(os.getenv('BACKUP_DIR', '/tmp/backups'))
        self.retention_days = int(os.getenv('BACKUP_RETENTION_DAYS', '30'))
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
    def dump_database(self) -> Path:
        """Dump PostgreSQL database to SQL file."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        dump_file = self.backup_dir / f"{self.db_name}_{timestamp}.sql"
        
        env = os.environ.copy()
        env['PGPASSWORD'] = self.db_password
        
        cmd = [
            'pg_dump',
            '-h', self.db_host,
            '-p', self.db_port,
            '-U', self.db_user,
            '-d', self.db_name,
            '-F', 'plain',
            '-v',
            '-f', str(dump_file)
        ]
        
        logger.info(f"Starting database dump: {dump_file.name}")
        
        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            logger.info(f"Database dump completed: {dump_file.stat().st_size} bytes")
            return dump_file
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Database dump failed: {e.stderr}")
            raise
    
    def compress_file(self, source_file: Path) -> Path:
        """Compress file with gzip."""
        compressed_file = source_file.with_suffix('.sql.gz')
        
        logger.info(f"Compressing {source_file.name}...")
        
        try:
            with open(source_file, 'rb') as f_in:
                with gzip.open(compressed_file, 'wb', compresslevel=6) as f_out:
                    shutil.copyfileobj(f_in, f_out)
            
            original_size = source_file.stat().st_size
            compressed_size = compressed_file.stat().st_size
            ratio = (1 - compressed_size / original_size) * 100
            
            logger.info(
                f"Compression complete: {original_size} -> {compressed_size} bytes "
                f"({ratio:.1f}% reduction)"
            )
            
            # Remove original dump file
            source_file.unlink()
            
            return compressed_file
            
        except Exception as e:
            logger.error(f"Compression failed: {e}")
            raise
    
    def upload_to_s3(self, file_path: Path) -> str:
        """Upload file to S3 (MinIO)."""
        logger.info(f"Uploading to S3: {file_path.name}")
        
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=self.s3_endpoint,
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
                use_ssl=self.s3_secure
            )
            
            # Ensure bucket exists
            try:
                s3_client.head_bucket(Bucket=self.s3_bucket)
            except ClientError:
                logger.info(f"Creating S3 bucket: {self.s3_bucket}")
                s3_client.create_bucket(Bucket=self.s3_bucket)
            
            # Upload with metadata
            s3_key = f"backups/{file_path.name}"
            s3_client.upload_file(
                str(file_path),
                self.s3_bucket,
                s3_key,
                ExtraArgs={
                    'Metadata': {
                        'backup-date': datetime.now().isoformat(),
                        'database': self.db_name,
                        'retention-days': str(self.retention_days)
                    }
                }
            )
            
            logger.info(f"Upload complete: s3://{self.s3_bucket}/{s3_key}")
            return s3_key
            
        except Exception as e:
            logger.error(f"S3 upload failed: {e}")
            raise
    
    def cleanup_old_backups(self) -> int:
        """Remove old backups from S3 based on retention policy."""
        logger.info(f"Cleaning up backups older than {self.retention_days} days")
        
        try:
            s3_client = boto3.client(
                's3',
                endpoint_url=self.s3_endpoint,
                aws_access_key_id=self.s3_access_key,
                aws_secret_access_key=self.s3_secret_key,
                use_ssl=self.s3_secure
            )
            
            cutoff_date = datetime.now() - timedelta(days=self.retention_days)
            deleted_count = 0
            
            response = s3_client.list_objects_v2(
                Bucket=self.s3_bucket,
                Prefix='backups/'
            )
            
            if 'Contents' not in response:
                logger.info("No backups found for cleanup")
                return 0
            
            for obj in response['Contents']:
                if obj['LastModified'].replace(tzinfo=None) < cutoff_date:
                    s3_client.delete_object(
                        Bucket=self.s3_bucket,
                        Key=obj['Key']
                    )
                    logger.info(f"Deleted old backup: {obj['Key']}")
                    deleted_count += 1
            
            logger.info(f"Cleanup complete: {deleted_count} backups removed")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
            return 0
    
    def run(self) -> bool:
        """Execute full backup workflow."""
        try:
            logger.info("=" * 50)
            logger.info("Starting database backup")
            logger.info("=" * 50)
            
            # Step 1: Dump database
            dump_file = self.dump_database()
            
            # Step 2: Compress
            compressed_file = self.compress_file(dump_file)
            
            # Step 3: Upload to S3
            s3_key = self.upload_to_s3(compressed_file)
            
            # Step 4: Cleanup local file
            compressed_file.unlink()
            logger.info(f"Local backup file removed: {compressed_file.name}")
            
            # Step 5: Cleanup old S3 backups
            self.cleanup_old_backups()
            
            logger.info("=" * 50)
            logger.info("Backup completed successfully")
            logger.info("=" * 50)
            
            return True
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return False


def main():
    """Main entry point."""
    backup = DatabaseBackup()
    success = backup.run()
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
