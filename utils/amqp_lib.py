import time
import pika
import json


def connect(hostname, port, exchange_name, exchange_type,queues ={}, max_retries=12, retry_interval=5):
    retries = 0
    while retries < max_retries:
        retries += 1
        try:
            print(f"=========== Connecting to AMQP broker {hostname}:{port} for {exchange_name}... ===========")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=hostname,
                    port=port,
                    heartbeat=300,
                )
            )
            print("Connected")
            channel = connection.channel()

            # Declare the exchange explicitly if it doesn't exist
            print(f"=========== Declaring exchange: {exchange_name} ===========")
            channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type,
                durable=True  # Ensure persistence
            )

            if queues:
                for queue_name, routing_key in queues.items():
                    print(f"=========== Declaring queue: {queue_name} for {exchange_name} ===========")
                    channel.queue_declare(queue=queue_name, durable=True)
                    print(f"=========== Binding queue {queue_name} to {exchange_name} with routing key {routing_key} ===========")
                    channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)

            return connection, channel

        except pika.exceptions.AMQPConnectionError as exception:
            print(f"Failed to connect: {exception}")
            print(f"Retrying in {retry_interval} seconds...")
            time.sleep(retry_interval)

    raise Exception(f"Max {max_retries} retries exceeded...")


def close(connection, channel):
    channel.close()
    connection.close()


def start_consuming(hostname, port, exchange_name, exchange_type, queue_name, callback):
    connection = None  # Initialize connection variable
    channel = None  # Initialize channel variable
    while True:
        try:
            connection, channel = connect(
                hostname=hostname,
                port=port,
                exchange_name=exchange_name,
                exchange_type=exchange_type,
            )

            print(f"=========== Consuming from queue: {queue_name} ===========")
            # Use manual acknowledgment (auto_ack=False)
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=False  # Set auto_ack to False for manual acknowledgment
            )
            channel.start_consuming()

        except pika.exceptions.ChannelClosedByBroker:
            print(f"Queue {queue_name} not found. Closing connection...")
            connection.close()
            raise Exception(f"Queue {queue_name} not found.")

        except pika.exceptions.ConnectionClosedByBroker:
            print("Connection closed by broker. Reconnecting...")
            continue

        except KeyboardInterrupt:
            close(connection, channel)
            break


def publish_message(channel, exchange_name, routing_key, message_body, properties=None):
    """
    Publishes a message to a RabbitMQ exchange with a given routing key.
    """
    try:
        if isinstance(message_body, dict):
            message_body = json.dumps(message_body)
        
        if not properties:
            properties = pika.BasicProperties(delivery_mode=2)  # Persistent message
        
        channel.basic_publish(
            exchange=exchange_name,
            routing_key=routing_key,
            body=message_body,
            properties=properties
        )
        print(f"Message published to {exchange_name} with routing key {routing_key}: {message_body}")

    except Exception as e:
        print(f"Error publishing message: {e}")
        raise e