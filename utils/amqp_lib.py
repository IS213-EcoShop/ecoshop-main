import time
import pika


def connect(hostname, port, exchange_name, exchange_type, max_retries=12, retry_interval=5):
    retries = 0
    while retries < max_retries:
        retries += 1
        try:
            print(f"Connecting to AMQP broker {hostname}:{port}...")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=hostname,
                    port=port,
                    heartbeat=300,
                    blocked_connection_timeout=300,
                )
            )
            print("Connected")
            channel = connection.channel()

            # Check if the exchange exists
            print(f"Checking existence of exchange: {exchange_name}")
            channel.exchange_declare(
                exchange=exchange_name,
                exchange_type=exchange_type,
                passive=True,  # passive=True will raise an error if the exchange doesn't exist
            )
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
    while True:
        try:
            connection, channel = connect(
                hostname=hostname,
                port=port,
                exchange_name=exchange_name,
                exchange_type=exchange_type,
            )

            print(f"Consuming from queue: {queue_name}")
            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=True
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
