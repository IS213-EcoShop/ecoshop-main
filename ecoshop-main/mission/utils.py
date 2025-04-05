import os
import json
import pika
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def publish_event(event: dict):
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
        channel = connection.channel()
        channel.exchange_declare(exchange="events.topic", exchange_type="topic", durable=True)
        routing_key = "mission.completed"
        channel.basic_publish(
            exchange="events.topic",
            routing_key=routing_key,
            body=json.dumps(event),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        connection.close()
        print(f"[✓] Published mission completion event: {event}")
    except Exception as e:
        print(f"[!] Failed to publish mission event: {e}")

def list_all_missions():
    return supabase.table("mission").select("*").execute().data

def join_mission(user_id, mission_id):
    print(f"[JOIN] User {user_id} joining mission {mission_id}")
    try:
        # Check if already joined
        existing = supabase.table("user_missions").select("*") \
            .eq("user_id", user_id).eq("mission_id", mission_id).execute().data
        if existing:
            print("[JOIN] Already joined")
            return

        supabase.table("user_missions").insert({
            "user_id": user_id,
            "mission_id": mission_id,
            "progress": 0,
            "completed": False
        }).execute()
        print("[JOIN] Mission joined successfully")
    except Exception as e:
        print(f"[JOIN ERROR] {e}")
        raise  # 👈 Rethrow to be caught in your route


def update_mission_progress(user_id, event_type):
    print(f"[MISSION] Updating progress for user: {user_id}, event: {event_type}")
    missions = supabase.table("mission").select("*").eq("event_type", event_type).execute().data
    results = []

    if not missions:
        print(f"[!] No matching missions for event_type={event_type}")
    else:
        print(f"[✓] Found {len(missions)} mission(s) for event_type={event_type}")

    for mission in missions:
        mission_id = mission['id']
        goal = mission['goal']
        reward = mission['reward_points']

        print(f"[MISSION] Checking mission_id={mission_id} with goal={goal} and reward={reward}")

        res = supabase.table("user_missions").select("*") \
            .eq("user_id", user_id).eq("mission_id", mission_id).execute().data

        if res:
            user_mission = res[0]
            if user_mission['completed']:
                print(f"[MISSION] User already completed mission {mission_id}")
                results.append({"mission_id": mission_id, "status": "already completed"})
                continue

            progress = user_mission['progress'] + 1
            completed = progress >= goal
            print(f"[MISSION] Progress: {user_mission['progress']} -> {progress}, completed={completed}")

            supabase.table("user_missions").update({
                "progress": progress,
                "completed": completed
            }).eq("id", user_mission['id']).execute()

            results.append({"mission_id": mission_id, "progress": progress, "completed": completed})

            if completed:
                print(f"[✓] Mission {mission_id} completed — emitting reward")
                publish_event({
                    "type": "MISSION_COMPLETED",
                    "user_id": user_id,
                    "mission_id": mission_id,
                    "reward_points": reward
                })
        # else:
        #     progress = 1
        #     completed = progress >= goal
        #     print(f"[+] Creating new user_mission with progress={progress}, completed={completed}")

        #     new_entry = {
        #         "user_id": user_id,
        #         "mission_id": mission_id,
        #         "progress": progress,
        #         "completed": completed
        #     }
        #     supabase.table("user_missions").insert(new_entry).execute()
            results.append({"mission_id": mission_id, "progress": progress, "completed": completed})

            if completed:
                print(f"[✓] Mission {mission_id} completed (new record) — emitting reward")
                publish_event({
                    "type": "MISSION_COMPLETED",
                    "user_id": user_id,
                    "mission_id": mission_id,
                    "reward_points": reward
                })
    return results

# def update_mission_progress(user_id, event_type):
#     missions = supabase.table("mission").select("*").eq("event_type", event_type).execute().data
#     results = []
#     for mission in missions:
#         mission_id = mission['id']
#         goal = mission['goal']
#         reward = mission['reward_points']

#         res = supabase.table("user_missions").select("*").eq("user_id", user_id).eq("mission_id", mission_id).execute().data

#         if res:
#             user_mission = res[0]
#             if user_mission['completed']:
#                 results.append({"mission_id": mission_id, "status": "already completed"})
#                 continue
#             progress = user_mission['progress'] + 1
#             completed = progress >= goal
#             supabase.table("user_missions").update({"progress": progress, "completed": completed}).eq("id", user_mission['id']).execute()
#             results.append({"mission_id": mission_id, "progress": progress, "completed": completed})

#             if completed:
#                 publish_event({
#                     "type": "MISSION_COMPLETED",
#                     "user_id": user_id,
#                     "mission_id": mission_id,
#                     "reward_points": reward
#                 })
#         else:
#             progress = 1
#             completed = progress >= goal
#             new_entry = {
#                 "user_id": user_id,
#                 "mission_id": mission_id,
#                 "progress": progress,
#                 "completed": completed
#             }
#             supabase.table("user_missions").insert(new_entry).execute()
#             results.append({"mission_id": mission_id, "progress": progress, "completed": completed})
#             if completed:
#                 publish_event({
#                     "type": "MISSION_COMPLETED",
#                     "user_id": user_id,
#                     "mission_id": mission_id,
#                     "reward_points": reward
#                 })
#     return results

def get_user_missions(user_id):
    user_data = supabase.table("user_missions").select("*").eq("user_id", user_id).execute().data
    all_missions = supabase.table("mission").select("*").execute().data
    mission_lookup = {m['id']: m for m in all_missions}

    enriched = []
    for record in user_data:
        mission = mission_lookup.get(record['mission_id'])
        if mission:
            enriched.append({
                "mission_id": record['mission_id'],
                "name": mission['name'],
                "description": mission['description'],
                "goal": mission['goal'],
                "progress": record['progress'],
                "completed": record['completed'],
                "reward_points": mission['reward_points']
            })
    return enriched

from flask_cors import CORS

def enable_cors(app):
    """Enable CORS for the Flask app."""
    CORS(app, resources={r"/*": {"origins": "http://localhost:5173"}})
    
# import os
# from supabase import create_client
# from dotenv import load_dotenv

# load_dotenv()
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# def list_all_missions():
#     return supabase.table("missions").select("*").execute().data

# def update_mission_progress(user_id, event_type):
#     missions = supabase.table("missions").select("*").eq("event_type", event_type).execute().data
#     results = []
#     for mission in missions:
#         mission_id = mission['id']
#         goal = mission['goal']
#         reward = mission['reward_points']

#         res = supabase.table("user_missions").select("*")\
#             .eq("user_id", user_id).eq("mission_id", mission_id).execute().data

#         if res:
#             user_mission = res[0]
#             if user_mission['completed']:
#                 results.append({"mission_id": mission_id, "status": "already completed"})
#                 continue
#             progress = user_mission['progress'] + 1
#             completed = progress >= goal
#             supabase.table("user_missions").update({"progress": progress, "completed": completed})\
#                 .eq("id", user_mission['id']).execute()
#             results.append({"mission_id": mission_id, "progress": progress, "completed": completed})
#         else:
#             progress = 1
#             completed = progress >= goal
#             new_entry = {
#                 "user_id": user_id,
#                 "mission_id": mission_id,
#                 "progress": progress,
#                 "completed": completed
#             }
#             supabase.table("user_missions").insert(new_entry).execute()
#             results.append({"mission_id": mission_id, "progress": progress, "completed": completed})
#     return results

# def get_user_missions(user_id):
#     user_data = supabase.table("user_missions").select("*").eq("user_id", user_id).execute().data
#     all_missions = supabase.table("missions").select("*").execute().data
#     mission_lookup = {m['id']: m for m in all_missions}

#     enriched = []
#     for record in user_data:
#         mission = mission_lookup.get(record['mission_id'])
#         if mission:
#             enriched.append({
#                 "mission_id": record['mission_id'],
#                 "name": mission['name'],
#                 "description": mission['description'],
#                 "goal": mission['goal'],
#                 "progress": record['progress'],
#                 "completed": record['completed'],
#                 "reward_points": mission['reward_points']
#             })
#     return enriched



###############################
# import os
# import json
# import pika
# from supabase import create_client
# from dotenv import load_dotenv

# load_dotenv()
# SUPABASE_URL = os.getenv("SUPABASE_URL")
# SUPABASE_KEY = os.getenv("SUPABASE_KEY")
# RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

# supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# def publish_event(event: dict):
#     try:
#         connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST))
#         channel = connection.channel()
#         channel.exchange_declare(exchange="events.topic", exchange_type="topic", durable=True)
#         routing_key = "mission.completed"
#         channel.basic_publish(
#             exchange="events.topic",
#             routing_key=routing_key,
#             body=json.dumps(event),
#             properties=pika.BasicProperties(delivery_mode=2)
#         )
#         connection.close()
#         print(f"[✓] Published mission completion event: {event}")
#     except Exception as e:
#         print(f"[!] Failed to publish mission event: {e}")

# def list_all_missions():
#     return supabase.table("mission").select("*").execute().data

# def update_mission_progress(user_id, event_type):
#     missions = supabase.table("mission").select("*").eq("event_type", event_type).execute().data
#     results = []
#     for mission in missions:
#         mission_id = mission['id']
#         goal = mission['goal']
#         reward = mission['reward_points']

#         res = supabase.table("user_missions").select("*")            .eq("user_id", user_id).eq("mission_id", mission_id).execute().data

#         if res:
#             user_mission = res[0]
#             if user_mission['completed']:
#                 results.append({"mission_id": mission_id, "status": "already completed"})
#                 continue
#             progress = user_mission['progress'] + 1
#             completed = progress >= goal
#             supabase.table("user_missions").update({"progress": progress, "completed": completed})                .eq("id", user_mission['id']).execute()
#             results.append({"mission_id": mission_id, "progress": progress, "completed": completed})

#             if completed:
#                 publish_event({
#                     "type": "MISSION_COMPLETED",
#                     "user_id": user_id,
#                     "mission_id": mission_id,
#                     "reward_points": reward
#                 })
#         else:
#             progress = 1
#             completed = progress >= goal
#             new_entry = {
#                 "user_id": user_id,
#                 "mission_id": mission_id,
#                 "progress": progress,
#                 "completed": completed
#             }
#             supabase.table("user_missions").insert(new_entry).execute()
#             results.append({"mission_id": mission_id, "progress": progress, "completed": completed})
#             if completed:
#                 publish_event({
#                     "type": "MISSION_COMPLETED",
#                     "user_id": user_id,
#                     "mission_id": mission_id,
#                     "reward_points": reward
#                 })
#     return results

# def get_user_missions(user_id):
#     user_data = supabase.table("user_missions").select("*").eq("user_id", user_id).execute().data
#     all_missions = supabase.table("mission").select("*").execute().data
#     mission_lookup = {m['id']: m for m in all_missions}

#     enriched = []
#     for record in user_data:
#         mission = mission_lookup.get(record['mission_id'])
#         if mission:
#             enriched.append({
#                 "mission_id": record['mission_id'],
#                 "name": mission['name'],
#                 "description": mission['description'],
#                 "goal": mission['goal'],
#                 "progress": record['progress'],
#                 "completed": record['completed'],
#                 "reward_points": mission['reward_points']
#             })
#     return enriched