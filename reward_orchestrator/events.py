import time
import pika
import json
import os
import requests
import utils as rabbit
from dotenv import load_dotenv

load_dotenv()

RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:5402")
MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL", "http://mission:5403")
QUEUE_NAME = "reward_orchestrator.queue"
EXCHANGE_NAME = "events.topic"

def should_update_mission(user_id, event_type):
    try:
        url = f"{MISSION_SERVICE_URL}/mission/check/{user_id}/{event_type}"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            return res.json().get("should_update", False)
    except Exception as e:
        print(f"[!] Failed to check mission eligibility: {e}")
    return False

def handle_event(event):
    event_type = event.get("type")
    user_id = event.get("user_id")

    print(f"[x] Handling event: {event_type} for user: {user_id}")

    if event_type == "TRADE_IN_SUCCESS":
        try:
            res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
                "user_id": user_id,
                "points": 50
            })
            print(f"[✓] Wallet credited: {res.status_code} - {res.text}")
            print(f"[>] Sending wallet credit for {user_id} with {points} points")

        
        except Exception as e:
            print(f"[!] Wallet credit failed: {e}")

        # Conditionally update mission
        if should_update_mission(user_id, event_type):
            try:
                res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
                    "user_id": user_id,
                    "event_type": event_type
                })
                print(f"[✓] Mission update sent: {res.status_code}")
            except Exception as e:
                print(f"[!] Mission update failed: {e}")
        else:
            print(f"[-] Skipping mission update: no joined mission for {event_type}")

    elif event_type == "ECO_PURCHASE":
        if should_update_mission(user_id, event_type):
            try:
                res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
                    "user_id": user_id,
                    "event_type": event_type
                })
                print(f"[✓] Mission update for eco-purchase: {res.status_code}")
            except Exception as e:
                print(f"[!] Mission update for eco-purchase failed: {e}")
        else:
            print(f"[-] Skipping mission update: user has not joined ECO_PURCHASE mission")

    elif event_type == "MISSION_COMPLETED":
        points = event.get("reward_points", 0)
        try:
            res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
                "user_id": user_id,
                "points": points
            })
            print(f"[✓] Wallet credited for mission: {res.status_code}")
        except Exception as e:
            print(f"[!] Wallet credit from mission failed: {e}")

def start_event_listener():
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, EXCHANGE_NAME, "topic", {QUEUE_NAME: "#"})

    def callback(ch, method, properties, body):
        try:
            event = json.loads(body)
            print(f"[📩] Received event: {event}")
            handle_event(event)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[!] Error processing message: {e}")

    rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, EXCHANGE_NAME, "topic", QUEUE_NAME, callback)

    print("[*] Listening for events...")
    channel.start_consuming()


# import os
# import json
# import pika
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
# WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL")
# MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL")

# QUEUE_NAME = "user.events"

# def handle_event(event):
#     event_type = event.get("type")
#     user_id = event.get("user_id")

#     if event_type == "TRADE_IN_SUCCESS":
#         # Directly credit wallet with, say, 50 points
#         requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#             "user_id": user_id,
#             "points": 50
#         })

#         requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#             "user_id": user_id,
#             "event_type": event_type
#         })

#     elif event_type == "ECO_PURCHASE":
#         requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#             "user_id": user_id,
#             "event_type": event_type
#         })

#     elif event_type == "MISSION_COMPLETED":
#         points = event.get("reward_points", 0)
#         requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#             "user_id": user_id,
#             "points": points
#         })


# #     if event_type == "TRADE_IN_SUCCESS" or event_type == "ECO_PURCHASE":
# #         requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
# #             "user_id": user_id,
# #             "event_type": event_type
# #         })

# #     elif event_type == "MISSION_COMPLETED":
# #         points = event.get("reward_points", 0)
# #         requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
# #             "user_id": user_id,
# #             "points": points
# #         })


# def start_event_listener():
#     connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
#     channel = connection.channel()
#     channel.queue_declare(queue=QUEUE_NAME, durable=True)

