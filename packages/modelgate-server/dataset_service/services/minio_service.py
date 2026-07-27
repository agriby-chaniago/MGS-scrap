import os
from minio import Minio


class MinIOService:
    def __init__(self):
        self.endpoint = os.getenv("MINIO_ENDPOINT", "minio:9000")
        self.access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
        self.secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin123")
        self.bucket = os.getenv("MINIO_BUCKET", "modelgate-datasets")
        self.secure = os.getenv("MINIO_SECURE", "false").lower() == "true"

        self.client = Minio(
            self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure,
        )

    def ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, object_name: str, file_path: str) -> str:
        self.client.fput_object(self.bucket, object_name, file_path)
        return f"{self.bucket}/{object_name}"

    def upload_manifest(self, dataset_id: str, manifest) -> str:
        """Upload every Sample in a modelgate Manifest to MinIO, keyed by
        its canonical `uri`. Replaces the old `upload_directory`, which
        guessed the dataset's root-folder structure itself (assumed a
        single wrapper folder always existed — silently uploaded zero
        objects for a flat-class ZIP) and dropped split information
        entirely (BACKLOG.md A1, G7). `Sample.uri` is already normalized
        by modelgate-core's Reader (`split/label/filename` or
        `label/filename`), so storing at that path is correct by
        construction — no structure-guessing here at all."""
        for sample in manifest.samples:
            object_name = f"{dataset_id}/{sample.uri}"
            self.client.fput_object(self.bucket, object_name, sample.source_path)

        return f"{self.bucket}/{dataset_id}/"

    def delete_prefix(self, prefix: str):
        """Hapus semua object dengan prefix tertentu (rollback)."""
        objects = self.client.list_objects(self.bucket, prefix=prefix, recursive=True)
        for obj in objects:
            self.client.remove_object(self.bucket, obj.object_name)


minio_service = MinIOService()
