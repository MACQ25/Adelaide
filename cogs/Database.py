from datetime import datetime as dt
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from discord.ext import commands
from objects.Event import Event

# Didn't use the following install, if problems arise because of the missing [srv] do it later
# python -m pip install "pymongo[srv]"

class Database(commands.Cog):
    def __init__(self, bot):

        self.bot = bot
        self.tkn = open("./secrets/mongoAccount.tkn").readline().strip()
        self.client = MongoClient("mongodb+srv://{}@cluster0.x5r2p5q.mongodb.net/?appName=Cluster0".format(self.tkn), server_api=ServerApi('1'))


    async def ping(self):
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
        except Exception as e:
            print(e)


    async def check_guilds(self, guilds: list):
        now = dt.now()

        try:
            db = self.client.get_database("scheduling")

            for g in guilds:
                db.guilds.update_one(
                    filter={'_id': g.id},
                    update={
                        '$setOnInsert': {
                            'insertion_date': now,
                            '_id': g.id,
                            'name': g.name,
                            'assigned_channel': 'n/a',
                            'last_update_date': now,
                        }
                    },
                    upsert=True
                )

        except Exception as e:
            print(e)


    async def save_assigned(self, g_id, channel):
        try:
            db = self.client.get_database("scheduling")
            db.guilds.update_one(
                filter={'_id': g_id},
                update={
                    '$set': {
                        'assigned_channel': {
                            'channel_id': channel.id,
                            'channel_name': channel.name
                        }
                    }
                }
            )
        except Exception as e:
            print(e)
            raise Exception("Failed to update assigned channel") from e


    async def save_event(self, g_id, event: Event):
        try:
            db = self.client.get_database("scheduling")

            db.guilds.update_one(
                filter={'_id': g_id, 'event_data.name': {'$ne': event.summary}},
                update={
                    '$push': {
                        'event_data': {
                            "name": event.summary,
                            "desc": event.description,
                            "channel": {
                                "section_id": event.section if event.section else None,
                                "text_id": event.text_channel if event.text_channel else None,
                                "vc_id": event.channel.id if event.channel else event.voice_channel,
                                "event_owns_it": event.created_for_event
                            } if event.channel or event.check_adv_present() else {},
                            "color": event.color,
                            "frequency": event.frequency,
                            "active": True,
                            "role_id": event.role
                        }
                    }
                }
            )

            # 2. Add dates and owner only if not already present
            new_dates = [
                {
                    "date": date,
                    "starts": dt.strptime(date, "%Y-%m-%d %H:%M:%S").hour,
                    "duration": event.duration,
                    "internal_id": event.int_evt[ind] if len(event.int_evt) > ind else None
                }
                for ind, date in enumerate(event.dates)
            ]

            existing = db.guilds.find_one(
                {'_id': g_id},
                {f'event_days.{event.summary}': 1}
            )

            existing_dates = set()
            if existing:
                days = existing.get('event_days', {}).get(event.summary, [])
                existing_dates = {d['date'] for d in days}

            filtered_dates = [d for d in new_dates if d['date'] not in existing_dates]

            if filtered_dates:
                db.guilds.update_one(
                    filter={'_id': g_id},
                    update={
                        '$push': {
                            f'event_days.{event.summary}': {'$each': filtered_dates}
                        },
                        '$addToSet': {
                            f'event_owners.{event.owner}': event.summary
                        }
                    }
                )

            """
            db.guilds.update_one(
                filter={'_id': g_id},
                update={
                    '$push': {
                        f'event_days.{event.summary}': {
                            '$each': [
                                {
                                    "date": date,
                                    "starts": dt.strptime(date, "%Y-%m-%d %H:%M:%S").hour,
                                    "duration": event.duration,
                                    "internal_id": event.int_evt[ind] if len(event.int_evt) > ind else None
                                }
                                for ind, date in enumerate(event.dates)
                            ]
                        }
                     },
                    '$addToSet': {
                        f'event_owners.{event.owner}': event.summary,
                        'event_data': {
                            "name": event.summary,
                            "desc": event.description,
                            "channel": {
                                "section_id": event.section if event.section else None,
                                "text_id":  event.text_channel if event.text_channel else None,
                                "vc_id": event.channel.id if event.channel else event.voice_channel,
                                "event_owns_it": event.created_for_event
                            } if event.channel or event.check_adv_present() else {},
                            "color": event.color,
                            "frequency": event.frequency,
                            "active": True,
                            "role_id": event.role
                        },
                    }
                }
            )
            """
        except Exception as e:
            print(e)
            raise Exception("Failed to create the event") from e


    async def quick_create(self, g_id, user_id, event_name, dates, starts_at, duration):
        try:
            db = self.client.get_database("scheduling")

            result = db.guilds.update_one(
                {
                    "_id": g_id,
                    f"event_owners.{user_id}": event_name,
                },
                update={
                    '$push': {
                        f'event_days.{event_name}': {
                            '$each': [
                                {
                                    "date": d,
                                    "starts": starts_at,
                                    "duration": duration
                                }
                                for d in dates
                            ]
                        }
                    }
                }
            )

            if result.matched_count == 0:
                print("Operation denied: user does not own this event.")
                return False

            return True

        except Exception as e:
            print(e)


    async def check_if_exists(self, g_id, val):
        try:
            db = self.client.get_database("scheduling")
            existing = db.guilds.find_one(
                {'_id': g_id},
                {f'event_days.{val}': 1}
            )
            return existing
        except Exception as e:
            print(e)
            raise Exception("Failed to create the event") from e


    async def get_by_user(self, g_id, user_id):
        try:
            db = self.client.get_database("scheduling")
            res = db.guilds.find_one(
                filter={
                    '_id': g_id,
                    f'event_owners.{user_id}': {'$exists': True}
                },
                projection={ f"event_owners.{user_id}": 1}
            )
            options = res.get('event_owners', {}).get(str(user_id), []) if res else []
            return options
        except Exception as e:
            print(e)
            raise Exception("Failed to create the event") from e


    async def get_by_class(self, g_id, event_name):
        try:
            db = self.client.get_database("scheduling")
            res = db.guilds.find_one(
                filter={
                    '_id': g_id,
                    f'event_days.{event_name}': {'$exists': True}
                },
                projection={ f"event_days.{event_name}": 1 }
            )
            options = res.get('event_days', {}).get(str(event_name), []) if res else []

            options = [ dt.strptime(val.get('date'), "%Y-%m-%d %H:%M:%S").date().strftime("%B %d of %Y")  for val in options ]

            return options
        except Exception as e:
            print(e)
            raise Exception("Failed to create the event") from e


    async def get_internal(self, g_id, user_id, event_name):
        try:
            db = self.client.get_database("scheduling")

            result = db.guilds.find_one(
                filter={
                    '_id': g_id,
                    f'event_owners.{user_id}': {'$exists': True}
                },
                projection={
                    "event_data": {
                        "$arrayElemAt": [
                            {
                                "$map": {
                                    "input": {
                                        "$filter": {
                                            "input": "$event_data",
                                            "as": "event",
                                            "cond": {"$eq": ["$$event.name", event_name]}
                                        }
                                    },
                                    "as": "event",
                                    "in": {
                                        "event_owns_it": "$$event.channel.event_owns_it",
                                        "section_id": "$$event.channel.section_id",
                                        "text_id": "$$event.channel.text_id",
                                        "vc_id": "$$event.channel.vc_id",
                                        "role_id": "$$event.role_id"
                                    }
                                }
                            }, 0
                        ]
                    },
                    "event_days": {
                        "$map": {
                            "input": {
                                "$getField": {
                                    "field": event_name,
                                    "input": "$event_days"
                                }
                            },
                            "as": "dates",
                            "in": "$$dates.internal_id"
                        }
                    }
                }
            )

            return result
        except Exception as e:
            print(e)


    async def delete_set(self, g_id, user_id, event_name, list_of_indexes):
        try:
            db = self.client.get_database("scheduling")

            # Step 1: Unset all target indexes in one update
            unset_dict = {f"event_days.{event_name}.{i}": "" for i in list_of_indexes}
            result = db.guilds.update_one(
                {"_id": g_id, f"event_owners.{user_id}": event_name},
                {"$unset": unset_dict}
            )

            if result.matched_count == 0:
                print("Operation denied: user does not own this event.")
                return False

            # Step 2: Pull all nulls out
            result = db.guilds.update_one({"_id": g_id}, {"$pull": {f"event_days.{event_name}": None}})

            return True
        except Exception as e:
            print(e)


    async def delete_by_class(self, g_id, user_id, event_name):
        try:
            db = self.client.get_database("scheduling")

            result = db.guilds.update_one(
                {"_id": g_id, f"event_owners.{user_id}": event_name},
                      update={"$set": { f"event_days.{event_name}" : [] }}
            )

            if result.matched_count == 0:
                print("Operation denied: user does not own this event.")
                return False
            return True

        except Exception as e:
            print(e)


    async def delete_full(self, g_id, user_id, event_name):
        try:
            db = self.client.get_database("scheduling")
            result = db.guilds.update_one(
                {"_id": g_id, f"event_owners.{user_id}": event_name},
                update= {
                    "$unset":
                        {
                          f"event_days.{event_name}": ""
                        },
                    "$pull": {
                        "event_data": {"name": event_name},
                        f"event_owners.{user_id}": event_name,
                    }
                }
            )

            if result.matched_count == 0:
                print("Operation denied: user does not own this event.")
                return False
            return True

        except Exception as e:
            print(e)


    async def update_to_inactive(self, g_id, user_id, event_name, val:bool):
        try:
            db = self.client.get_database("scheduling")

            result = db.guilds.update_one(
                {"_id": g_id, f"event_owners.{user_id}": event_name, "event_data.name": event_name},
                update={"$set": { f"event_data.$.active": val}}
            )

            if result.matched_count == 0:
                print("Operation denied: user does not own this event.")
                return False

            return True

        except Exception as e:
            print(e)


    async def get_events(self, gId):
        try:
            db = self.client.get_database("scheduling")
            res = db.guilds.aggregate([
                {"$match": {"_id": gId}},
                {"$project": {
                    "assigned_channel": 1,
                    "event_data": {
                        "$map": {
                            "input": {
                                "$filter": {
                                    "input": "$event_data",
                                    "as": "event",
                                    "cond": {"$eq": ["$$event.active", True]}
                                }
                            },
                            "as": "event",
                            "in": {
                                "name": "$$event.name",
                                "color": "$$event.color",
                                "role_id": "$$event.role_id"
                            }
                        }
                    },
                    "event_days": 1
                }}
            ]).next()
            return res
        except Exception as e:
            print(e)
            raise Exception("Failed to acquire events")


    async def cog_unload(self):
        self.client.close()

async def setup(bot):
    await bot.add_cog(Database(bot))