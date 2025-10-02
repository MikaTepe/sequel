import logging
import re
from typing import List, Tuple

logger = logging.getLogger("keyword-extraction.chunker")


class TextChunker:
    """
    Utility to split long text into overlapping chunks while trying to keep
    boundaries at whitespace or sentence ends.
    """

    @staticmethod
    def estimate_pages(char_count: int, approx_chars_per_page: int) -> float:
        """Return approximate page count for logging/limit decisions."""
        return char_count / max(approx_chars_per_page, 1)

    @staticmethod
    def normalize_whitespace(text: str) -> str:
        """Collapse excessive whitespace to keep chunk sizes meaningful."""
        return re.sub(r"[ \t\f\v]+", " ", text).replace("\r\n", "\n").strip()

    @staticmethod
    def smart_split(
        text: str,
        chunk_size: int,
        overlap: int,
    ) -> List[str]:
        """
        Split text into overlapping chunks of ~chunk_size chars with `overlap`.
        Prefer splitting on whitespace close to boundaries to avoid word cuts.
        """
        if chunk_size <= 0:
            raise ValueError("chunk_size must be > 0")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        text = TextChunker.normalize_whitespace(text)
        n = len(text)
        if n == 0:
            return []

        chunks: List[str] = []
        start = 0

        while start < n:
            end = min(start + chunk_size, n)

            # try to end on whitespace/punctuation within a small window forward
            window_end = min(end + 200, n)
            best_end = end

            # look forward for a nicer boundary
            forward = re.search(r"[ \n\.\!\?\:\;\,]", text[end:window_end])
            if forward:
                cand = end + forward.start()
                if cand - start >= chunk_size * 0.6:  # don't shrink too much
                    best_end = cand

            # if no forward boundary, try looking backward a little
            if best_end == end:
                window_start = max(start + int(chunk_size * 0.6), start)
                backward = re.search(
                    r"[ \n\.\!\?\:\;\,](?!.*[ \n\.\!\?\:\;\,])", text[window_start:end]
                )
                if backward:
                    best_end = window_start + backward.start()

            chunk = text[start:best_end].strip()
            if chunk:
                chunks.append(chunk)

            if best_end >= n:
                break

            # next start with overlap
            start = max(0, best_end - overlap)

        logger.info(
            "Chunked text into %d chunks (size≈%d, overlap=%d)",
            len(chunks), chunk_size, overlap
        )
        return chunks