#     def callback(ch, method, properties, body):
#         event = json.loads(body)
#         print(f"[x] Received event: {event}")
#         handle_event(event)
#         ch.basic_ack(delivery_tag=method.delivery_tag)

#     channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
#     print('[*] Waiting for events. To exit press CTRL+C')
#     channel.start_consuming()
##################################################

####### 0401

# import time
# import pika
# import json
# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
# WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:5402")
# MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL", "http://mission:5403")

# QUEUE_NAME = "user.events"

# def handle_event(event):
#     event_type = event.get("type")
#     user_id = event.get("user_id")

#     if event_type == "TRADE_IN_SUCCESS":
#         print(f"[x] Handling TRADE_IN_SUCCESS for user: {user_id}")
#         # Credit wallet directly
#         try:
#             res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#                 "user_id": user_id,
#                 "points": 50
#             })
#             print(f"[+] Wallet credited: {res.status_code}, {res.text}")
#         except Exception as e:
#             print(f"[!] Failed to credit wallet: {e}")

#         # Also notify mission service (optional)
#         try:
#             requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#                 "user_id": user_id,
#                 "event_type": event_type
#             })
#         except Exception as e:
#             print(f"[!] Mission service failed: {e}")

#     elif event_type == "MISSION_COMPLETED":
#         points = event.get("reward_points", 0)
#         try:
#             requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#                 "user_id": user_id,
#                 "points": points
#             })
#         except Exception as e:
#             print(f"[!] Failed to credit wallet from mission: {e}")

# def start_event_listener():
#     print("[*] Starting event listener...")

#     # Retry loop for RabbitMQ connection
#     for i in range(10):
#         try:
#             connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
#             print("[✓] Connected to RabbitMQ")
#             break
#         except pika.exceptions.AMQPConnectionError as e:
#             print(f"[!] RabbitMQ not ready yet. Retrying in 3s... ({i+1}/10)")
#             time.sleep(3)
#     else:
#         print("[✘] Failed to connect to RabbitMQ after retries.")
#         return

#     channel = connection.channel()
#     channel.queue_declare(queue=QUEUE_NAME, durable=True)

#     def callback(ch, method, properties, body):
#         event = json.loads(body)
#         print(f"[x] Received event: {event}")
#         handle_event(event)
#         ch.basic_ack(delivery_tag=method.delivery_tag)

#     channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
#     print('[*] Waiting for events. To exit press CTRL+C')
#     channel.start_consuming()

# import time
# import pika
# import json
# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
# WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:5402")
# MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL", "http://mission:5403")
# QUEUE_NAME = "user.events"

# def handle_event(event):
#     event_type = event.get("type")
#     user_id = event.get("user_id")

#     print(f"[x] Handling event: {event_type} for user: {user_id}")

#     if event_type == "TRADE_IN_SUCCESS":
#         # Credit 50 points to wallet
#         try:
#             res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#                 "user_id": user_id,
#                 "points": 50
#             })
#             print(f"[✓] Wallet credit response: {res.status_code} - {res.text}")
#         except Exception as e:
#             print(f"[!] Wallet credit failed: {e}")

#         # Optional: Notify mission service
#         try:
#             res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#                 "user_id": user_id,
#                 "event_type": event_type
#             })
#             print(f"[✓] Mission update response: {res.status_code}")
#         except Exception as e:
#             print(f"[!] Mission update failed: {e}")

#     elif event_type == "MISSION_COMPLETED":
#         points = event.get("reward_points", 0)
#         try:
#             res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#                 "user_id": user_id,
#                 "points": points
#             })
#             print(f"[✓] Wallet credited from mission: {res.status_code}")
#         except Exception as e:
#             print(f"[!] Wallet credit from mission failed: {e}")

# def start_event_listener():
#     print(f"[*] Starting event listener... Connecting to RabbitMQ at: {RABBITMQ_HOST}")

