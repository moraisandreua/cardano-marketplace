from flask import Flask, request
from flask_restful import Resource
from utils import createMintTransaction, witnessWithPolicy, loadKeys, getAuxiliaryData, getPolicy, BLOCK_FROST_PROJECT_ID, getExpirationBlock
from blockfrost import ApiUrls
from pycardano import Transaction as PyCaTransaction
from pycardano import *
import random # just to generate the nft uids

class Mint(Resource):
    def get(self):

        args = request.args

        if "buyer_address" not in args:
            return {'status': 'error', 'message':'missing buyer address parameter'}, 400

        buyer_address = args["buyer_address"] # in hex format

        tx_body, nft_uid=createMintTransaction(buyer_address)
        
        tx=PyCaTransaction(tx_body, TransactionWitnessSet())

        return {"tx_cbor":tx.to_cbor(), "nft_uid":nft_uid}, 200


    def post(self):

        data=request.get_json(force=True)

        if "buyer_address" not in data or "nft_uid" not in data or "witness" not in data or "tx_cbor" not in data:
            return {'status': 'error', 'message':'missing buyer address, nft uid or witness parameter(s)'}, 400

        """ tx, nft_uid = createMintTransaction(data["buyer_address"], data["nft_uid"]) """

        tx = PyCaTransaction.from_cbor(data["tx_cbor"])
        tx_body=tx.transaction_body

        # get collection's policy
        policy=getPolicy("collection_ticket", getExpirationBlock("collection_ticket")) # getPolicy(<directory_name>, <expiration_slot>)

        # create the witness set with: user signature witness, policy signature witness and policy script
        witnessSet = TransactionWitnessSet.from_cbor(data["witness"])
        witnessSet.vkey_witnesses.append(witnessWithPolicy(tx_body.hash()))
        witnessSet.native_scripts = [policy]

        tx.transaction_witness_set=witnessSet

        # set the auxiliary data for the transaction
        auxiliary_data=getAuxiliaryData(policy, data["nft_uid"])
        tx.auxiliary_data=auxiliary_data

        # submit transaction
        context = BlockFrostChainContext( project_id=BLOCK_FROST_PROJECT_ID, base_url=ApiUrls.preprod.value )
        
        tx_id = tx.transaction_body.hash().hex()
        
        try:
            context.submit_tx(tx.to_cbor())
        except:
            return{"status":"error", "message":"maybe you tried to submit many transactions at once."}, 500

        
        return {"status":"ok", "tx_id":tx_id}, 200