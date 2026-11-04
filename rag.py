
import argparse
import os
import re
from pathlib import Path
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
import psycopg
from dotenv import load_dotenv

from chunking import chunk_text

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")
DB_PASSWORD = os.getenv("DB_PASSWORD")
if not DB_PASSWORD:
    raise ValueError("DB_PASSWORD missing from .env")

PDF_PATH = Path(os.getenv("RAG_PDF_PATH", "resume.pdf"))
def get_db_connection():
    return psycopg.connect(
        dbname=os.getenv("DB_NAME", "rag_db"),
        user=os.getenv("DB_USER", "rag_user"),
        password=DB_PASSWORD,
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "5433"))
    )

# Load free embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")


def load_pdf(file_path):
    if not file_path.exists():
        raise FileNotFoundError(f"PDF not found: {file_path}")

    reader = PdfReader(str(file_path))
    extracted_text = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            extracted_text.append(text)

    return "\n".join(extracted_text)


def generate_embeddings(chunks):
    embeddings = embedding_model.encode(
        chunks,
        convert_to_numpy=True,
        normalize_embeddings=True
    )

    return embeddings
def store_embeddings(chunks, embeddings):

    conn = get_db_connection()

    try:
        with conn.cursor() as cur:

            for chunk, embedding in zip(chunks, embeddings):

                cur.execute(
                    """
                    INSERT INTO documents (content, embedding)
                    VALUES (%s, %s)
                    """,
                    (chunk, embedding.tolist())
                )

        conn.commit()
        print("Embeddings stored successfully!")

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def main(ingest=False):
    print("Loading Resume PDF...")

    text = load_pdf(PDF_PATH)

    print("PDF successfully loaded!")
    print("Total Characters:", len(text))

    # Step 1: Chunking
    chunks = chunk_text(
        text,
        embedding_model.tokenizer,
        chunk_size=180,
        overlap=35
    )

    print("\n--- CHUNKING REPORT ---")
    print("Total chunks:", len(chunks))
    print("Unique chunks:", len(set(chunks)))
    token_counts = [
        len(embedding_model.tokenizer.encode(
            chunk,
            add_special_tokens=True
        ))
        for chunk in chunks
    ]
    average_tokens = round(sum(token_counts) / len(token_counts), 2) if token_counts else 0
    print("Average tokens:", average_tokens)
    print("Maximum tokens:", max(token_counts, default=0))
    for index, chunk in enumerate(chunks, start=1):
        print(f"\nChunk {index} ({token_counts[index - 1]} tokens)")
        print(chunk[:150])
    if any(count > embedding_model.max_seq_length for count in token_counts):
        raise ValueError("A chunk exceeds the model's maximum sequence length!")

    if not chunks:
        raise ValueError("No text chunks were created from the PDF.")

    print("\nTotal Chunks Created:", len(chunks))

    # Step 2: Generate embeddings
    print("\nGenerating Embeddings...")

    embeddings = generate_embeddings(chunks)

    print("\nEmbeddings Generated Successfully!")
    print("Total Embeddings:", len(embeddings))
    print("Embedding Dimension:", embeddings.shape[1])

    if not ingest:
        print("\nDRY RUN: No database records will be inserted.")
        return

    store_embeddings(chunks, embeddings)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Create resume embeddings.")
    parser.add_argument(
        "--ingest",
        action="store_true",
        help="Insert generated embeddings into PostgreSQL.",
    )
    main(ingest=parser.parse_args().ingest)
