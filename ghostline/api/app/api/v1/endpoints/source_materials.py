import hashlib
from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    UploadFile,
    status,
    Response,
)
from sqlalchemy import and_
from sqlalchemy.orm import Session

from app.api import deps
from app.models.project import Project
from app.models.source_material import SourceMaterial, MaterialType, ProcessingStatus
from app.models.user import User
from app.services.storage import StorageService
from app.services.processing import get_processing_service

router = APIRouter()

ALLOWED_EXTENSIONS = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "txt": "text/plain",
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "m4a": "audio/mp4",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "png": "image/png",
    "gif": "image/gif",
}

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    project_id: str = Form(...),
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Upload a source material file."""
    # Validate project ownership
    project = (
        db.query(Project)
        .filter(and_(Project.id == project_id, Project.owner_id == current_user.id))
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    # Validate file extension
    file_extension = file.filename.split(".")[-1].lower()
    if file_extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"File type not allowed. Allowed types: "
                f"{', '.join(ALLOWED_EXTENSIONS.keys())}"
            ),
        )

    # Validate file size
    contents = await file.read()
    file_size = len(contents)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)}MB",
        )

    # Generate file hash
    file_hash = hashlib.sha256(contents).hexdigest()

    # Check for duplicate by filename and project
    if project_id:
        existing = (
            db.query(SourceMaterial)
            .filter(
                SourceMaterial.filename == file.filename,
                SourceMaterial.project_id == project_id,
            )
            .first()
        )

        if existing:
            return {"id": str(existing.id), "message": "File already exists", "duplicate": True}

    # Reset file position
    await file.seek(0)

    # Upload to S3
    storage_service = StorageService()
    file_key = (
        f"source-materials/{current_user.id}/{project_id}/{file_hash}/{file.filename}"
    )
    file_url = await storage_service.upload_file(file, file_key)

    # Check if file URL is valid (should be local URL or S3 URL)
    if not file_url or file_url.startswith("mock-"):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="File upload service is temporarily unavailable. The file could not be uploaded."
        )

    # Map file extension to MaterialType enum
    material_type_map = {
        'pdf': MaterialType.PDF,
        'docx': MaterialType.DOCX,
        'txt': MaterialType.TEXT,
        'mp3': MaterialType.AUDIO,
        'wav': MaterialType.AUDIO,
        'm4a': MaterialType.AUDIO,
        'jpg': MaterialType.IMAGE,
        'jpeg': MaterialType.IMAGE,
        'png': MaterialType.IMAGE,
        'gif': MaterialType.IMAGE,
    }
    material_type = material_type_map.get(file_extension, MaterialType.OTHER)

    # Create database record with error handling
    try:
        source_material = SourceMaterial(
            project_id=project_id,
            filename=file.filename,
            material_type=material_type,
            s3_bucket=storage_service.bucket_name,
            s3_key=file_key,
            s3_url=file_url,
            file_size=file_size,
            mime_type=ALLOWED_EXTENSIONS[file_extension],
            file_metadata={
                "original_filename": file.filename,
                "upload_timestamp": datetime.utcnow().isoformat(),
            },
            processing_status=ProcessingStatus.PENDING,  # Start as pending
        )
        
        # Store local path for local development
        if storage_service.use_local:
            source_material.local_path = str(storage_service.local_path / file_key)

        db.add(source_material)
        db.commit()
        db.refresh(source_material)
        
        # Process the source material (extract text, chunk, embed)
        processing_service = get_processing_service()
        cost_token = None
        try:
            # Ensure VLM + embedding calls during ingestion are cost-tracked in the DB.
            # (Uploads are synchronous and don't go through the Celery wrapper.)
            from agents.base.agent import set_cost_context, clear_cost_context

            cost_token = set_cost_context(
                project_id=project.id,
                task_id=None,
                workflow_run_id=f"ingest_{source_material.id}",
                db_session=db,
            )
        except Exception:
            clear_cost_context = None  # type: ignore
        try:
            result = processing_service.process_source_material(source_material, db)
            print(f"[UPLOAD] Processed {source_material.filename}: {result.chunks_created} chunks, {result.total_words} words")
        except Exception as e:
            print(f"[UPLOAD] Warning: Processing failed for {source_material.filename}: {e}")
            # Don't fail the upload, just mark as failed processing
            source_material.processing_status = ProcessingStatus.FAILED
            source_material.processing_error = str(e)
            db.commit()
        finally:
            if cost_token is not None and clear_cost_context is not None:
                try:
                    clear_cost_context(cost_token)
                except Exception:
                    pass

        return {
            "id": str(source_material.id),
            "name": source_material.filename,
            "type": file_extension,
            "size": source_material.file_size,
            "status": source_material.processing_status.value.lower() if hasattr(source_material.processing_status, 'value') else "completed",
        }
    except Exception as e:
        db.rollback()
        # Log the actual error for debugging
        print(f"Database error during upload: {type(e).__name__}: {str(e)}")
        
        # Check if it's an enum value error
        if "invalid input value for enum" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Database enum mismatch. The server needs to be updated to support this file type. Error: {str(e)}"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save file metadata: {str(e)}"
            )


@router.get("/{material_id}/content")
def get_material_content(
    material_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get the content of a source material file (proxy to avoid CORS issues)."""
    try:
        print(f"[CONTENT] Fetching content for material {material_id}, user {current_user.id}")
        
        material = (
            db.query(SourceMaterial)
            .join(Project)
            .filter(SourceMaterial.id == material_id, Project.owner_id == current_user.id)
            .first()
        )

        if not material:
            print(f"[CONTENT] Material {material_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Source material not found"
            )

        print(f"[CONTENT] Found material: {material.filename}, S3 key: {material.s3_key}")

        # Generate presigned URL and fetch content server-side
        storage_service = StorageService()
        try:
            presigned_url = storage_service.generate_presigned_url(
                material.s3_key, 
                expiration=3600
            )
            print(f"[CONTENT] Generated presigned URL for content fetch")
            
            # Fetch content server-side to avoid CORS issues
            import requests
            response = requests.get(presigned_url, timeout=30)
            response.raise_for_status()
            
            content = response.content
            print(f"[CONTENT] Successfully fetched {len(content)} bytes of content")
            
            # Return content with proper headers
            return Response(
                content=content,
                media_type=material.mime_type or "application/octet-stream",
                headers={
                    "Content-Disposition": f'inline; filename="{material.filename}"',
                    "Cache-Control": "private, max-age=3600",
                }
            )
            
        except Exception as e:
            print(f"[CONTENT] Failed to fetch content: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to fetch content: {str(e)}"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        print(f"[CONTENT] Unexpected error fetching content for {material_id}: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch content: {str(e)}"
        )


@router.get("/{material_id}/download")
def download_material(
    material_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Download a source material file directly (forces download)."""
    try:
        print(f"[DOWNLOAD] Starting direct download for material {material_id}, user {current_user.id}")
        
        material = (
            db.query(SourceMaterial)
            .join(Project)
            .filter(SourceMaterial.id == material_id, Project.owner_id == current_user.id)
            .first()
        )

        if not material:
            print(f"[DOWNLOAD] Material {material_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Source material not found"
            )

        print(f"[DOWNLOAD] Found material: {material.filename}, S3 key: {material.s3_key}")

        # Generate presigned URL and fetch content server-side
        storage_service = StorageService()
        try:
            presigned_url = storage_service.generate_presigned_url(
                material.s3_key, 
                expiration=3600
            )
            print(f"[DOWNLOAD] Generated presigned URL for download")
            
            # Fetch content server-side to avoid CORS issues
            import requests
            response = requests.get(presigned_url, timeout=60)  # Longer timeout for downloads
            response.raise_for_status()
            
            content = response.content
            print(f"[DOWNLOAD] Successfully fetched {len(content)} bytes for download")
            
            # Return content with download headers
            return Response(
                content=content,
                media_type="application/octet-stream",  # Force download
                headers={
                    "Content-Disposition": f'attachment; filename="{material.filename}"',
                    "Content-Length": str(len(content)),
                    "Cache-Control": "no-cache",
                }
            )
            
        except Exception as e:
            print(f"[DOWNLOAD] Failed to fetch file for download: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to download file: {str(e)}"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        print(f"[DOWNLOAD] Unexpected error downloading file {material_id}: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )


@router.get("/{material_id}")
def get_source_material(
    material_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get details of a specific source material."""
    material = (
        db.query(SourceMaterial)
        .join(Project)
        .filter(SourceMaterial.id == material_id, Project.owner_id == current_user.id)
        .first()
    )

    if not material:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Source material not found"
        )

    # Convert to dict for JSON serialization
    return {
        "id": str(material.id),
        "filename": material.filename,
        "material_type": material.material_type.value if hasattr(material.material_type, 'value') else material.material_type,
        "file_size": material.file_size,
        "mime_type": material.mime_type,
        "processing_status": material.processing_status.value if hasattr(material.processing_status, 'value') else material.processing_status,
        "created_at": material.created_at.isoformat() if material.created_at else None,
        "s3_url": material.s3_url,
    }


@router.delete("/{material_id}")
def delete_source_material(
    material_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Delete a source material."""
    try:
        print(f"[DELETE] Attempting to delete material {material_id} for user {current_user.id}")
        
        material = (
            db.query(SourceMaterial)
            .join(Project)
            .filter(SourceMaterial.id == material_id, Project.owner_id == current_user.id)
            .first()
        )

        if not material:
            print(f"[DELETE] Material {material_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Source material not found"
            )

        print(f"[DELETE] Found material: {material.filename}, S3 key: {material.s3_key}")

        # Delete from S3
        storage_service = StorageService()
        try:
            storage_service.delete_file_by_key(material.s3_key)
            print(f"[DELETE] Successfully deleted from S3: {material.s3_key}")
        except Exception as e:
            print(f"[DELETE] Failed to delete from S3: {e}")
            # Continue with database deletion even if S3 fails

        # Delete from database
        try:
            db.delete(material)
            db.commit()
            print(f"[DELETE] Successfully deleted from database: {material_id}")
        except Exception as e:
            print(f"[DELETE] Database deletion failed: {type(e).__name__}: {str(e)}")
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete material from database: {str(e)}"
            )

        return {"detail": "Source material deleted successfully"}
    
    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        print(f"[DELETE] Unexpected error deleting material {material_id}: {type(e).__name__}: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete source material: {str(e)}"
        )


@router.get("/{material_id}/download-url")
def get_download_url(
    material_id: str,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user),
):
    """Get a presigned URL for downloading a source material."""
    try:
        print(f"[DOWNLOAD] Generating download URL for material {material_id}, user {current_user.id}")
        
        material = (
            db.query(SourceMaterial)
            .join(Project)
            .filter(SourceMaterial.id == material_id, Project.owner_id == current_user.id)
            .first()
        )

        if not material:
            print(f"[DOWNLOAD] Material {material_id} not found for user {current_user.id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Source material not found"
            )

        print(f"[DOWNLOAD] Found material: {material.filename}, S3 key: {material.s3_key}")

        # Generate presigned URL for download
        storage_service = StorageService()
        try:
            download_url = storage_service.generate_presigned_url(
                material.s3_key, 
                expiration=3600  # 1 hour expiration
            )
            print(f"[DOWNLOAD] Successfully generated presigned URL for: {material.filename}")
            
            return {
                "download_url": download_url,
                "filename": material.filename,
                "expires_in": 3600
            }
        except Exception as e:
            print(f"[DOWNLOAD] Failed to generate presigned URL: {type(e).__name__}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate download URL: {str(e)}"
            )
    
    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        print(f"[DOWNLOAD] Unexpected error generating download URL for {material_id}: {type(e).__name__}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate download URL: {str(e)}"
        )
