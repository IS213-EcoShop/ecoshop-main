import os
import json
import pika
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

VERIFICATION_EXCHANGE_NAME = "verification_exchange"
DELIVERY_VERIFICATION_QUEUE_NAME = "delivery_verification_queue"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def list_pending_trades():
    res = supabase.table("trade_ins").select("*").eq("status", "pending").execute()
    return res.data

def publish_event(event):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()

        channel.exchange_declare(exchange="events.topic", exchange_type="topic", durable= True)

        routing_key = event.get("type", "trade.unknown").lower()

        channel.basic_publish(
            exchange="events.topic",
            routing_key=routing_key,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f"Published event to topic exchange: {routing_key} -> {event}")
    except Exception as e:
        print(f"Failed to publish event: {e}")

def update_trade_status(trade_id, status):
    # Update trade status in Supabase
    result = supabase.from_("trade_ins").update({"status": status}).eq("id", trade_id).execute()
    if result.data:
        trade = result.data[0]
        body = {
            "message": "Trade Unsuccessful",
            "user_id": trade["user_id"],
            "trade" : trade
        }
        
        # If accepted, publish TRADE_IN_SUCCESS event
        if status == "accepted":
            publish_event({
                "type": "TRADE_IN_SUCCESS",
                "user_id": trade["user_id"],
                "trade_id": trade_id
            })

            body["message"] = "Trade Successful"
        
        connection, channel = connect(RABBITMQ_HOST, 5672, VERIFICATION_EXCHANGE_NAME, "direct", {DELIVERY_VERIFICATION_QUEUE_NAME: "send_verification"})

        publish_message(channel, VERIFICATION_EXCHANGE_NAME, "send_verification",body)

        close(connection, channel)

        return trade
    return None

from flask_cors import CORS

def enable_cors(app):
    """Enable CORS for the Flask app."""
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})

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