import time
import pika
import json
import os
import requests
import threading
import utils as rabbit
import uuid
from dotenv import load_dotenv

load_dotenv()
processed_events = set()

# RabbitMQ
RABBITMQ_HOST = "rabbitmq"
RABBITMQ_PORT = 5672

# Microservices
WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:5402")
MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL", "http://mission:5403")

# Exchanges & Queues
TOPIC_EXCHANGE = "events.topic"
TOPIC_QUEUE = "reward_orchestrator.queue"

FANOUT_EXCHANGE = "place_order_exchange"
FANOUT_QUEUE = "reward_orchestrator.purchase"

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
    user_id = str(event.get("user_id"))  # Ensure user_id is a string

    print(f"[x] Handling event: {event_type} for user: {user_id}")

    if event_type == "TRADE_IN_SUCCESS":
        try:
            res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
                "user_id": user_id,
                "points": 50
            })
            print(f"[✓] Wallet credited: {res.status_code} - {res.text}")
        except Exception as e:
            print(f"[!] Wallet credit failed: {e}")

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
            print(f"[-] No joined mission for {event_type}")

    elif event_type == "ECO_PURCHASE":
        if should_update_mission(user_id, event_type):
            try:
                res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
                    "user_id": user_id,
                    "event_type": event_type
                })
                print(f"[✓] Mission update for ECO_PURCHASE: {res.status_code}")
            except Exception as e:
                print(f"[!] Mission update failed: {e}")
        else:
            print(f"[-] No joined mission for {event_type}")

    elif event_type == "MISSION_COMPLETED":
        points = event.get("reward_points", 0)
        print(f"[DEBUG] Received MISSION_COMPLETED with points: {points}")
        try:
            res = requests.post(f"{WALLET_SERVICE_URL}/wallet/credit", json={
                "user_id": user_id,
                "points": points
            })
            print(f"[✓] Wallet credited for mission: {res.status_code}")
        except Exception as e:
            print(f"[!] Wallet credit failed: {e}")

def start_event_listener():
    # Topic listener (e.g., TRADE_IN_SUCCESS, MISSION_COMPLETED)
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, TOPIC_EXCHANGE, "topic", {TOPIC_QUEUE: "#"})

    def callback_topic(ch, method, properties, body):
        try:
            event = json.loads(body)

            # Add deduplication logic here
            event_key = f"{event.get('type')}_{event.get('user_id')}"
            if event_key in processed_events:
                print(f"[WARN] Duplicate topic event detected: {event_key}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            processed_events.add(event_key)

            print(f"[📩 topic] Received event: {event}")
            handle_event(event)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            print(f"[!] Error processing topic message: {e}")

    threading.Thread(target=lambda: rabbit.start_consuming(
        RABBITMQ_HOST, RABBITMQ_PORT, TOPIC_EXCHANGE, "topic", TOPIC_QUEUE, callback_topic
    )).start()

    # Fanout listener (e.g., from order_service)
    rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, FANOUT_EXCHANGE, "fanout", {FANOUT_QUEUE: ""})

    def callback_fanout(ch, method, properties, body):
        try:
            payload = json.loads(body)
            profile = payload.get("user_details", {}).get("profile", {})
            user_id = profile.get("user_id")

            if user_id is None:
                print(f"[!] No user_id found in fanout message.")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return

            user_id_str = str(user_id)

            # Add deduplication logic here
            event_key = f"ECO_PURCHASE_{user_id_str}"
            if event_key in processed_events:
                print(f"[WARN] Duplicate fanout event detected: {event_key}")
                ch.basic_ack(delivery_tag=method.delivery_tag)
                return
            processed_events.add(event_key)

            print(f"[📩] [fanout] Received purchase event for user: {user_id_str}")

            handle_event({"type": "ECO_PURCHASE", "user_id": user_id_str})
            ch.basic_ack(delivery_tag=method.delivery_tag)

        except Exception as e:
            print(f"[!] Error processing fanout message: {e}")


    # def callback_fanout(ch, method, properties, body):
    #     try:
    #         payload = json.loads(body)
    #         user_info = payload.get("user_details", {})
    #         user_id = user_info.get("user_id") or user_info.get("userID")

    #         if user_id is None:
    #             print(f"[!] user_id not found in fanout payload: {payload}")
    #             ch.basic_ack(delivery_tag=method.delivery_tag)
    #             return

    #         print(f"[📩 fanout] Received order event for user: {user_id}")
    #         # Convert to string to keep downstream logic consistent
    #         handle_event({"type": "ECO_PURCHASE", "user_id": str(user_id)})

    #         ch.basic_ack(delivery_tag=method.delivery_tag)
    #     except Exception as e:
    #         print(f"[!] Error processing fanout message: {e}")

    threading.Thread(target=lambda: rabbit.start_consuming(
        RABBITMQ_HOST, RABBITMQ_PORT, FANOUT_EXCHANGE, "fanout", FANOUT_QUEUE, callback_fanout
    )).start()




# import time
# import pika
# import json
# import os
# import requests
# import threading
# import utils as rabbit
# from dotenv import load_dotenv

# load_dotenv()

# RABBITMQ_HOST = "rabbitmq"
# RABBITMQ_PORT = 5672

# WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:5402")
# MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL", "http://mission:5403")

# TOPIC_EXCHANGE = "events.topic"
# TOPIC_QUEUE = "reward_orchestrator.queue"

# FANOUT_EXCHANGE = "place_order_exchange"
# FANOUT_QUEUE = "reward_orchestrator.purchase"

