import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np
from typing import List, Tuple, Optional

class PGVectorClient:
    def __init__(self, db_params: dict, init_table: bool = False):
        self.db_params = db_params
        if init_table:
            self.initialize_table()
        
    def _get_connection(self):
        conn = psycopg2.connect(**self.db_params)
        register_vector(conn)
        return conn

    def initialize_table(self):
        """Create the embeddings table if it doesn't exist"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    conn.commit()
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS embeddings_test (
                            id SERIAL PRIMARY KEY,
                            content TEXT,
                            embedding vector(1536)
                        )
                    """)
                conn.commit()
            print("Table initialized successfully!")
        except Exception as e:
            print(f"Error initializing table: {e}")

    def insert_embedding(self, content: str, embedding: np.ndarray) -> bool:
        """Insert a single embedding with its content"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO embeddings_test (content, embedding) VALUES (%s, %s)",
                        (content, embedding)
                    )
                conn.commit()
            return True
        except Exception as e:
            print(f"Error inserting embedding: {e}")
            return False

    def read_all_embeddings(self) -> List[Tuple[int, str, np.ndarray]]:
        """Read all embeddings from the database"""
        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id, content, embedding FROM embeddings_test")
                    return cur.fetchall()
        except Exception as e:
            print(f"Error reading embeddings: {e}")
            return []
        
    def search_similar(self, query_embedding: list, limit: int = 3) -> List[Tuple[int, str, float, np.ndarray]]:
        """Search for similar embeddings based on a query embedding
        
        Returns:
            List of tuples containing (id, content, similarity_score, embedding)
            Similarity score is cosine similarity, higher means more similar
        """

        try:
            with self._get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT id, content, 1 - (embedding <=> %s::vector) as similarity
                        FROM embeddings_test
                        ORDER BY embedding <=> %s::vector
                        LIMIT %s
                    """, (query_embedding, query_embedding, limit))
                    return cur.fetchall()   
        except Exception as e:
            print(f"Error searching for similar embeddings: {e}")
            return []
        
    def search_similar_query(self, query: str, limit: int = 3) -> List[Tuple[int, str, float, np.ndarray]]:
        """Search for similar embeddings based on a query string"""
        query_embedding = self.embed_query(query)
        return self.search_similar(query_embedding, limit)
        
# Example usage
if __name__ == "__main__":
    # Connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres',
        'password': 'pixcap123'
    }

    # Initialize client
    client = PGVectorClient(db_params)
    
    # Insert test data
    test_embedding = np.random.rand(1536).astype(np.float32)
    if client.insert_embedding("test content", test_embedding):
        print("Test embedding inserted successfully!")
    
    # Read and display data
    print("\nReading inserted data:")
    for id, content, embedding in client.read_all_embeddings():
        print(f"\nID: {id}")
        print(f"Content: {content}")
        print(f"Embedding shape: {len(embedding)}")
        print(f"First 5 values of embedding: {embedding[:5]}")
