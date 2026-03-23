from datetime import datetime as dt
from pymongo import MongoClient
from pymongo.server_api import ServerApi
from discord.ext import commands

# Didn't use the following install, if problems arise because of the missing [srv] do it later
# python -m pip install "pymongo[srv]"

class Database(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.tkn = open("./secrets/mongoAccount.tkn").readline().strip()

    def client_init(self):
        return MongoClient("mongodb+srv://{}@cluster0.x5r2p5q.mongodb.net/?appName=Cluster0".format(self.tkn), server_api=ServerApi('1'))

    async def ping(self):
        # Create a new client and connect to the server
        client = self.client_init()
        result = False
        # Send a ping to confirm a successful connection
        try:
            client.admin.command('ping')
            print("Pinged your deployment. You successfully connected to MongoDB!")
            result = True
        except Exception as e:
            print(e)
        finally:
            client.close()
            return result

    async def check_guilds(self, guilds: list):
        client = self.client_init()
        now = dt.now()

        try:
            db = client.get_database("scheduling")

            for g in guilds:
                db.guilds.update_one(
                    filter={'_id': g.id},
                    update={
                        '$setOnInsert': {
                            'insertion_date': now,
                        },
                        '$set': {
                            '_id': g.id,
                            'name': g.name,
                            'assigned_channel': 'n/a',
                            'last_update_date': now,
                        },
                    },
                    upsert=True
                )

        except Exception as e:
            print(e)
        finally:
            client.close()

    async def save_assigned(self, gId, channel):
        client = self.client_init()
        now = dt.now()

        try:
            db = client.get_database("scheduling")
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
        finally:
            client.close()

async def setup(bot):
    await bot.add_cog(Database(bot))