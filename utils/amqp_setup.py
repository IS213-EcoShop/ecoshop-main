import pika
import logging
import time

# Configure logging
logging.basicConfig(level=logging.INFO)

def setup_rabbitmq(hostname, port, exchange_name, exchange_type, queues, max_retries=5, retry_delay=5):
    """
    Ensure the exchange and queues exist before consuming messages.

    :param hostname: RabbitMQ server hostname
    :param port: RabbitMQ server port
    :param exchange_name: Name of the exchange
    :param exchange_type: Type of the exchange (topic, direct, fanout)
    :param queues: Dictionary {queue_name: routing_key}
    :param max_retries: Maximum number of retries before failing
    :param retry_delay: Delay between retries in seconds
    """
    connection = None
    retries = 0

    while retries < max_retries:
        try:
            logging.info(f"Connecting to RabbitMQ at {hostname}:{port} (Attempt {retries + 1}/{max_retries})...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=hostname,
                    port=port,
                    heartbeat=300,
                    blocked_connection_timeout=300,
                )
            )
            channel = connection.channel()

            # Declare the exchange
            logging.info(f"Declaring exchange: {exchange_name} (Type: {exchange_type})")
            channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, durable=True)

            # Declare and bind each queue
            for queue_name, routing_key in queues.items():
                logging.info(f"Declaring queue: {queue_name}")
                channel.queue_declare(queue=queue_name, durable=True)
                logging.info(f"Binding queue {queue_name} to exchange {exchange_name} with routing key {routing_key}")
                channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)

            logging.info("RabbitMQ setup completed successfully.")
            break  # Exit the loop once successful

        except Exception as e:
            retries += 1
            logging.error(f"Error setting up RabbitMQ: {e}")
            if retries < max_retries:
                logging.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logging.error("Max retries reached. Failed to connect to RabbitMQ.")
                break

        finally:
            if connection:
                connection.close()
                logging.info("RabbitMQ connection closed.")
