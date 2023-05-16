from flask import Flask, request
from flask_restful import Resource
from pycardano import Address
from utils import BLOCK_FROST_PROJECT_ID
import requests

class Wallet(Resource):
    def get(self):
        args = request.args

        if "address" not in args:
            return {'status': 'error', 'message':'missing address parameter'}, 400

        user_address=Address.from_primitive(bytes.fromhex(args["address"]))

        r = requests.get(
            url="https://cardano-preprod.blockfrost.io/api/v0/addresses/"+str(user_address),
            headers={"project_id":BLOCK_FROST_PROJECT_ID}
        )
        obj=r.json()

        if "error" in obj:
            return {"status":"error", "message":obj["message"]}, obj["status_code"]

        return {"status":"ok", "assets":obj["amount"]}