#     # Retry RabbitMQ connection
#     for i in range(10):
#         try:
#             connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
#             print("[✓] Connected to RabbitMQ")
#             break
#         except pika.exceptions.AMQPConnectionError:
#             print(f"[!] RabbitMQ not ready yet. Retrying in 3s... ({i+1}/10)")
#             time.sleep(3)
#     else:
#         print("[✘] Could not connect to RabbitMQ after retries.")
#         return

#     channel = connection.channel()
#     channel.queue_declare(queue=QUEUE_NAME, durable=True)


#     def callback(ch, method, properties, body):
#         try:
#             event = json.loads(body)
#             print(f"[📩] Received event: {event}")
#             handle_event(event)
#             ch.basic_ack(delivery_tag=method.delivery_tag)
#         except Exception as e:
#             print(f"[!] Error processing message: {e}")

#     channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
#     print("[*] Listening for events...")
#     channel.start_consuming()

    # def callback(ch, method, properties, body):
    #     event = json.loads(body)
    #     print(f"[→] Received event: {event}")
    #     handle_event(event)
    #     ch.basic_ack(delivery_tag=method.delivery_tag)

    # channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
    # print("[*] Waiting for messages...")
    # channel.start_consuming()


###################################
#0401


# import time
# import pika
# import json
# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
# WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:5402")
# MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL", "http://mission:5403")
# QUEUE_NAME = "reward_orchestrator.queue"
# EXCHANGE_NAME = "events.topic"

# def handle_event(event):
#     event_type = event.get("type")
#     user_id = event.get("user_id")

#     print(f"[x] Handling event: {event_type} for user: {user_id}")

#     if event_type == "TRADE_IN_SUCCESS":
#         try:
#             res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#                 "user_id": user_id,
#                 "points": 50
#             })
#             print(f"[✓] Wallet credited: {res.status_code} - {res.text}")
#         except Exception as e:
#             print(f"[!] Wallet credit failed: {e}")

#         # try:
#         #     res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#         #         "user_id": user_id,
#         #         "event_type": event_type
#         #     })
#         #     print(f"[✓] Mission update sent: {res.status_code}")
#         # except Exception as e:
#         #     print(f"[!] Mission update failed: {e}")

#     elif event_type == "ECO_PURCHASE":
#         try:
#             res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#                 "user_id": user_id,
#                 "event_type": event_type
#             })
#             print(f"[✓] Mission update for eco-purchase: {res.status_code}")
#         except Exception as e:
#             print(f"[!] Mission update for eco-purchase failed: {e}")

#     elif event_type == "MISSION_COMPLETED":
#         points = event.get("reward_points", 0)
#         try:
#             res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
#                 "user_id": user_id,
#                 "points": points
#             })
#             print(f"[✓] Wallet credited for mission: {res.status_code}")
#         except Exception as e:
#             print(f"[!] Wallet credit from mission failed: {e}")

# def start_event_listener():
#     print(f"[*] Starting event listener... Connecting to RabbitMQ at: {RABBITMQ_HOST}")
#     for i in range(10):
#         try:
#             connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
#             print("[✓] Connected to RabbitMQ")
#             break
#         except pika.exceptions.AMQPConnectionError:
#             print(f"[!] RabbitMQ not ready yet. Retrying in 3s... ({i+1}/10)")
#             time.sleep(3)
#     else:
#         print("[✘] Could not connect to RabbitMQ after retries.")
#         return

#     channel = connection.channel()
#     channel.exchange_declare(exchange=EXCHANGE_NAME, exchange_type="topic", durable=True)
#     channel.queue_declare(queue=QUEUE_NAME, durable=True)
#     channel.queue_bind(exchange=EXCHANGE_NAME, queue=QUEUE_NAME, routing_key="#")

#     def callback(ch, method, properties, body):
#         try:
#             event = json.loads(body)
#             print(f"[📩] Received event: {event}")
#             handle_event(event)
#             ch.basic_ack(delivery_tag=method.delivery_tag)
#         except Exception as e:
#             print(f"[!] Error processing message: {e}")

#     channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
#     print("[*] Listening for events...")
#     channel.start_consuming()