# def should_update_mission(user_id, event_type):
#     try:
#         url = f"{MISSION_SERVICE_URL}/mission/check/{user_id}/{event_type}"
#         res = requests.get(url, timeout=3)
#         if res.status_code == 200:
#             return res.json().get("should_update", False)
#     except Exception as e:
#         print(f"[!] Failed to check mission eligibility: {e}")
#     return False

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

#         if should_update_mission(user_id, event_type):
#             try:
#                 res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#                     "user_id": user_id,
#                     "event_type": event_type
#                 })
#                 print(f"[✓] Mission update sent: {res.status_code}")
#             except Exception as e:
#                 print(f"[!] Mission update failed: {e}")
#         else:
#             print(f"[-] Skipping mission update: no joined mission for {event_type}")

#     elif event_type == "ECO_PURCHASE":
#         if should_update_mission(user_id, event_type):
#             try:
#                 res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#                     "user_id": user_id,
#                     "event_type": event_type
#                 })
#                 print(f"[✓] Mission update for eco-purchase: {res.status_code}")
#             except Exception as e:
#                 print(f"[!] Mission update for eco-purchase failed: {e}")
#         else:
#             print(f"[-] Skipping mission update: user has not joined ECO_PURCHASE mission")

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
#     # Consumer for topic-based events
#     rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, TOPIC_EXCHANGE, "topic", {TOPIC_QUEUE: "#"})

#     def callback_topic(ch, method, properties, body):
#         try:
#             event = json.loads(body)
#             print(f"[📩] [topic] Received event: {event}")
#             handle_event(event)
#             ch.basic_ack(delivery_tag=method.delivery_tag)
#         except Exception as e:
#             print(f"[!] Error processing topic message: {e}")

#     topic_thread = threading.Thread(target=lambda: rabbit.start_consuming(
#         RABBITMQ_HOST, RABBITMQ_PORT, TOPIC_EXCHANGE, "topic", TOPIC_QUEUE, callback_topic
#     ))
#     topic_thread.start()

#     # Consumer for fanout exchange (purchase success)
#     rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, FANOUT_EXCHANGE, "fanout", {FANOUT_QUEUE: ""})

#     def callback_fanout(ch, method, properties, body):
#         try:
#             payload = json.loads(body)
#             user = payload.get("user_details", {})
#             user_id = user.get("userID")
#             if not user_id:
#                 print(f"[!] No userID found in fanout message.")
#                 return
#             print(f"[📩] [fanout] Received purchase event for user: {user_id}")
#             handle_event({"type": "ECO_PURCHASE", "user_id": user_id})
#             ch.basic_ack(delivery_tag=method.delivery_tag)
#         except Exception as e:
#             print(f"[!] Error processing fanout message: {e}")

#     fanout_thread = threading.Thread(target=lambda: rabbit.start_consuming(
#         RABBITMQ_HOST, RABBITMQ_PORT, FANOUT_EXCHANGE, "fanout", FANOUT_QUEUE, callback_fanout
#     ))
#     fanout_thread.start()





# import time
# import pika
# import json
# import os
# import requests
# import utils as rabbit
# from dotenv import load_dotenv

# load_dotenv()

# RABBITMQ_HOST = "rabbitmq"
# RABBITMQ_PORT = 5672
# WALLET_SERVICE_URL = os.getenv("WALLET_SERVICE_URL", "http://wallet:5402")
# MISSION_SERVICE_URL = os.getenv("MISSION_SERVICE_URL", "http://mission:5403")
# QUEUE_NAME = "reward_orchestrator.queue"
# EXCHANGE_NAME = "events.topic"

# def should_update_mission(user_id, event_type):
#     try:
#         url = f"{MISSION_SERVICE_URL}/mission/check/{user_id}/{event_type}"
#         res = requests.get(url, timeout=3)
#         if res.status_code == 200:
#             return res.json().get("should_update", False)
#     except Exception as e:
#         print(f"[!] Failed to check mission eligibility: {e}")
#     return False

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
#             print(f"[>] Sending wallet credit for {user_id} with {points} points")

        
#         except Exception as e:
#             print(f"[!] Wallet credit failed: {e}")

#         # Conditionally update mission
#         if should_update_mission(user_id, event_type):
#             try:
#                 res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#                     "user_id": user_id,
#                     "event_type": event_type
#                 })
#                 print(f"[✓] Mission update sent: {res.status_code}")
#             except Exception as e:
#                 print(f"[!] Mission update failed: {e}")
#         else:
#             print(f"[-] Skipping mission update: no joined mission for {event_type}")

#     elif event_type == "ECO_PURCHASE":
#         if should_update_mission(user_id, event_type):
#             try:
#                 res = requests.post(f"{MISSION_SERVICE_URL}/mission/update", json={
#                     "user_id": user_id,
#                     "event_type": event_type
#                 })
#                 print(f"[✓] Mission update for eco-purchase: {res.status_code}")
#             except Exception as e:
#                 print(f"[!] Mission update for eco-purchase failed: {e}")
#         else:
#             print(f"[-] Skipping mission update: user has not joined ECO_PURCHASE mission")

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
#     rabbit.connect(RABBITMQ_HOST, RABBITMQ_PORT, EXCHANGE_NAME, "topic", {QUEUE_NAME: "#"})

#     def callback(ch, method, properties, body):
#         try:
#             event = json.loads(body)
#             print(f"[📩] Received event: {event}")
#             handle_event(event)
#             ch.basic_ack(delivery_tag=method.delivery_tag)
#         except Exception as e:
#             print(f"[!] Error processing message: {e}")

#     rabbit.start_consuming(RABBITMQ_HOST, RABBITMQ_PORT, EXCHANGE_NAME, "topic", QUEUE_NAME, callback)

#     print("[*] Listening for events...")
#     channel.start_consuming()

