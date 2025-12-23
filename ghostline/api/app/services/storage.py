"""
Storage service supporting both local file storage and S3.
For local development, files are stored on disk.
For production, files are stored in S3.
"""

import os
import shutil
import uuid
from pathlib import Path

from fastapi import UploadFile

from app.core.config import settings


class StorageService:
    """Storage service that supports local files or S3."""

    def __init__(self):
        self.use_local = settings.USE_LOCAL_STORAGE
        self.local_path = Path(settings.LOCAL_STORAGE_PATH)
        self.bucket_name = settings.S3_SOURCE_MATERIALS_BUCKET

        if self.use_local:
            # Create local storage directory
            self.local_path.mkdir(parents=True, exist_ok=True)
            print(f"[StorageService] Using LOCAL storage at: {self.local_path.absolute()}")
        else:
            # Try to initialize S3
            self._init_s3()

    def _init_s3(self):
        """Initialize S3 client (only when not using local storage)."""
        try:
            import boto3
            from botocore.config import Config as BotoConfig

            s3_config = BotoConfig(
                signature_version='s3v4',
                region_name=settings.AWS_REGION,
            )

            if settings.AWS_ACCESS_KEY_ID and settings.AWS_SECRET_ACCESS_KEY:
                self.s3_client = boto3.client(
                    "s3",
                    aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                    aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                    config=s3_config,
                )
            else:
                self.s3_client = boto3.client("s3", config=s3_config)

            # Test connection
            self.s3_client.head_bucket(Bucket=self.bucket_name)
            print(f"[StorageService] Connected to S3 bucket: {self.bucket_name}")

        except Exception as e:
            print(f"[StorageService] S3 init failed: {e}, falling back to local storage")
            self.use_local = True
            self.local_path.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file: UploadFile, key: str) -> str:
        """Upload a file and return the URL/path."""
        content = await file.read()

        if self.use_local:
            return self._upload_local(content, key, file.content_type)
        else:
            return self._upload_s3(content, key, file.content_type)

    def _upload_local(self, content: bytes, key: str, content_type: str | None) -> str:
        """Upload file to local storage."""
        # Create directory structure
        file_path = self.local_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(file_path, 'wb') as f:
            f.write(content)

        # Return a URL that can be served by the API
        url = f"http://localhost:8000/api/v1/files/{key}"
        print(f"[LOCAL] Saved {len(content)} bytes to: {file_path}")
        return url

    def _upload_s3(self, content: bytes, key: str, content_type: str | None) -> str:
        """Upload file to S3."""
        from botocore.exceptions import ClientError

        try:
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=content,
                ContentType=content_type or "application/octet-stream",
            )
            url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{key}"
            print(f"[S3] Uploaded {len(content)} bytes to: {url}")
            return url
        except ClientError as e:
            print(f"[S3] Upload failed: {e}")
            raise

    def get_file_content(self, key: str) -> bytes:
        """Get file content by key."""
        if self.use_local:
            file_path = self.local_path / key
            if file_path.exists():
                with open(file_path, 'rb') as f:
                    return f.read()
            raise FileNotFoundError(f"File not found: {key}")
        else:
            from botocore.exceptions import ClientError
            try:
                response = self.s3_client.get_object(Bucket=self.bucket_name, Key=key)
                return response['Body'].read()
            except ClientError as e:
                raise FileNotFoundError(f"S3 file not found: {key}") from e

    def delete_file(self, file_url: str) -> bool:
        """Delete a file by URL."""
        if self.use_local:
            # Extract key from local URL
            if "/api/v1/files/" in file_url:
                key = file_url.split("/api/v1/files/")[-1]
            else:
                key = file_url
            return self.delete_file_by_key(key)
        else:
            # Extract key from S3 URL
            key = file_url.split(f"{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/")[-1]
            return self.delete_file_by_key(key)

    def delete_file_by_key(self, key: str) -> bool:
        """Delete a file by key."""
        if self.use_local:
            file_path = self.local_path / key
            if file_path.exists():
                file_path.unlink()
                print(f"[LOCAL] Deleted: {file_path}")
                return True
            return False
        else:
            from botocore.exceptions import ClientError
            try:
                self.s3_client.delete_object(Bucket=self.bucket_name, Key=key)
                print(f"[S3] Deleted: {key}")
                return True
            except ClientError as e:
                print(f"[S3] Delete failed: {e}")
                return False

    def generate_presigned_url(self, key: str, expiration: int = 3600) -> str:
        """Generate a URL to access the file."""
        if self.use_local:
            # For local, return the API endpoint URL
            return f"http://localhost:8000/api/v1/files/{key}"
        else:
            url = self.s3_client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration,
                HttpMethod='GET'
            )
            return url

    def file_exists(self, key: str) -> bool:
        """Check if a file exists."""
        if self.use_local:
            return (self.local_path / key).exists()
        else:
            from botocore.exceptions import ClientError
            try:
                self.s3_client.head_object(Bucket=self.bucket_name, Key=key)
                return True
            except ClientError:
                return False
