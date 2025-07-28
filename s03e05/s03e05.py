import logging
from clients.centrala_client import CentralaClient
from clients.neo4j_client import Neo4jClient


class TaskSolver:
    """
    Solver for S03E04 task - finding shortest path between users using graph database.
    """

    def __init__(self, centrala_client: CentralaClient, neo4j_client: Neo4jClient):
        """
        Initialize TaskSolver with required clients.

        Args:
            centrala_client: Client for Centrala API interactions
            neo4j_client: Client for Neo4j graph database operations
        """
        self.logger = logging.getLogger("TaskSolver")
        self.centrala_client = centrala_client
        self.neo4j_client = neo4j_client
        self.logger.info("TaskSolver initialized")

    def fetch_users_from_database(self) -> list[dict]:
        """
        Fetch all users from the MySQL database via Centrala API.

        Returns:
            List of user dictionaries with id and username
        """
        self.logger.info("Fetching users from database")

        query = "SELECT id, username FROM users"
        response = self.centrala_client.query_database(query)

        if "reply" in response and isinstance(response["reply"], list):
            users = response["reply"]
            self.logger.info(f"Retrieved {len(users)} users from database")
            return users
        else:
            self.logger.error("Failed to retrieve users from database")
            raise Exception("Could not fetch users data")

    def fetch_connections_from_database(self) -> list[dict]:
        """
        Fetch all connections from the MySQL database via Centrala API.

        Returns:
            List of connection dictionaries from the connections table
        """
        self.logger.info("Fetching connections from connections table")

        # First, let's see what columns are in the connections table
        describe_query = "DESCRIBE connections"
        describe_response = self.centrala_client.query_database(describe_query)
        self.logger.info(f"Connections table structure: {describe_response}")

        # Fetch all connections - we'll determine the column names based on the table structure
        query = "SELECT * FROM connections"
        response = self.centrala_client.query_database(query)

        if "reply" in response and isinstance(response["reply"], list):
            connections = response["reply"]
            self.logger.info(f"Retrieved {len(connections)} connections from connections table")

            # Log first connection to see the structure
            if connections:
                self.logger.info(f"Sample connection record: {connections[0]}")

            return connections
        else:
            self.logger.error("Failed to retrieve connections from connections table")
            raise Exception("Could not fetch connections data")

    def load_users_to_graph(self, users: list[dict]):
        """
        Load users as nodes into Neo4j database.

        Args:
            users: List of user dictionaries from database
        """
        self.logger.info("Loading users into Neo4j as nodes")

        # Prepare nodes data for batch creation
        nodes_data = []
        for user in users:
            # Using userId instead of id to avoid conflicts with Neo4j internal id
            nodes_data.append({"userId": user["id"], "username": user["username"]})

        # Create all user nodes in batch
        self.neo4j_client.create_nodes_batch("User", nodes_data)
        self.logger.info(f"Loaded {len(users)} users as nodes")

    def load_connections_to_graph(self, connections: list[dict]):
        """
        Load connections as relationships into Neo4j database.

        Args:
            connections: List of connection dictionaries from connections table
        """
        self.logger.info("Loading connections into Neo4j as relationships")

        if not connections:
            self.logger.warning("No connections to load")
            return

        # Determine the column names from the first connection record
        first_connection = connections[0]
        connection_keys = list(first_connection.keys())
        self.logger.info(f"Connection record keys: {connection_keys}")

        # Try to identify the user ID columns
        # Common patterns: user1_id/user2_id, from_user/to_user, user_a/user_b, etc.
        user1_key = None
        user2_key = None

        for key in connection_keys:
            key_lower = key.lower()
            if "user1" in key_lower or "from" in key_lower or "user_a" in key_lower:
                user1_key = key
            elif "user2" in key_lower or "to" in key_lower or "user_b" in key_lower:
                user2_key = key

        # If standard patterns don't work, assume first two columns are the user IDs
        if not user1_key or not user2_key:
            if len(connection_keys) >= 2:
                user1_key = connection_keys[0]
                user2_key = connection_keys[1]
                self.logger.info(f"Using first two columns as user IDs: {user1_key}, {user2_key}")
            else:
                raise Exception("Cannot determine user ID columns in connections table")

        self.logger.info(f"Using columns: {user1_key} -> {user2_key}")

        # Prepare relationships data for batch creation
        relationships_data = []
        for connection in connections:
            user1_id = connection[user1_key]
            user2_id = connection[user2_key]

            # Create bidirectional relationships (assuming friendship is mutual)
            relationships_data.append(
                {
                    "start_filter": {"userId": user1_id},
                    "end_filter": {"userId": user2_id},
                    "rel_type": "KNOWS",
                }
            )
            relationships_data.append(
                {
                    "start_filter": {"userId": user2_id},
                    "end_filter": {"userId": user1_id},
                    "rel_type": "KNOWS",
                }
            )

        # Create all relationships in batch
        self.neo4j_client.create_relationships_batch(relationships_data)
        self.logger.info(f"Loaded {len(connections)} connections as bidirectional relationships")

    def find_shortest_path_between_users(self, start_name: str, end_name: str) -> list[str]:
        """
        Find shortest path between two users using Neo4j client.

        Args:
            start_name: Starting user's name
            end_name: Ending user's name

        Returns:
            List of usernames representing the shortest path
        """
        self.logger.info(f"Finding shortest path from {start_name} to {end_name}")

        path_nodes = self.neo4j_client.find_shortest_path(
            start_label="User",
            start_properties={"username": start_name},
            end_label="User",
            end_properties={"username": end_name},
            relationship_type="KNOWS",
        )

        if path_nodes:
            # Extract usernames from path nodes
            path_usernames = [node["username"] for node in path_nodes]
            self.logger.info(
                f"Found shortest path with {len(path_usernames)} nodes: {' -> '.join(path_usernames)}"
            )
            return path_usernames
        else:
            self.logger.error(f"No path found between {start_name} and {end_name}")
            raise Exception(f"No path exists between {start_name} and {end_name}")

    def solve_task(self) -> str:
        """
        Main method to solve the connections task.

        Returns:
            Comma-separated string of names representing the shortest path
        """
        try:
            # Step 1: Fetch data from MySQL database
            self.logger.info("Step 1: Fetching data from MySQL database")
            users = self.fetch_users_from_database()
            connections = self.fetch_connections_from_database()

            # Step 2: Clear and populate graph database
            self.logger.info("Step 2: Setting up graph database")
            self.neo4j_client.clear_database()
            self.load_users_to_graph(users)
            self.load_connections_to_graph(connections)

            # Step 3: Verify database setup
            db_info = self.neo4j_client.get_database_info()
            self.logger.info(f"Graph database populated: {db_info}")

            # Step 4: Find shortest path
            self.logger.info("Step 3: Finding shortest path")
            path = self.find_shortest_path_between_users("Rafał", "Barbara")

            # Step 5: Format result
            result = ",".join(path)
            self.logger.info(f"Shortest path result: {result}")

            return result

        except Exception as e:
            self.logger.error(f"Error solving task: {e}")
            raise


def main():
    """
    Main function to execute the S03E04 task.
    """
    # Configure logging
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    logger = logging.getLogger("S03E04")
    logger.info("Starting S03E04 - Connections task")

    neo4j_client = None

    try:
        # Initialize clients
        centrala_client = CentralaClient(task_identifier="database")

        neo4j_client = Neo4jClient()

        task_solver = TaskSolver(centrala_client=centrala_client, neo4j_client=neo4j_client)

        # Solve the task
        answer = task_solver.solve_task()

        # Send answer to Centrala
        centrala_client = CentralaClient(task_identifier="connections")
        logger.info(f"Sending answer: {answer}")
        centrala_client.send_answer(answer)

        logger.info("Task completed successfully!")

    except Exception as e:
        logger.error(f"Task failed: {e}")
        raise
    finally:
        # Always close Neo4j connection
        if neo4j_client:
            neo4j_client.close()


if __name__ == "__main__":
    main()
