#!/bin/bash
echo "Restoring data..."
mongorestore --uri="mongodb://$MONGO_USER:$MONGO_PASS@localhost:27017/" --drop /dump
echo "Done!"