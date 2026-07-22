import faiss
import numpy as np
from fastembed import TextEmbedding
import json


class SemanticSearchService:

    def __init__(self, knowledge_repository):

        self.repository = knowledge_repository

        self.model = TextEmbedding(
            model_name="BAAI/bge-small-en-v1.5"
        )

        self.index = None
        self.documents = []

        self.build_index()

    # ----------------------------------------------------
    # Build searchable document
    # ----------------------------------------------------

    def build_document(self, row):

        return f"""

Host:
{row.get("host","")}

Trigger ID:
{row.get("trigger_id", "")}

Severity:
{row.get("severity", "")}

Technology:
{row.get("technology", "")}

Problem:
{row.get("problem", "")}

Metrics:
{json.dumps(row.get("metrics", {}), indent=2)}

Root Cause:
{row.get("root_cause", "")}

Remediation:
{" ".join(row.get("recommended_resolution", []))}

Next Diagnostics:
{row.get("next_diagnostics", [])}

Logs:
{row.get("log_summary", "")}
"""

    # ----------------------------------------------------

    def embed(self, text):

        embedding = next(
            self.model.embed([text])
        )

        return np.array(
            embedding,
            dtype=np.float32
        )

    # ----------------------------------------------------

    def build_index(self):

        incidents = self.repository.get_all()

        if len(incidents) == 0:

            print("Knowledge Base is empty.")
            return

        self.documents = incidents

        vectors = []

        for incident in incidents:

            vector = self.embed(
                self.build_document(incident)
            )

            faiss.normalize_L2(
                vector.reshape(1, -1)
            )

            vectors.append(vector)

        vectors = np.vstack(vectors)

        self.index = faiss.IndexFlatIP(
            vectors.shape[1]
        )

        self.index.add(vectors)

        print(f"Semantic Index Built : {len(vectors)} documents")

    # ----------------------------------------------------

    def search(self, parsed, trigger_id=None, technology="", top_k=5):

        if self.index is None:
            return []

        query = f"""
Host:
{parsed.host}

Problem:
{parsed.problem}

Severity:
{parsed.severity}

Trigger ID:
{trigger_id}

Technology:
{technology}
"""

        query_vector = self.embed(query)

        faiss.normalize_L2(
            query_vector.reshape(1, -1)
        )

        scores, indices = self.index.search(
            query_vector.reshape(1, -1),
            top_k
        )

        results = []

        for score, idx in zip(scores[0], indices[0]):

            if idx == -1:
                continue

            incident = dict(self.documents[idx])

            embedding_score = float(score)

            final_score = embedding_score

            # Technology match
            if technology:
                if incident.get("technology") == technology:
                    final_score += 0.15

            # Trigger match
            if trigger_id:
                if str(incident.get("trigger_id")) == str(trigger_id):
                    final_score += 0.25

            # Same severity
            if incident.get("severity") == parsed.severity:
                final_score += 0.05

            incident["similarity"] = round(final_score, 3)
            if technology:

                if incident.get("technology") != technology:
                    continue

            results.append(incident)
        results.sort(
            key=lambda x: x["similarity"],
            reverse=True
        )

        return results
                    # return results

    # ----------------------------------------------------

    def rebuild(self):

        self.index = None
        self.documents = []

        self.build_index()

    # ----------------------------------------------------

    def get_embedding(self, text):

        vector = list(
            self.model.embed([text])
        )[0]

        vector = np.array(
            vector,
            dtype=np.float32
        )

        faiss.normalize_L2(
            vector.reshape(1, -1)
        )

        return vector

    # ----------------------------------------------------

    def add_document(self, incident):

        text = self.build_document(incident)

        vector = self.get_embedding(text)

        if self.index is None:

            self.index = faiss.IndexFlatIP(
                len(vector)
            )

        self.index.add(
            np.array([vector], dtype=np.float32)
        )

        self.documents.append(dict(incident))

        print(
            f"Added '{incident.get('problem')}' to Semantic Index."
        )