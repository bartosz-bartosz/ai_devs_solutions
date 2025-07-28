import logging
import os

from typing import Any, Optional
from neo4j import GraphDatabase, Driver, Session


class Neo4jClient:
    """
    A client for interacting with Neo4j graph database.
    Provides methods for managing nodes, relationships, and running queries.
    """

    def __init__(self):
        """
        Initialize Neo4j client.

        Args:
            uri: Neo4j server URI (e.g., "bolt://localhost:7687")
            user: Neo4j username
            password: Neo4j password
        """
        self.logger = logging.getLogger("Neo4jClient")
        self.uri, self.username, self.password = self.read_environment_variables()
        self.driver: Driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))

        # Test connection
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            self.logger.info(f"Successfully connected to Neo4j at {self.uri}")
        except Exception as e:
            self.logger.error(f"Failed to connect to Neo4j: {e}")
            raise

    def read_environment_variables(self):
        # Read username and password from environment variables
        uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = os.getenv("NEO4J_USERNAME", "neo4j")
        password = os.getenv("NEO4J_PASSWORD", "neo4j")

        if not username or not password or not uri:
            raise ValueError("NEO4J_USERNAME and NEO4J_PASSWORD environment variables must be set")

        return uri, username, password

    def close(self):
        """Close Neo4j driver connection."""
        if self.driver:
            self.driver.close()
            self.logger.info("Neo4j driver connection closed")

    def run_query(self, query: str, parameters: Optional[dict[str, Any]] = None) -> list[dict]:
        """
        Execute a Cypher query and return results.

        Args:
            query: Cypher query string
            parameters: Optional parameters for the query

        Returns:
            List of dictionaries containing query results
        """
        try:
            with self.driver.session() as session:
                result = session.run(query, parameters or {})
                records = [dict(record) for record in result]
                self.logger.info(f"Query executed successfully, returned {len(records)} records")
                return records
        except Exception as e:
            self.logger.error(f"Failed to execute query: {e}")
            raise

    def run_single_query(
        self, query: str, parameters: Optional[dict[str, Any]] = None
    ) -> Optional[dict]:
        """
        Execute a Cypher query and return single result.

        Args:
            query: Cypher query string
            parameters: Optional parameters for the query

        Returns:
            Dictionary containing single query result or None
        """
        results = self.run_query(query, parameters)
        return results[0] if results else None

    def clear_database(self):
        """Remove all nodes and relationships from the database."""
        self.logger.info("Clearing entire Neo4j database")
        self.run_query("MATCH (n) DETACH DELETE n")
        self.logger.info("Database cleared successfully")

    def create_node(self, label: str, properties: dict[str, Any]) -> dict:
        """
        Create a single node with given label and properties.

        Args:
            label: Node label (e.g., "User", "Person")
            properties: Dictionary of node properties

        Returns:
            Dictionary containing created node information
        """
        # Build property string for Cypher query
        prop_strings = [f"{key}: ${key}" for key in properties.keys()]
        prop_clause = "{" + ", ".join(prop_strings) + "}"

        query = f"CREATE (n:{label} {prop_clause}) RETURN n"
        result = self.run_single_query(query, properties)

        self.logger.info(f"Created node with label '{label}' and properties: {properties}")
        return result

    def create_nodes_batch(self, label: str, nodes_data: list[dict[str, Any]]):
        """
        Create multiple nodes in a single transaction for better performance.

        Args:
            label: Node label for all nodes
            nodes_data: List of dictionaries containing node properties
        """
        if not nodes_data:
            return

        query = f"""
        UNWIND $nodes_data AS nodeData
        CREATE (n:{label})
        SET n = nodeData
        """

        self.run_query(query, {"nodes_data": nodes_data})
        self.logger.info(f"Created {len(nodes_data)} nodes with label '{label}'")

    def create_relationship(
        self,
        start_node_filter: dict,
        end_node_filter: dict,
        relationship_type: str,
        properties: Optional[dict[str, Any]] = None,
    ):
        """
        Create a relationship between two nodes.

        Args:
            start_node_filter: Properties to identify start node
            end_node_filter: Properties to identify end node
            relationship_type: Type of relationship (e.g., "KNOWS", "FOLLOWS")
            properties: Optional properties for the relationship
        """
        # Build WHERE clauses for node matching
        start_conditions = " AND ".join(
            [f"start.{key} = $start_{key}" for key in start_node_filter.keys()]
        )
        end_conditions = " AND ".join([f"end.{key} = $end_{key}" for key in end_node_filter.keys()])

        # Prepare parameters
        params = {}
        for key, value in start_node_filter.items():
            params[f"start_{key}"] = value
        for key, value in end_node_filter.items():
            params[f"end_{key}"] = value

        # Build relationship properties clause
        rel_props = ""
        if properties:
            prop_strings = [f"{key}: $rel_{key}" for key in properties.keys()]
            rel_props = "{" + ", ".join(prop_strings) + "}"
            for key, value in properties.items():
                params[f"rel_{key}"] = value

        query = f"""
        MATCH (start) WHERE {start_conditions}
        MATCH (end) WHERE {end_conditions}
        CREATE (start)-[r:{relationship_type} {rel_props}]->(end)
        RETURN r
        """

        self.run_query(query, params)
        self.logger.info(f"Created {relationship_type} relationship")

    def create_relationships_batch(self, relationships_data: list[dict]):
        """
        Create multiple relationships in a single transaction.

        Args:
            relationships_data: List of dictionaries containing:
                - start_filter: dict to identify start node
                - end_filter: dict to identify end node
                - rel_type: relationship type
                - rel_props: optional relationship properties
        """
        if not relationships_data:
            return

        # Process each relationship type separately for efficiency
        rel_types = set(rel["rel_type"] for rel in relationships_data)

        for rel_type in rel_types:
            typed_rels = [rel for rel in relationships_data if rel["rel_type"] == rel_type]

            query = f"""
            UNWIND $relationships AS rel
            MATCH (start) WHERE start.userId = rel.start_id
            MATCH (end) WHERE end.userId = rel.end_id
            CREATE (start)-[:{rel_type}]->(end)
            """

            # Transform data for query
            query_data = []
            for rel in typed_rels:
                query_data.append(
                    {
                        "start_id": rel["start_filter"]["userId"],
                        "end_id": rel["end_filter"]["userId"],
                    }
                )

            self.run_query(query, {"relationships": query_data})

        self.logger.info(f"Created {len(relationships_data)} relationships")

    def find_node(self, label: str, properties: dict[str, Any]) -> Optional[dict]:
        """
        Find a single node by label and properties.

        Args:
            label: Node label
            properties: Properties to match

        Returns:
            Dictionary containing node data or None if not found
        """
        conditions = " AND ".join([f"n.{key} = ${key}" for key in properties.keys()])
        query = f"MATCH (n:{label}) WHERE {conditions} RETURN n LIMIT 1"

        result = self.run_single_query(query, properties)
        return result["n"] if result else None

    def find_nodes(self, label: str, properties: Optional[dict[str, Any]] = None) -> list[dict]:
        """
        Find multiple nodes by label and optional properties.

        Args:
            label: Node label
            properties: Optional properties to match

        Returns:
            List of dictionaries containing node data
        """
        if properties:
            conditions = " AND ".join([f"n.{key} = ${key}" for key in properties.keys()])
            query = f"MATCH (n:{label}) WHERE {conditions} RETURN n"
        else:
            query = f"MATCH (n:{label}) RETURN n"

        results = self.run_query(query, properties or {})
        return [result["n"] for result in results]

    def find_shortest_path(
        self,
        start_label: str,
        start_properties: dict[str, Any],
        end_label: str,
        end_properties: dict[str, Any],
        relationship_type: str = "*",
    ) -> Optional[list[dict]]:
        """
        Find shortest path between two nodes.

        Args:
            start_label: Label of start node
            start_properties: Properties to identify start node
            end_label: Label of end node
            end_properties: Properties to identify end node
            relationship_type: Type of relationships to traverse (default: any)

        Returns:
            List of node dictionaries representing the path, or None if no path exists
        """
        start_conditions = " AND ".join(
            [f"start.{key} = $start_{key}" for key in start_properties.keys()]
        )
        end_conditions = " AND ".join([f"end.{key} = $end_{key}" for key in end_properties.keys()])

        # Prepare parameters
        params = {}
        for key, value in start_properties.items():
            params[f"start_{key}"] = value
        for key, value in end_properties.items():
            params[f"end_{key}"] = value

        # Build relationship pattern - fix syntax for variable length paths
        if relationship_type == "*":
            rel_pattern = "[*]"
        else:
            rel_pattern = f"[:{relationship_type}*]"

        query = f"""
        MATCH (start:{start_label}) WHERE {start_conditions}
        MATCH (end:{end_label}) WHERE {end_conditions}
        MATCH path = shortestPath((start)-{rel_pattern}-(end))
        RETURN [node in nodes(path) | node] as path
        """

        result = self.run_single_query(query, params)

        if result and result["path"]:
            self.logger.info(f"Found shortest path with {len(result['path'])} nodes")
            return result["path"]
        else:
            self.logger.warning("No path found between specified nodes")
            return None

    def count_nodes(self, label: Optional[str] = None) -> int:
        """
        Count nodes in the database.

        Args:
            label: Optional label to filter nodes

        Returns:
            Number of nodes
        """
        if label:
            query = f"MATCH (n:{label}) RETURN count(n) as count"
        else:
            query = "MATCH (n) RETURN count(n) as count"

        result = self.run_single_query(query)
        return result["count"] if result else 0

    def count_relationships(self, relationship_type: Optional[str] = None) -> int:
        """
        Count relationships in the database.

        Args:
            relationship_type: Optional relationship type to filter

        Returns:
            Number of relationships
        """
        if relationship_type:
            query = f"MATCH ()-[r:{relationship_type}]-() RETURN count(r) as count"
        else:
            query = "MATCH ()-[r]-() RETURN count(r) as count"

        result = self.run_single_query(query)
        return result["count"] if result else 0

    def get_database_info(self) -> dict[str, Any]:
        """
        Get basic information about the database.

        Returns:
            Dictionary containing database statistics
        """
        node_count = self.count_nodes()
        rel_count = self.count_relationships()

        # Get node labels
        labels_result = self.run_query("CALL db.labels()")
        labels = [record["label"] for record in labels_result]

        # Get relationship types
        rel_types_result = self.run_query("CALL db.relationshipTypes()")
        rel_types = [record["relationshipType"] for record in rel_types_result]

        info = {
            "node_count": node_count,
            "relationship_count": rel_count,
            "node_labels": labels,
            "relationship_types": rel_types,
        }

        self.logger.info(f"Database info: {info}")
        return info
