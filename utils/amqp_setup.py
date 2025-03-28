import pika
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

def setup_rabbitmq(hostname, port, exchange_name, exchange_type, queues):
    """
    Ensure the exchange and queues exist before consuming messages.

    :param hostname: RabbitMQ server hostname
    :param port: RabbitMQ server port
    :param exchange_name: Name of the exchange
    :param exchange_type: Type of the exchange (topic, direct, fanout)
    :param queues: Dictionary {queue_name: routing_key}
    """
    connection = None
    try:
        logging.info(f"Connecting to RabbitMQ at {hostname}:{port}...")
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

    except Exception as e:
        logging.error(f"Error setting up RabbitMQ: {e}")

    finally:
        if connection:
            connection.close()
            logging.info("RabbitMQ connection closed.")
