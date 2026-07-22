"""M21: Storage abstraction layer (local vs S3)."""

from abc import ABC, abstractmethod
import os


class StorageAdapter(ABC):
    """Abstract storage adapter interface."""

    @abstractmethod
    def upload(self, file_key, file_content):
        """Upload file content to storage."""
        pass

    @abstractmethod
    def download(self, file_key):
        """Download file content from storage."""
        pass

    @abstractmethod
    def delete(self, file_key):
        """Delete file from storage."""
        pass

    @abstractmethod
    def exists(self, file_key):
        """Check if file exists in storage."""
        pass


class LocalStorageAdapter(StorageAdapter):
    """Local filesystem storage (for development/small deployments)."""

    def __init__(self, base_path='/tmp/vtt-assets'):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def upload(self, file_key, file_content):
        """Upload file to local filesystem."""
        path = os.path.join(self.base_path, file_key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'wb') as f:
            f.write(file_content)
        return {'path': path, 'provider': 'local'}

    def download(self, file_key):
        """Download file from local filesystem."""
        path = os.path.join(self.base_path, file_key)
        if not os.path.exists(path):
            raise FileNotFoundError(f'File not found: {file_key}')
        with open(path, 'rb') as f:
            return f.read()

    def delete(self, file_key):
        """Delete file from local filesystem."""
        path = os.path.join(self.base_path, file_key)
        if os.path.exists(path):
            os.remove(path)

    def exists(self, file_key):
        """Check if file exists in local filesystem."""
        path = os.path.join(self.base_path, file_key)
        return os.path.exists(path)


class S3StorageAdapter(StorageAdapter):
    """S3-compatible object storage (production)."""

    def __init__(self, bucket_name, region='us-east-1', endpoint_url=None, aws_access_key=None, aws_secret_key=None):
        import boto3
        self.bucket_name = bucket_name

        self.s3_client = boto3.client(
            's3',
            region_name=region,
            endpoint_url=endpoint_url,  # For MinIO or DigitalOcean Spaces
            aws_access_key_id=aws_access_key,
            aws_secret_access_key=aws_secret_key,
        )

    def upload(self, file_key, file_content):
        """Upload file to S3."""
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=file_key,
            Body=file_content
        )
        return {
            's3_key': file_key,
            'bucket': self.bucket_name,
            'provider': 's3',
        }

    def download(self, file_key):
        """Download file from S3."""
        response = self.s3_client.get_object(
            Bucket=self.bucket_name,
            Key=file_key
        )
        return response['Body'].read()

    def delete(self, file_key):
        """Delete file from S3."""
        self.s3_client.delete_object(
            Bucket=self.bucket_name,
            Key=file_key
        )

    def exists(self, file_key):
        """Check if file exists in S3."""
        try:
            self.s3_client.head_object(
                Bucket=self.bucket_name,
                Key=file_key
            )
            return True
        except Exception:
            return False


def get_storage_adapter():
    """Get configured storage adapter based on config."""
    from flask import current_app

    provider = current_app.config.get('STORAGE_PROVIDER', 'local')

    if provider == 's3':
        return S3StorageAdapter(
            bucket_name=current_app.config.get('S3_BUCKET'),
            region=current_app.config.get('S3_REGION', 'us-east-1'),
            endpoint_url=current_app.config.get('S3_ENDPOINT_URL'),
            aws_access_key=current_app.config.get('AWS_ACCESS_KEY_ID'),
            aws_secret_key=current_app.config.get('AWS_SECRET_ACCESS_KEY'),
        )
    else:
        return LocalStorageAdapter(
            base_path=current_app.config.get('LOCAL_STORAGE_PATH', '/tmp/vtt-assets')
        )
