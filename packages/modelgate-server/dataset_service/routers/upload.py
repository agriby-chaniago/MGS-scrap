import hashlib
import os
import shutil
from uuid import uuid4

from fastapi import APIRouter, UploadFile, File, Form, Header, BackgroundTasks, HTTPException, Depends
from sqlalchemy.orm import Session

from modelgate import read_dataset

from models.database import get_db
from models.orm import Dataset, DatasetClass
from models.schemas import UploadResponseSchema
from services.minio_service import minio_service
from shared.response import success_response, error_response

router = APIRouter()

SERVICE_NAME = "dataset_service"
UPLOAD_TMP_DIR = "/tmp/modelgate_uploads"

# Single ceiling for everyone — no longer a per-tier cap (G8, BACKLOG.md).
# The old TIER_UPLOAD_LIMITS_MB (free=150/pro=1024/max=2048) is gone along
# with the rest of the tier system; this is the same value the "max" tier
# used to get.
MAX_ZIP_SIZE_MB = 2048


def _cleanup_tmp(path: str):
    if os.path.exists(path):
        shutil.rmtree(path, ignore_errors=True)


@router.post("/api/v1/datasets/upload", status_code=201)
async def upload_dataset(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    name: str = Form(...),
    db: Session = Depends(get_db),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
):
    # 1. Size limit — one ceiling for all, not per-plan (G8).
    file_bytes = await file.read()
    size_mb = len(file_bytes) / (1024 * 1024)
    if size_mb > MAX_ZIP_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum {MAX_ZIP_SIZE_MB}MB, got {size_mb:.1f}MB",
        )

    # 1b. Dedup by hash — return the existing dataset if identical (scoped
    # to this user's own datasets, or unowned legacy ones — never another
    # user's data).
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing = db.query(Dataset).filter(
        Dataset.file_hash == file_hash,
        Dataset.status == "active",
    ).filter(
        (Dataset.user_id == x_user_id) | (Dataset.user_id.is_(None))
    ).first()
    if existing:
        return success_response(
            data=UploadResponseSchema(
                dataset_id=str(existing.id),
                name=existing.name,
                class_count=existing.class_count,
                total_images=existing.total_images,
                file_size_mb=existing.file_size_mb,
                cached=True,
            ).model_dump(),
            service=SERVICE_NAME,
        )

    upload_id = str(uuid4())
    tmp_dir = os.path.join(UPLOAD_TMP_DIR, upload_id)
    os.makedirs(tmp_dir, exist_ok=True)
    zip_path = os.path.join(tmp_dir, "upload.zip")

    with open(zip_path, "wb") as f:
        f.write(file_bytes)

    # 2. Parse structure via modelgate-core — the ONE structure-detection
    # implementation (G4/D2.1, BACKLOG.md A1). This used to be a separate
    # validator.py here, out of sync with the storage layer's own (buggy,
    # single-root-only) assumptions — that bug is what silently uploaded
    # zero objects for a flat-class ZIP. There's also no more "must have
    # >=2 classes" rejection here: under MGS-0000 (fail closed), that
    # determination is a real verdict (MGS-0001) produced when an audit is
    # requested, not a pre-audit HTTP 400 that hides the actual result.
    try:
        manifest = read_dataset(zip_path)
    except ValueError:
        background_tasks.add_task(_cleanup_tmp, tmp_dir)
        raise HTTPException(status_code=400, detail="File is not a valid ZIP archive")

    dataset_id = str(uuid4())
    minio_path = None
    total_size_bytes = sum(s.bytes for s in manifest.samples)
    images_per_class: dict[str, int] = {}
    for s in manifest.samples:
        images_per_class[s.label] = images_per_class.get(s.label, 0) + 1

    try:
        # 3. Upload to MinIO, keyed by each Sample's canonical uri (G7) —
        # split (if any) and label are already embedded in the path by
        # modelgate-core's Reader, so storage can't drop them the way the
        # old naive `{dataset_id}/{class_name}/{filename}` scheme did.
        minio_path = minio_service.upload_manifest(dataset_id, manifest)

        # 4. Save to DB
        dataset = Dataset(
            id=dataset_id,
            name=name,
            status="active",
            class_count=len(manifest.labels),
            total_images=len(manifest.samples),
            file_size_mb=round(total_size_bytes / (1024 * 1024), 2),
            minio_path=minio_path,
            file_hash=file_hash,
            user_id=x_user_id,
        )
        db.add(dataset)
        db.flush()

        for class_name, count in images_per_class.items():
            db.add(DatasetClass(
                dataset_id=dataset_id,
                class_name=class_name,
                image_count=count,
            ))

        db.commit()

    except Exception as e:
        db.rollback()
        if minio_path:
            try:
                minio_service.delete_prefix(dataset_id + "/")
            except Exception:
                pass
        background_tasks.add_task(_cleanup_tmp, tmp_dir)

        if "minio" in str(type(e).__module__).lower() or "s3" in str(e).lower():
            raise HTTPException(status_code=500, detail="Storage upload failed")
        raise HTTPException(status_code=500, detail="Database save failed")

    background_tasks.add_task(_cleanup_tmp, tmp_dir)

    return success_response(
        data=UploadResponseSchema(
            dataset_id=dataset_id,
            name=name,
            class_count=len(manifest.labels),
            total_images=len(manifest.samples),
            file_size_mb=round(total_size_bytes / (1024 * 1024), 2),
        ).model_dump(),
        service=SERVICE_NAME,
    )
