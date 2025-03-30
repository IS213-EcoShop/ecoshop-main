import pika
import json
import time

RABBITMQ_HOST = "rabbitmq"  
EMAIL_EXCHANGE_NAME = "notification_exchange"  # Use a topic exchange for routing
QUEUE_NAME = "notification_queue"  # Default queue name
ROUTING_KEY = "email.welcome"  # Default routing key, can be overridden dynamically

def get_rabbitmq_connection(EXCHANGE_NAME):
    """
    Establishes a connection to RabbitMQ with retry logic.
    Returns: (connection, channel)
    """
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(RABBITMQ_HOST))
            channel = connection.channel()
            # Declare the exchange (topic exchange) and the queue
            channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type='topic', durable=True)
            channel.queue_declare(queue=QUEUE_NAME, durable=True)  # Ensure queue exists
            return connection, channel
        except (pika.exceptions.AMQPConnectionError, pika.exceptions.ChannelClosedByBroker) as e:
            print(f"Failed to connect to RabbitMQ, retrying in 5s... Error: {e}")
            time.sleep(5)

def send_notification(email, channel, message, data, routing_key, exchange_name):
    """
    Sends a notification message to the RabbitMQ exchange with routing key.
    """
    notification = {
        "email": email,
        "message": message,
        "data": data if data else {}  # Default to empty dict if no data is provided
    }
    try:
        channel.basic_publish(
                exchange=exchange_name,
                routing_key=routing_key,  # Use dynamic routing key
                body=json.dumps(notification),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make the message persistent
                )
        )
        print(f"Notification sent: {notification} with routing key: {routing_key}")
    
    except Exception as e:
        print(f"Error sending notification: {e}")
        raise  # Re-raise the error after logging it

def notify_user(email, message, data={}, routing_key=ROUTING_KEY, exchange_name="notification_exchange"):
    """
    Main function to notify a user by sending a message to the queue with routing key.
    Takes in email, message, (optional) data, and (optional) routing_key
    """
    print("======================================================================")
    connection, channel = get_rabbitmq_connection(exchange_name)
    try:
        send_notification(email, channel, message, data, routing_key, exchange_name)
    finally:
        channel.close()
        connection.close()  # Always close connection
