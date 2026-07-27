from pydantic import BaseModel, ConfigDict
from datetime import datetime
from uuid import UUID


class DatasetClassSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    class_name: str
    image_count: int


class DatasetSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: str
    class_count: int | None
    total_images: int | None
    file_size_mb: float | None
    minio_path: str | None
    created_at: datetime


class DatasetDetailSchema(DatasetSchema):
    classes: list[DatasetClassSchema] = []


class UploadResponseSchema(BaseModel):
    dataset_id: str
    name: str
    class_count: int
    total_images: int
    file_size_mb: float
    cached: bool = False
    # `invalid_files` (corrupted images at upload time) removed in Fase 5 —
    # that check now lives solely in modelgate-core's MGS-0002 checker
    # (G4/D2.1, BACKLOG.md), run when an audit is requested. Upload no
    # longer duplicates it. See dataset_service/routers/upload.py.
