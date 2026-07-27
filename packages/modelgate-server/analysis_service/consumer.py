"""RabbitMQ consumer — runs an audit by calling modelgate-core.

Fase 5 (G4/D2.1, BACKLOG.md): this used to own a local `analyzers/`
directory with 5 separate analyzer implementations, each run and stored
independently, filtered by a tier-derived `requested_analyzers` list.
That was a second, server-side copy of logic that now lives once in
modelgate-core. This module now does exactly one thing: download the
dataset (already in modelgate-core's canonical uri layout — see
dataset_service's minio_service.py, which is what makes this work
without any structure-guessing here), call `modelgate.audit()` once, and
store the Report's per-Requirement results.

`AnalysisResult.status` here means "did this row's data get produced
successfully" (execution status) — it is NOT the MGS verdict. A dataset
that legitimately FAILs MGS-0003 (too many duplicates) still has
status="completed": the check ran and produced a real answer. The
verdict itself (PASS/FAIL/NOT_EVALUATED) lives inside `result_payload`.
Conflating the two would make a correctly-detected FAIL look like a
crashed analyzer to audit_service's results_consumer.py.
"""

import json
import logging
import os
import time
from datetime import datetime, timezone

import pika
from modelgate import audit as modelgate_audit

from models.database import SessionLocal
from models.orm import AnalysisResult, AuditStatus
from services.minio_downloader import cleanup_tmp, download_dataset
from services.publisher import publish_analysis_result

logger = logging.getLogger(__name__)

# Row used to carry Report.informative (currently just resolution stats)
# — not an MGS requirement, so it doesn't get an "MGS-000X" analyzer_type,
# but report_service reads it back the same way as the normative ones.
INFORMATIVE_ANALYZER_TYPE = "informative"


def process_message(ch, method, properties, body):
    db = SessionLocal()
    audit_id = None
    try:
        payload = json.loads(body)
        audit_id = payload["audit_id"]

        # Force retry: clear old results so this can be redone from scratch.
        if payload.get("force"):
            db.query(AnalysisResult).filter(AnalysisResult.audit_id == audit_id).delete()
            db.commit()
            logger.info(f"[{audit_id}] Force retry: cleared existing results")

        # Idempotency: already fully processed? (4 requirements + 1 informative row)
        expected_rows = len(payload["requested_analyzers"]) + 1
        existing = db.query(AnalysisResult).filter(
            AnalysisResult.audit_id == audit_id,
            AnalysisResult.status == "completed",
        ).count()
        if existing == expected_rows:
            logger.info(f"[{audit_id}] Already processed, ack and skip")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        audit = db.query(AuditStatus).filter(AuditStatus.id == audit_id).first()
        if not audit or audit.status != "queued":
            status_val = audit.status if audit else "not found"
            logger.warning(f"[{audit_id}] Unexpected status={status_val}, skip")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        audit.status = "processing"
        db.commit()

        started = datetime.now(timezone.utc)
        try:
            local_path = download_dataset(payload["dataset_minio_path"], audit_id)
            logger.info(f"[{audit_id}] Running modelgate.audit()")
            report = modelgate_audit(local_path)
        except Exception as e:
            # The whole audit blew up (dataset unreadable from storage, or
            # an unexpected bug) — this is NOT a per-Requirement FAIL
            # verdict; those are handled gracefully inside modelgate-core
            # itself (see checkers/*.py) and never raise. Without this
            # branch, zero result rows would ever get published, and
            # audit_service's results_consumer.py — which waits for
            # exactly len(requested_analyzers) done rows before deciding
            # completed vs. failed — would never see enough rows to
            # decide anything. The Audit would hang in "processing"
            # forever: not "failed", so not retryable either. Publishing
            # one "failed" row per expected requirement, all carrying the
            # same error, closes that gate the same way a real per-
            # requirement failure would have in the pre-Fase-5 design.
            logger.error(f"[{audit_id}] modelgate.audit() failed: {e}", exc_info=True)
            completed = datetime.now(timezone.utc)
            for req_id in payload["requested_analyzers"]:
                db.add(AnalysisResult(
                    audit_id=audit_id,
                    analyzer_type=req_id,
                    status="failed",
                    result_payload=None,
                    error_message=str(e),
                    started_at=started,
                    completed_at=completed,
                ))
                db.commit()
                publish_analysis_result({
                    "audit_id": audit_id,
                    "analyzer_type": req_id,
                    "status": "failed",
                    "result_payload": None,
                    "error_message": str(e),
                    "completed_at": completed.isoformat(),
                })
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        completed = datetime.now(timezone.utc)

        for r in report.requirements:
            row_payload = {
                "verdict": r.verdict,
                "config": r.config,
                "metrics": r.metrics,
                "findings": r.findings,
            }
            db.add(AnalysisResult(
                audit_id=audit_id,
                analyzer_type=r.id,
                status="completed",
                result_payload=row_payload,
                error_message=None,
                started_at=started,
                completed_at=completed,
            ))
            db.commit()

            publish_analysis_result({
                "audit_id": audit_id,
                "analyzer_type": r.id,
                "status": "completed",
                "result_payload": row_payload,
                "error_message": None,
                "completed_at": completed.isoformat(),
            })

        # dataset_hash and spec_version ride along on the informative row
        # rather than needing a new column — this is what lets
        # report_service reconstruct a Report shape comparable to
        # modelgate-core's own (spec §4 requires both on every Report;
        # they were previously computed by modelgate.audit() and then
        # silently discarded once only report.informative was kept).
        informative_payload = {
            "dataset_hash": report.dataset_hash,
            "spec_version": report.spec_version,
            **report.informative,
        }

        db.add(AnalysisResult(
            audit_id=audit_id,
            analyzer_type=INFORMATIVE_ANALYZER_TYPE,
            status="completed",
            result_payload=informative_payload,
            error_message=None,
            started_at=started,
            completed_at=completed,
        ))
        db.commit()

        publish_analysis_result({
            "audit_id": audit_id,
            "analyzer_type": INFORMATIVE_ANALYZER_TYPE,
            "status": "completed",
            "result_payload": informative_payload,
            "error_message": None,
            "completed_at": completed.isoformat(),
        })

        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        db.rollback()
        logger.error(f"[{audit_id}] Consumer error: {e}", exc_info=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

    finally:
        db.close()
        if audit_id:
            cleanup_tmp(f"/tmp/analysis_{audit_id}")


def start_consuming():
    while True:
        try:
            conn = pika.BlockingConnection(pika.ConnectionParameters(
                host=os.getenv("RABBITMQ_HOST", "rabbitmq"),
                port=int(os.getenv("RABBITMQ_PORT", "5672")),
                virtual_host=os.getenv("RABBITMQ_VHOST", "/"),
                credentials=pika.PlainCredentials(
                    os.getenv("RABBITMQ_USER", "guest"),
                    os.getenv("RABBITMQ_PASS", "guest"),
                ),
            ))
            ch = conn.channel()
            ch.queue_declare(queue="audit.jobs", durable=True)
            ch.basic_qos(prefetch_count=1)
            ch.basic_consume(queue="audit.jobs", on_message_callback=process_message)
            logger.info("Analysis consumer started, waiting for messages...")
            ch.start_consuming()
        except Exception as e:
            logger.error(f"Consumer connection lost: {e}. Reconnecting in 5s...")
            time.sleep(5)
