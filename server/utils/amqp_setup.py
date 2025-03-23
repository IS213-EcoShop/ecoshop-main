#!/usr/bin/env python3

"""
A standalone script to create exchanges and queues on RabbitMQ.
"""

import pika

# RabbitMQ connection settings
amqp_host = "localhost"
amqp_port = 5672
exchange_name = "order_topic"
exchange_type = "topic"

# Define the queues for payment confirmation and order handling
payment_queue = "payment_confirmation_queue"
order_queue = "order_queue"


def create_exchange(hostname, port, exchange_name, exchange_type):
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

    print("Open channel")
    channel = connection.channel()

    # Set up the exchange if it doesn't exist
    print(f"Declaring exchange: {exchange_name}")
    channel.exchange_declare(
        exchange=exchange_name, exchange_type=exchange_type, durable=True
    )

    return channel


def create_queue(channel, exchange_name, queue_name, routing_key):
    print(f"Declaring queue: {queue_name}")
    channel.queue_declare(queue=queue_name, durable=True)
    
    # Bind the queue to the exchange via routing_key
    print(f"Binding queue {queue_name} to exchange {exchange_name} with routing key {routing_key}")
    channel.queue_bind(
        exchange=exchange_name, queue=queue_name, routing_key=routing_key
    )


# Create the exchange and queues
channel = create_exchange(
    hostname=amqp_host,
    port=amqp_port,
    exchange_name=exchange_name,
    exchange_type=exchange_type,
)

# Create payment confirmation queue
create_queue(
    channel=channel,
    exchange_name=exchange_name,
    queue_name=payment_queue,
    routing_key="payment.confirmation",
)

# Create order handling queue
create_queue(
    channel=channel,
    exchange_name=exchange_name,
    queue_name=order_queue,
    routing_key="order.*",
)

# Close the channel and connection after setting up
channel.close()
