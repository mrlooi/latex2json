import json

import psycopg2
from pgvector.psycopg2 import register_vector
import numpy as np

from pgvector_test import PGVectorClient

from openai import OpenAI


if __name__ == '__main__':
    with open('data/res.json', 'r') as f:
        paper_data = json.load(f)

        # Connection parameters
    db_params = {
        'host': 'localhost',
        'port': 5432,
        'database': 'postgres',
        'user': 'postgres',
        'password': 'pixcap123'
    }
    OPENAI_API_KEY = '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'

    # Initialize client
    client = PGVectorClient(db_params)
    
    openai_client = OpenAI(api_key=OPENAI_API_KEY)  # Replace with your actual API key

    # abstract = paper_data['abstract']
    
    # response = openai_client.embeddings.create(input=abstract, model="text-embedding-3-small", encoding_format="float")
    # embedding = response.data[0].embedding

    # client.insert_embedding(abstract, embedding)

    # # Create a list to store all chunks
    # all_chunks = []
    
    # # Add abstract as first chunk
    # all_chunks.append(abstract)
    
    # # Process sections and collect all chunks
    # for section in paper_data['sections']:
    #     content = section['content']
    #     words = content.split()
    #     chunks = [' '.join(words[i:i+400]) for i in range(0, len(words), 400)]
    #     all_chunks.extend(chunks)
    
    # # Process chunks in batches of 100 (you can adjust this number)
    # BATCH_SIZE = 100
    # for i in range(0, len(all_chunks), BATCH_SIZE):
    #     batch = all_chunks[i:i+BATCH_SIZE]
        
    #     # Get embeddings for the entire batch
    #     response = openai_client.embeddings.create(
    #         input=batch,
    #         model="text-embedding-3-small",
    #         encoding_format="float"
    #     )
        
    #     # Insert embeddings in bulk
    #     for j, embedding_data in enumerate(response.data):
    #         client.insert_embedding(batch[j], embedding_data.embedding)
        
    #     print(f"Processed batch {i//BATCH_SIZE + 1} of {(len(all_chunks) + BATCH_SIZE - 1)//BATCH_SIZE}")

    # print("Done inserting embeddings")

    def search_query(query: str, limit: int = 3):
        query_response = openai_client.embeddings.create(input=query, model="text-embedding-3-small", encoding_format="float")
        query_embedding = query_response.data[0].embedding

        results = client.search_similar(query_embedding, limit=limit)  # Assuming your client has a search method
        return results

    query = "what is attention equation?"
    results = search_query(query)
    print("Results Similarity:", [f[2] for f in results])

    # convert to json and dump results to file
    with open('results.json', 'w') as f:
        json.dump(results, f)
