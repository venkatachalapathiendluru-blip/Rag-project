"""Token-aware chunking that returns the original text.

It measures with the tokenizer but never rebuilds text from tokens, because the
embedding tokenizer is uncased and would lowercase names in the evidence.
"""

import re


def chunk_text(text, tokenizer, chunk_size=180, overlap=35):
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and overlap smaller than chunk_size.")

    if not text or not text.strip():
        return []

    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    chunks = []
    current_sentences = []
    current_tokens = 0

    def save_chunk():
        if current_sentences:
            chunks.append(" ".join(current_sentences))

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        token_count = len(
            tokenizer.encode(sentence, add_special_tokens=False)
        )

        if not token_count:
            continue

        if token_count > chunk_size:
            if current_sentences:
                save_chunk()
                current_sentences = []
                current_tokens = 0

            encoded = tokenizer(
                sentence,
                add_special_tokens=False,
                return_offsets_mapping=True
            )
            offsets = encoded["offset_mapping"]
            start = 0
            step = chunk_size - overlap
            while start < len(offsets):
                end = min(start + chunk_size, len(offsets))
                char_start = offsets[start][0]
                char_end = offsets[end - 1][1]
                # Preserve complete words at the beginning.
                while (
                    char_start > 0
                    and not sentence[char_start - 1].isspace()
                ):
                    char_start -= 1
                # Preserve complete words at the end.
                while (
                    char_end < len(sentence)
                    and not sentence[char_end].isspace()
                ):
                    char_end += 1
                chunk = sentence[char_start:char_end].strip()
                if chunk:
                    chunks.append(chunk)
                if end == len(offsets):
                    break
                start += step
            continue

        # Normal sentence packing.
        if current_tokens + token_count > chunk_size:
            save_chunk()
            previous_sentences = []
            previous_tokens = 0
            # Preserve complete sentences as overlap.
            for previous in reversed(current_sentences):
                previous_count = len(
                    tokenizer.encode(
                        previous,
                        add_special_tokens=False
                    )
                )
                if previous_tokens + previous_count > overlap:
                    break
                previous_sentences.insert(0, previous)
                previous_tokens += previous_count

            while previous_sentences and previous_tokens + token_count > chunk_size:
                removed = previous_sentences.pop(0)
                previous_tokens -= len(
                    tokenizer.encode(removed, add_special_tokens=False)
                )

            current_sentences = previous_sentences
            current_tokens = previous_tokens

        current_sentences.append(sentence)
        current_tokens += token_count

    save_chunk()
    return [chunk for chunk in chunks if chunk]
