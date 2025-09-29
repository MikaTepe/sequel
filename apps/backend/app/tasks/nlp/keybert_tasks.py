"""KeyBERT Celery Tasks"""

import asyncio
import logging
from typing import Dict, List, Any
from datetime import datetime

from ..celery_app import celery_app
from ...services.nlp.keybert_service import keybert_service
from ...schemas.nlp.keybert import KeywordExtractionRequest, SupportedLanguage
from ...core.exceptions import BatchSizeExceededException

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def extract_keywords_async(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """Async keyword extraction task"""

    task_id = self.request.id
    logger.info(f"Starting task {task_id}")

    try:
        # Update state
        self.update_state(state='PROCESSING', meta={'progress': 50})

        # Ensure service is initialized
        if not keybert_service.is_initialized():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(keybert_service.initialize())
            finally:
                loop.close()

        # Extract keywords
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            keywords, metadata = loop.run_until_complete(
                keybert_service.extract_keywords(
                    text=task_data.get('text', ''),
                    language=task_data.get('language', 'de'),
                    max_keywords=task_data.get('max_keywords', 10),
                    min_ngram=task_data.get('min_ngram', 1),
                    max_ngram=task_data.get('max_ngram', 2),
                    diversity=task_data.get('diversity', 0.5),
                    use_mmr=task_data.get('use_mmr', True),
                    include_metadata=True
                )
            )
        finally:
            loop.close()

        # Format result
        return {
            "status": "SUCCESS",
            "keywords": [
                {"keyword": kw.keyword, "score": kw.score, "ngram_size": kw.ngram_size}
                for kw in keywords
            ],
            "task_id": task_id,
            "completed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Task {task_id} failed: {e}")

        if self.request.retries < self.max_retries:
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {
            "status": "FAILURE",
            "error": str(e),
            "task_id": task_id,
            "failed_at": datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, max_retries=2)
def extract_keywords_batch_async(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """Batch keyword extraction task"""

    task_id = self.request.id
    texts = batch_data.get('texts', [])

    logger.info(f"Starting batch task {task_id} with {len(texts)} texts")

    try:
        if len(texts) > 100:
            raise BatchSizeExceededException(len(texts), 100)

        # Initialize service if needed
        if not keybert_service.is_initialized():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(keybert_service.initialize())
            finally:
                loop.close()

        # Convert to request objects
        requests = [
            KeywordExtractionRequest(
                text=t.get('text', ''),
                language=SupportedLanguage(t.get('language', 'de')),
                max_keywords=t.get('max_keywords', 10),
                min_ngram=t.get('min_ngram', 1),
                max_ngram=t.get('max_ngram', 2),
                diversity=t.get('diversity', 0.5),
                use_mmr=t.get('use_mmr', True)
            )
            for t in texts
        ]

        # Process batch
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            raw_results = loop.run_until_complete(
                keybert_service.extract_keywords_batch(
                    requests=requests,
                    parallel_processing=batch_data.get('parallel_processing', True),
                    fail_fast=batch_data.get('fail_fast', False)
                )
            )
        finally:
            loop.close()

        # Format results
        results = []
        successful = 0
        for r in raw_results:
            if r["success"]:
                results.append({
                    "index": r["index"],
                    "success": True,
                    "keywords": [
                        {"keyword": kw.keyword, "score": kw.score}
                        for kw in r["keywords"]
                    ]
                })
                successful += 1
            else:
                results.append({
                    "index": r["index"],
                    "success": False,
                    "error": r["error"]
                })

        return {
            "status": "SUCCESS",
            "results": results,
            "summary": {
                "total": len(texts),
                "successful": successful,
                "failed": len(texts) - successful
            },
            "task_id": task_id,
            "completed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Batch task {task_id} failed: {e}")

        if self.request.retries < self.max_retries:
            raise self.retry(countdown=120 * (self.request.retries + 1))

        return {
            "status": "FAILURE",
            "error": str(e),
            "task_id": task_id,
            "failed_at": datetime.utcnow().isoformat()
        }


@celery_app.task
def keybert_health_check() -> Dict[str, Any]:
    """Periodic health check"""

    logger.info("Running KeyBERT health check")

    try:
        if not keybert_service.is_initialized():
            return {"status": "UNHEALTHY", "reason": "Not initialized"}

        # Test extraction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            keywords, _ = loop.run_until_complete(
                keybert_service.extract_keywords(
                    text="This is a health check test.",
                    language="en",
                    max_keywords=3
                )
            )
        finally:
            loop.close()

        return {
            "status": "HEALTHY" if len(keywords) > 0 else "DEGRADED",
            "checked_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "UNHEALTHY",
            "reason": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }