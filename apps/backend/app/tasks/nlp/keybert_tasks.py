import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from celery import current_task
from celery.exceptions import Retry

from ..celery_app import celery_app
from ...services.nlp.keybert_service import keybert_service
from ...schemas.nlp.keybert import KeywordExtractionRequest, SupportedLanguage
from ...core.exceptions import (
    KeywordExtractionException,
    ModelNotLoadedException,
    UnsupportedLanguageException,
    BatchSizeExceededException
)

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def extract_keywords_async(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asynchronous keyword extraction task

    Args:
        task_data: Dictionary containing extraction parameters

    Returns:
        Task result with keywords or error information
    """

    task_id = self.request.id
    logger.info(f"Starting async keyword extraction task {task_id}")

    try:
        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Initializing keyword extraction...',
                'progress': 10,
                'task_id': task_id
            }
        )

        # Ensure service is initialized
        if not keybert_service.is_initialized():
            logger.info("Initializing KeyBERT service for async task...")
            # Run async initialization in sync context
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(keybert_service.initialize())
            finally:
                loop.close()

        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Extracting keywords...',
                'progress': 50,
                'task_id': task_id
            }
        )

        # Extract parameters
        text = task_data.get('text', '')
        language = task_data.get('language', 'de')
        max_keywords = task_data.get('max_keywords', 10)
        min_ngram = task_data.get('min_ngram', 1)
        max_ngram = task_data.get('max_ngram', 2)
        diversity = task_data.get('diversity', 0.5)
        use_mmr = task_data.get('use_mmr', True)
        include_metadata = task_data.get('include_metadata', True)

        # Run keyword extraction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            keywords, metadata = loop.run_until_complete(
                keybert_service.extract_keywords(
                    text=text,
                    language=language,
                    max_keywords=max_keywords,
                    min_ngram=min_ngram,
                    max_ngram=max_ngram,
                    diversity=diversity,
                    use_mmr=use_mmr,
                    include_metadata=include_metadata
                )
            )
        finally:
            loop.close()

        # Convert KeywordResult objects to dictionaries
        keywords_data = [
            {
                "keyword": kw.keyword,
                "score": kw.score,
                "ngram_size": kw.ngram_size
            }
            for kw in keywords
        ]

        # Convert metadata to dictionary
        metadata_data = None
        if metadata:
            metadata_data = {
                "processing_time_ms": metadata.processing_time_ms,
                "model_used": metadata.model_used,
                "total_tokens": metadata.total_tokens,
                "extraction_parameters": metadata.extraction_parameters
            }

        # Final result
        result = {
            "status": "SUCCESS",
            "keywords": keywords_data,
            "language": language,
            "text_length": len(text),
            "total_keywords_found": len(keywords),
            "processing_metadata": metadata_data,
            "task_id": task_id,
            "completed_at": datetime.utcnow().isoformat()
        }

        logger.info(f"Async keyword extraction task {task_id} completed successfully")
        return result

    except (ModelNotLoadedException, UnsupportedLanguageException) as e:
        logger.error(f"Task {task_id} failed with validation error: {e}")
        return {
            "status": "FAILURE",
            "error": str(e),
            "error_code": getattr(e, 'error_code', 'VALIDATION_ERROR'),
            "task_id": task_id,
            "failed_at": datetime.utcnow().isoformat()
        }

    except KeywordExtractionException as e:
        logger.error(f"Task {task_id} failed with extraction error: {e}")

        # Retry for certain errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {
            "status": "FAILURE",
            "error": str(e),
            "error_code": getattr(e, 'error_code', 'EXTRACTION_ERROR'),
            "task_id": task_id,
            "retries": self.request.retries,
            "failed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Task {task_id} failed with unexpected error: {e}", exc_info=True)

        # Retry for unexpected errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {task_id} due to unexpected error")
            raise self.retry(countdown=60 * (self.request.retries + 1))

        return {
            "status": "FAILURE",
            "error": f"Unexpected error: {str(e)}",
            "error_code": "INTERNAL_ERROR",
            "task_id": task_id,
            "retries": self.request.retries,
            "failed_at": datetime.utcnow().isoformat()
        }


@celery_app.task(bind=True, max_retries=2, default_retry_delay=120)
def extract_keywords_batch_async(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Asynchronous batch keyword extraction task

    Args:
        batch_data: Dictionary containing batch extraction parameters

    Returns:
        Batch processing results
    """

    task_id = self.request.id
    texts = batch_data.get('texts', [])
    parallel_processing = batch_data.get('parallel_processing', True)
    fail_fast = batch_data.get('fail_fast', False)

    logger.info(f"Starting async batch extraction task {task_id} with {len(texts)} texts")

    try:
        # Validate batch size
        if len(texts) > 100:
            raise BatchSizeExceededException(current_size=len(texts), max_size=100)

        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Processing batch extraction...',
                'progress': 10,
                'total_texts': len(texts),
                'processed': 0,
                'task_id': task_id
            }
        )

        # Ensure service is initialized
        if not keybert_service.is_initialized():
            logger.info("Initializing KeyBERT service for batch task...")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(keybert_service.initialize())
            finally:
                loop.close()

        # Convert to KeywordExtractionRequest objects
        requests = []
        for text_data in texts:
            request = KeywordExtractionRequest(
                text=text_data.get('text', ''),
                language=SupportedLanguage(text_data.get('language', 'de')),
                max_keywords=text_data.get('max_keywords', 10),
                min_ngram=text_data.get('min_ngram', 1),
                max_ngram=text_data.get('max_ngram', 2),
                diversity=text_data.get('diversity', 0.5),
                use_mmr=text_data.get('use_mmr', True),
                include_metadata=text_data.get('include_metadata', False)
            )
            requests.append(request)

        # Update progress
        self.update_state(
            state='PROCESSING',
            meta={
                'status': 'Extracting keywords from batch...',
                'progress': 30,
                'total_texts': len(texts),
                'processed': 0,
                'task_id': task_id
            }
        )

        # Process batch
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            raw_results = loop.run_until_complete(
                keybert_service.extract_keywords_batch(
                    requests=requests,
                    parallel_processing=parallel_processing,
                    fail_fast=fail_fast
                )
            )
        finally:
            loop.close()

        # Process results
        results = []
        successful_count = 0
        failed_count = 0

        for raw_result in raw_results:
            if raw_result["success"]:
                # Convert KeywordResult objects to dictionaries
                keywords_data = [
                    {
                        "keyword": kw.keyword,
                        "score": kw.score,
                        "ngram_size": kw.ngram_size
                    }
                    for kw in raw_result["keywords"]
                ]

                result_item = {
                    "index": raw_result["index"],
                    "success": True,
                    "keywords": keywords_data,
                    "language": raw_result["language"],
                    "text_length": raw_result["text_length"],
                    "processing_time_ms": raw_result.get("processing_time_ms")
                }

                # Add metadata if present
                if raw_result.get("metadata"):
                    metadata = raw_result["metadata"]
                    result_item["metadata"] = {
                        "processing_time_ms": metadata.processing_time_ms,
                        "model_used": metadata.model_used,
                        "total_tokens": metadata.total_tokens
                    }

                results.append(result_item)
                successful_count += 1
            else:
                results.append({
                    "index": raw_result["index"],
                    "success": False,
                    "error": raw_result["error"],
                    "error_code": raw_result.get("error_code"),
                    "processing_time_ms": raw_result.get("processing_time_ms")
                })
                failed_count += 1

        # Final result
        final_result = {
            "status": "SUCCESS",
            "results": results,
            "summary": {
                "total_texts": len(texts),
                "successful": successful_count,
                "failed": failed_count,
                "success_rate": successful_count / len(texts) if len(texts) > 0 else 0.0,
                "parallel_processing": parallel_processing,
                "fail_fast": fail_fast
            },
            "task_id": task_id,
            "completed_at": datetime.utcnow().isoformat()
        }

        logger.info(
            f"Batch extraction task {task_id} completed: "
            f"{successful_count}/{len(texts)} successful"
        )

        return final_result

    except BatchSizeExceededException as e:
        logger.error(f"Batch task {task_id} failed: batch size exceeded")
        return {
            "status": "FAILURE",
            "error": str(e),
            "error_code": "BATCH_SIZE_EXCEEDED",
            "task_id": task_id,
            "failed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"Batch task {task_id} failed: {e}", exc_info=True)

        # Retry for unexpected errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying batch task {task_id}")
            raise self.retry(countdown=120 * (self.request.retries + 1))

        return {
            "status": "FAILURE",
            "error": f"Batch processing failed: {str(e)}",
            "error_code": "BATCH_PROCESSING_ERROR",
            "task_id": task_id,
            "retries": self.request.retries,
            "failed_at": datetime.utcnow().isoformat()
        }


@celery_app.task
def cleanup_keybert_service() -> Dict[str, Any]:
    """
    Task to cleanup KeyBERT service resources

    Returns:
        Cleanup status
    """

    logger.info("Starting KeyBERT service cleanup task")

    try:
        if keybert_service.is_initialized():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(keybert_service.cleanup())
            finally:
                loop.close()

            logger.info("KeyBERT service cleanup completed")
            return {
                "status": "SUCCESS",
                "message": "KeyBERT service cleaned up successfully",
                "completed_at": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "SKIPPED",
                "message": "KeyBERT service was not initialized",
                "completed_at": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"KeyBERT cleanup failed: {e}", exc_info=True)
        return {
            "status": "FAILURE",
            "error": str(e),
            "failed_at": datetime.utcnow().isoformat()
        }


@celery_app.task
def get_keybert_service_status() -> Dict[str, Any]:
    """
    Task to get KeyBERT service status and statistics

    Returns:
        Service status information
    """

    try:
        if keybert_service.is_initialized():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                service_info = loop.run_until_complete(keybert_service.get_service_info())
            finally:
                loop.close()

            return {
                "status": "SUCCESS",
                "service_info": service_info,
                "checked_at": datetime.utcnow().isoformat()
            }
        else:
            return {
                "status": "NOT_INITIALIZED",
                "message": "KeyBERT service is not initialized",
                "checked_at": datetime.utcnow().isoformat()
            }

    except Exception as e:
        logger.error(f"Failed to get KeyBERT service status: {e}")
        return {
            "status": "ERROR",
            "error": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }


# === PERIODIC TASKS ===

@celery_app.task
def keybert_health_check():
    """
    Periodic health check for KeyBERT service

    This task can be scheduled to run periodically to monitor service health
    """

    logger.info("Running periodic KeyBERT health check")

    try:
        if not keybert_service.is_initialized():
            logger.warning("KeyBERT service is not initialized")
            return {
                "status": "UNHEALTHY",
                "reason": "Service not initialized",
                "checked_at": datetime.utcnow().isoformat()
            }

        # Test with simple extraction
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            test_text = "This is a simple test for health check purposes."
            keywords, _ = loop.run_until_complete(
                keybert_service.extract_keywords(
                    text=test_text,
                    language="en",
                    max_keywords=3
                )
            )

            if len(keywords) > 0:
                logger.info("KeyBERT health check passed")
                return {
                    "status": "HEALTHY",
                    "test_keywords_count": len(keywords),
                    "checked_at": datetime.utcnow().isoformat()
                }
            else:
                logger.warning("KeyBERT health check: no keywords extracted")
                return {
                    "status": "DEGRADED",
                    "reason": "No keywords extracted from test text",
                    "checked_at": datetime.utcnow().isoformat()
                }

        finally:
            loop.close()

    except Exception as e:
        logger.error(f"KeyBERT health check failed: {e}")
        return {
            "status": "UNHEALTHY",
            "reason": str(e),
            "checked_at": datetime.utcnow().isoformat()
        }


# === TASK UTILITIES ===

def submit_keyword_extraction_task(
        text: str,
        language: str = "de",
        max_keywords: int = 10,
        **kwargs
) -> str:
    """
    Submit a keyword extraction task

    Args:
        text: Text to analyze
        language: Language code
        max_keywords: Maximum keywords to extract
        **kwargs: Additional extraction parameters

    Returns:
        Task ID
    """

    task_data = {
        "text": text,
        "language": language,
        "max_keywords": max_keywords,
        **kwargs
    }

    task = extract_keywords_async.delay(task_data)
    return task.id


def submit_batch_extraction_task(
        texts: List[Dict[str, Any]],
        parallel_processing: bool = True,
        fail_fast: bool = False
) -> str:
    """
    Submit a batch extraction task

    Args:
        texts: List of text data dictionaries
        parallel_processing: Process in parallel
        fail_fast: Stop on first error

    Returns:
        Task ID
    """

    batch_data = {
        "texts": texts,
        "parallel_processing": parallel_processing,
        "fail_fast": fail_fast
    }

    task = extract_keywords_batch_async.delay(batch_data)
    return task.id


def get_task_result(task_id: str) -> Dict[str, Any]:
    """
    Get result of a task

    Args:
        task_id: Task ID

    Returns:
        Task result or status
    """

    result = celery_app.AsyncResult(task_id)

    if result.ready():
        if result.successful():
            return {
                "task_id": task_id,
                "status": "COMPLETED",
                "result": result.result
            }
        else:
            return {
                "task_id": task_id,
                "status": "FAILED",
                "error": str(result.result)
            }
    else:
        # Get current state info
        state_info = result.info if result.info else {}

        return {
            "task_id": task_id,
            "status": result.state,
            "progress": state_info.get("progress", 0),
            "current_status": state_info.get("status", "Processing...")
        }