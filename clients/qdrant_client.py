import logging
from typing import Any, Optional
from qdrant_client import QdrantClient as QdrantSDK
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PointIdsList,
)


class QdrantClient:
    """Universal Qdrant vector database client for managing collections and vectors."""

    def __init__(self, host: str = "localhost", port: int = 6333):
        """
        Initialize Qdrant client.

        Args:
            host: Qdrant server host
            port: Qdrant server port
        """
        self.client = QdrantSDK(host=host, port=port)
        logging.info(f"Initialized Qdrant client connecting to {host}:{port}")

    def create_collection(
        self, collection_name: str, vector_size: int, distance: Distance = Distance.COSINE
    ) -> bool:
        """
        Create a new collection in Qdrant.

        Args:
            collection_name: Name of the collection to create
            vector_size: Dimension of vectors to store
            distance: Distance metric to use (COSINE, DOT, EUCLID)

        Returns:
            True if collection was created successfully
        """
        try:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=distance),
            )
            logging.info(f"Created collection '{collection_name}' with vector size {vector_size}")
            return True
        except Exception as e:
            logging.error(f"Failed to create collection '{collection_name}': {e}")
            return False

    def collection_exists(self, collection_name: str) -> bool:
        """
        Check if a collection exists.

        Args:
            collection_name: Name of the collection to check

        Returns:
            True if collection exists
        """
        try:
            exists = self.client.collection_exists(collection_name)
            logging.info(f"Collection '{collection_name}' exists: {exists}")
            return exists
        except Exception as e:
            logging.error(f"Failed to check if collection '{collection_name}' exists: {e}")
            return False

    def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            True if collection was deleted successfully
        """
        try:
            self.client.delete_collection(collection_name=collection_name)
            logging.info(f"Deleted collection '{collection_name}'")
            return True
        except Exception as e:
            logging.error(f"Failed to delete collection '{collection_name}': {e}")
            return False

    def add_points(self, collection_name: str, points: list[PointStruct]) -> bool:
        """
        Add multiple points to a collection.

        Args:
            collection_name: Name of the collection
            points: List of PointStruct objects to add

        Returns:
            True if points were added successfully
        """
        try:
            self.client.upsert(collection_name=collection_name, points=points)
            logging.info(f"Added {len(points)} points to collection '{collection_name}'")
            return True
        except Exception as e:
            logging.error(f"Failed to add points to collection '{collection_name}': {e}")
            return False

    def add_point(
        self,
        collection_name: str,
        point_id: str | int,
        vector: list[float],
        payload: Optional[dict[str, Any]] = None,
    ) -> bool:
        """
        Add a single point to a collection.

        Args:
            collection_name: Name of the collection
            point_id: Unique identifier for the point
            vector: Vector embedding as list of floats
            payload: Optional metadata dictionary

        Returns:
            True if point was added successfully
        """
        try:
            point = PointStruct(id=point_id, vector=vector, payload=payload or {})
            return self.add_points(collection_name, [point])
        except Exception as e:
            logging.error(f"Failed to add point {point_id} to collection '{collection_name}': {e}")
            return False

    def search(
        self,
        collection_name: str,
        query_vector: list[float],
        limit: int = 10,
        filter_conditions: Optional[Filter] = None,
        score_threshold: Optional[float] = None,
    ) -> list[dict]:
        """
        Search for similar vectors in a collection.

        Args:
            collection_name: Name of the collection to search
            query_vector: Query vector as list of floats
            limit: Maximum number of results to return
            filter_conditions: Optional filter conditions
            score_threshold: Optional minimum score threshold

        Returns:
            List of search results with id, score, and payload
        """
        try:
            results = self.client.search(
                collection_name=collection_name,
                query_vector=query_vector,
                query_filter=filter_conditions,
                limit=limit,
                score_threshold=score_threshold,
            )

            search_results = []
            for result in results:
                search_results.append(
                    {"id": result.id, "score": result.score, "payload": result.payload}
                )

            logging.info(f"Found {len(search_results)} results in collection '{collection_name}'")
            return search_results

        except Exception as e:
            logging.error(f"Failed to search collection '{collection_name}': {e}")
            return []

    def get_point(self, collection_name: str, point_id: str | int) -> Optional[dict]:
        """
        Retrieve a specific point by ID.

        Args:
            collection_name: Name of the collection
            point_id: ID of the point to retrieve

        Returns:
            Dictionary with point data or None if not found
        """
        try:
            result = self.client.retrieve(
                collection_name=collection_name,
                ids=[point_id],
                with_vectors=True,
                with_payload=True,
            )

            if result:
                point = result[0]
                return {"id": point.id, "vector": point.vector, "payload": point.payload}
            else:
                logging.info(f"Point {point_id} not found in collection '{collection_name}'")
                return None

        except Exception as e:
            logging.error(
                f"Failed to get point {point_id} from collection '{collection_name}': {e}"
            )
            return None

    def delete_points(self, collection_name: str, point_ids: list[str | int]) -> bool:
        """
        Delete multiple points from a collection.

        Args:
            collection_name: Name of the collection
            point_ids: List of point IDs to delete

        Returns:
            True if points were deleted successfully
        """
        try:
            self.client.delete(
                collection_name=collection_name, points_selector=PointIdsList(points=point_ids)
            )
            logging.info(f"Deleted {len(point_ids)} points from collection '{collection_name}'")
            return True
        except Exception as e:
            logging.error(f"Failed to delete points from collection '{collection_name}': {e}")
            return False

    def get_collection_info(self, collection_name: str) -> Optional[dict]:
        """
        Get information about a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Dictionary with collection information or None if error
        """
        try:
            info = self.client.get_collection(collection_name=collection_name)

            # Handle both single vector and named vector configurations
            vector_config = info.config.params.vectors
            if hasattr(vector_config, "size"):
                # Single vector configuration
                vector_size = vector_config.size
                distance = vector_config.distance
            else:
                # Named vectors configuration - get the default or first vector
                vector_name = list(vector_config.keys())[0] if vector_config else "default"
                vector_size = vector_config[vector_name].size
                distance = vector_config[vector_name].distance

            return {
                "name": collection_name,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "points_count": info.points_count,
                "segments_count": info.segments_count,
                "config": {
                    "vector_size": vector_size,
                    "distance": distance.value if hasattr(distance, "value") else str(distance),
                },
            }
        except Exception as e:
            logging.error(f"Failed to get info for collection '{collection_name}': {e}")
            return None

    def count_points(self, collection_name: str, filter_conditions: Optional[Filter] = None) -> int:
        """
        Count points in a collection with optional filtering.

        Args:
            collection_name: Name of the collection
            filter_conditions: Optional filter conditions

        Returns:
            Number of points matching the criteria
        """
        try:
            result = self.client.count(
                collection_name=collection_name,
                count_filter=filter_conditions,
                exact=True,  # Use exact counting for accuracy
            )
            count = result.count
            logging.info(f"Collection '{collection_name}' contains {count} points")
            return count
        except Exception as e:
            logging.error(f"Failed to count points in collection '{collection_name}': {e}")
            return 0

    def create_field_filter(self, field_name: str, match_value: Any) -> Filter:
        """
        Create a simple field filter for search queries.

        Args:
            field_name: Name of the field to filter by
            match_value: Value to match

        Returns:
            Filter object for use in search queries
        """
        return Filter(must=[FieldCondition(key=field_name, match=MatchValue(value=match_value))])
