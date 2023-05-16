from flask import Flask, request
from flask_restful import Resource
from utils import createBuyTransaction, burnAndSendToBuyer, loadKeys, getAuxiliaryData, getPolicy, BLOCK_FROST_PROJECT_ID
from blockfrost import ApiUrls
from pycardano import Transaction as PyCaTransaction
from pycardano import *
import random # just to generate the nft uids

class Buy(Resource):
    def get(self):

        args = request.args

        if "buyer_address" not in args or "asset_name" not in args:
            return {'status': 'error', 'message':'missing buyer address or asset name not in parameters'}, 400
        
        buyer_address = args["buyer_address"] # hex format
        asset_name = args["asset_name"] # hex format

        tx_body = createBuyTransaction(buyer_address, asset_name)

        tx=PyCaTransaction(tx_body, TransactionWitnessSet())

        return {"tx_cbor":tx.to_cbor()}, 200


    def post(self):

        data=request.get_json(force=True)

        if "buyer_address" not in data or "asset_name" not in data or "witness" not in data or "tx_cbor" not in data:
            return {'status': 'error', 'message':'missing buyer address, asset name, tx cbor or witness parameter(s)'}, 400

        buyer_address=Address.from_primitive(bytes.fromhex(data["buyer_address"]))
        asset_name=''.join(data["asset_name"]) # i need to put a join because what comes in the request is an array ['<asset_name_part1>', '<asset_name_part2>'...]. Each element has a maximum of 64 chars and together form the asset id

        tx = PyCaTransaction.from_cbor(data["tx_cbor"])
        tx_body=tx.transaction_body

        # create the witness set with: user's signature witness and project's storage signature witness
        witnessSet = TransactionWitnessSet.from_cbor(data["witness"])

        tx.transaction_witness_set=witnessSet

        # submit transaction
        context = BlockFrostChainContext( project_id=BLOCK_FROST_PROJECT_ID, base_url=ApiUrls.preprod.value )
        
        tx_id = tx.transaction_body.hash().hex()
        
        try:
            context.submit_tx(tx.to_cbor())
        except:
            return{"status":"error", "message":"maybe you tried to submit many transactions at once."}, 500
        
        # after confirming submission, send nft to buyer and burn NFT
        burnAndSendToBuyer(data["buyer_address"], asset_name)

        return {"status":"ok", "tx_id":tx_id}, 200