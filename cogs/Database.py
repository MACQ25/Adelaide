from datetime import datetime as dt
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from discord.ext import commands
from cogs.SchedulingInteractions import Event

# Didn't use the following install, if problems arise because of the missing [srv] do it later
# python -m pip install "pymongo[srv]"

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tkn = open("./secrets/mongoAccount.tkn").readline().strip()
        self.client = MongoClient("mongodb+srv://{}@cluster0.x5r2p5q.mongodb.net/?appName=Cluster0".format(self.tkn), server_api=ServerApi('1'))


    async def ping(self):
        # Create a new client and connect to the server
        result = False
        # Send a ping to confirm a successful connection
        try:
            self.client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
            result = True
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


    async def save_assigned(self, gId, channel):
        try:
            db = self.client.get_database("scheduling")
            db.guilds.update_one(
                filter={'_id': gId },
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


    async def save_event(self, gId, event: Event):
        try:
            db = self.client.get_database("scheduling")
            db.guilds.update_one(
                filter={'_id': gId },
                update={
                    '$push': {
                        f'event_days.{event.summary}': {
                            '$each': [
                                {
                                    "date": date,
                                    "starts": event.starts,
                                    "duration": event.duration
                                }
                                for date in event.dates
                            ]
                        }
                     },
                    '$addToSet': {
                        f'event_owners.{event.owner}': event.summary,
                        'event_data': {
                            "name": event.summary,
                            "desc": event.description,
                            "location": event.location,
                            "color": event.color,
                            "frequency": event.frequency,
                            "active": True
                        },
                    }
                }
            )
        except Exception as e:
            print(e)
            raise Exception("Failed to create the event") from e


    async def get_by_user(self, gId, userId):
        try:
            db = self.client.get_database("scheduling")
            res = db.guilds.find_one(
                filter={
                    '_id': gId,
                    f'event_owners.{userId}': {'$exists': True}
                },
                projection={ f"event_owners.{userId}": 1 }
            )
            options = res.get('event_owners', {}).get(str(userId), []) if res else []
            return options
        except Exception as e:
            print(e)
            raise Exception("Failed to create the event") from e


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
                                "color": "$$event.color"
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