import os
from typing import List, Dict, Any

from dotenv import load_dotenv
from google import genai
from pinecone import Pinecone

load_dotenv()


class GeminiPineconeVectorStore:
    def __init__(
        self,
        index_name: str = "gemini-demo",
        dimension: int = 768,
        metric: str = "cosine",
        cloud: str = "aws",
        region: str = "us-east-1",
    ):
        self.index_name = index_name
        self.dimension = dimension

        # 🔐 keys
        self._pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
        self._genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

        # 🧠 ensure index exists
        self._ensure_index(metric, cloud, region)

        # 📦 index handle
        self._index = self._pc.Index(self.index_name)

    # -----------------------------
    # Internal helpers
    # -----------------------------

    def _ensure_index(self, metric: str, cloud: str, region: str):
        if self.index_name not in self._pc.list_indexes().names():
            self._pc.create_index(
                name=self.index_name,
                dimension=self.dimension,
                metric=metric,
                spec={"serverless": {"cloud": cloud, "region": region}},
            )

    def _get_embedding(self, text: str) -> List[float]:
        response = self._genai_client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=text,
            config={"output_dimensionality": self.dimension},
        )
        return response.embeddings[0].values

    # -----------------------------
    # Public methods
    # -----------------------------

    def upsert_texts(self, texts: List[str]):
        vectors = []

        for i, text in enumerate(texts):
            emb = self._get_embedding(text)

            vectors.append(
                {
                    "id": str(i),
                    "values": emb,
                    "metadata": {"text": text},
                }
            )

        self._index.upsert(vectors)

    def upsert_documents(self, docs: List[Dict[str, Any]]):
        """
        docs = [
            {"id": "chunk1", "text": "...", "meta": {...}}
        ]
        """
        vectors = []

        for doc in docs:
            emb = self._get_embedding(doc["text"])

            vectors.append(
                {
                    "id": doc["id"],
                    "values": emb,
                    "metadata": doc.get("meta", {}),
                }
            )

        self._index.upsert(vectors)

    def query(self, text: str, top_k: int = 5):
        query_embedding = self._get_embedding(text)

        return self._index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
        )