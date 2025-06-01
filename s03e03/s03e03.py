import json
import logging

from clients.centrala_client import CentralaClient


class TaskSolver:
    """
    Provides methods to interact with the database via CentralaClient.
    """

    def __init__(self, centrala_client: CentralaClient):
        """
        Initializes the TaskSolver with a CentralaClient instance.

        Args:
            centrala_client (CentralaClient): An instance of the CentralaClient.
        """
        self.centrala_client = centrala_client

    def show_tables(self):
        """
        Returns a list of tables in the database.

        Returns:
            list[str]: List of table names.
        """
        logging.info("Fetching list of tables from the database.")

        sql_query = "SHOW TABLES;"
        database_response = self.centrala_client.query_database(query=sql_query)
        database_response = database_response.get("reply", {})
        # Extract table names from the response
        tables = [v for item in database_response for v in item.values()]
        return tables

    def show_create_table(self, table_name: str):
        """
        Returns the CREATE TABLE statement for the specified table.

        Args:
            table_name (str): The name of the table.

        Returns:
            str: The CREATE TABLE SQL statement.
        """
        logging.info(f"Fetching CREATE TABLE statement for table: {table_name}")

        sql_query = f"SHOW CREATE TABLE {table_name};"
        database_response = self.centrala_client.query_database(query=sql_query)

        logging.info(f"Response from database for table {table_name}: {database_response}")

        # Extract the CREATE TABLE statement from the response
        return database_response.get("reply", [{}])[0].get("Create Table", "")

    def select_all_from_table(self, table_name: str, order_by: str = ""):
        """
        Returns all rows from the specified table.

        Args:
            table_name (str): The name of the table.
            order_by (str, optional): Column name to order by.

        Returns:
            list[dict]: A list of rows, where each row is represented as a dictionary.
        """
        logging.info(f"Selecting all rows from table: {table_name}")

        sql_query = f"SELECT * FROM {table_name}"
        if order_by:
            sql_query += f" ORDER BY {order_by}"
        sql_query += ";"

        database_response = self.centrala_client.query_database(query=sql_query)

        logging.info(f"Response from database for table {table_name}: {database_response}")

        return database_response.get("reply", [])

    def get_the_solution(self):
        """
        Fetches the solution by querying for active datacenters managed by inactive users.
        The query was created by LLM but in chat mode - maybe too easy solution but well.

        Returns:
            list[dict]: List of dictionaries containing 'dc_id'.
        """
        logging.info("Fetching the solution from the database.")

        sql_query = """
        SELECT dc_id 
        FROM datacenters d
        JOIN users u ON d.manager = u.id
        WHERE d.is_active = 1 AND u.is_active = 0
        """

        database_response = self.centrala_client.query_database(query=sql_query)
        return database_response.get("reply", [])


def main():
    """
    Main execution function to interact with the database and send the answer.
    """
    centrala_client = CentralaClient(task_identifier="database")
    solver = TaskSolver(centrala_client=centrala_client)

    tables = solver.show_tables()

    table_create_statements = {}
    for table in tables:
        table_create = solver.show_create_table(table_name=table)
        table_create_statements[table] = table_create

    logging.info(f"Table create statements: {json.dumps(table_create_statements, indent=2)}")

    # Fetch the correct order and reconstruct the secret flag
    correct_order_reply = solver.select_all_from_table(
        table_name="correct_order", order_by="weight"
    )
    secret_flag = "".join([item["letter"] for item in correct_order_reply])
    logging.info(f"Secret flag: {secret_flag}")

    # Get the solution and send the answer
    solution_response = solver.get_the_solution()
    dc_ids = [item["dc_id"] for item in solution_response]

    centrala_client.send_answer(answer=dc_ids)


