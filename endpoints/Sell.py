from flask import Flask, request
from flask_restful import Resource
from pycardano import Transaction as PyCaTransaction
from pycardano import *
from blockfrost import ApiUrls
import requests
import random # just to generate the nft uids
from utils import createSellTransaction, witnessSellWithPolicy, loadKeys, getInfoNftAuxiliaryData, getPolicy, getSellDetails, getExpirationBlock, BLOCK_FROST_PROJECT_ID

class Sell(Resource):
    def get(self):
        args = request.args

        if "address" not in args or "asset" not in args:
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

    def post(self):
        args=request.get_json(force=True)

        if "seller_address" not in args or "policy_id" not in args or "asset_name_hex" not in args or "price" not in args:
            return {'status': 'error', 'message':'missing seller address, policy id, asset name (hex) or price parameter'}, 400

        seller_address = args["seller_address"] # in hex format
        asset_name_hex = args["asset_name_hex"] # in hex format
        policy_id = args["policy_id"]
        price = args["price"] 

        tx_body, storage_wallet_name = createSellTransaction(seller_address, policy_id, asset_name_hex, price)

        tx=PyCaTransaction(tx_body, TransactionWitnessSet())

        return {"tx_cbor":tx.to_cbor(), "storage_wallet_name":storage_wallet_name}, 200

    def put(self):
        args=request.get_json(force=True)

        if "seller_address" not in args or "witness" not in args or "tx_cbor" not in args or "policy_id" not in args or "asset_name_hex" not in args or "price" not in args or "storage_wallet_name" not in args:
            return {'status': 'error', 'message':'missing seller address, witness, tx (in cbor format), policy id, asset name (hex), storage wallet name or price parameter(s)'}, 400

        seller_address=Address.from_primitive(bytes.fromhex(args["seller_address"])) # convert hex format to Address
        asset_name_hex=args["asset_name_hex"]
        asset_policy_id=args["policy_id"]
        price=args["price"]
        storage_wallet_name=args["storage_wallet_name"]

        tx = PyCaTransaction.from_cbor(args["tx_cbor"])
        tx_body=tx.transaction_body

        # get "_info" collection's policy
        policy=getPolicy("collection_info", getExpirationBlock("collection_info")) # getPolicy(<directory_name>, <expiration_slot>)
        
        
        # create the witness set with: user signature witness, policy signature witness and policy script
        witnessSet = TransactionWitnessSet.from_cbor(args["witness"])
        witnessSet.vkey_witnesses.append(witnessSellWithPolicy(tx_body.hash()))
        witnessSet.native_scripts = [policy]

        tx.transaction_witness_set=witnessSet

        # set the auxiliary data for the transaction
        auxiliary_data=getInfoNftAuxiliaryData(policy, asset_name_hex, asset_policy_id, price, str(seller_address), storage_wallet_name)
        tx.auxiliary_data=auxiliary_data

        # submit transaction
        context = BlockFrostChainContext( project_id=BLOCK_FROST_PROJECT_ID, base_url=ApiUrls.preprod.value )
        
        tx_id = tx.transaction_body.hash().hex()
        
        try:
            context.submit_tx(tx.to_cbor())
        except:
            return{"status":"error", "message":"maybe you tried to submit many transactions at once."}, 500

        
        return {"status":"ok", "tx_id":tx_id}, 200