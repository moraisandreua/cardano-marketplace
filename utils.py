import os
import sys
import pathlib
from pycardano import *
from blockfrost import ApiUrls
from pycardano import Transaction as PyCaTransaction
import random # just to generate the 
import requests

BLOCK_FROST_PROJECT_ID = "preprodeMB9jfka6qXsluxEhPLhKczRdaC5QKab" # since it is in preprod mode and this is the project_id used by Nami Wallet

def getExpirationBlock(dir, PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))):
    '''
        function to return the expiration block defined in setup
    '''
    if not os.path.exists(PROJECT_ROOT+"/"+dir):
        return 0

    f=open(PROJECT_ROOT + "/" + dir + "/expiration.block", "r")
    expiration_block=f.read()

    return int(expiration_block)


def createKeys(wallet_name, dir, PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))):
    '''
        function to generate the required files to create a wallet

        wallet_name->name given to the file inside the folder. Three files will be created with that name: 
            * <wallet_name>.skey -> signing key
            * <wallet_name>.vkey -> verification key
            * <wallet_name>.addr -> file with the address if the wallet
    '''
    path_skey = PROJECT_ROOT + "/" + dir + "/" + wallet_name + ".skey"
    path_vkey = PROJECT_ROOT + "/" + dir + "/" + wallet_name + ".vkey"

    if pathlib.Path(path_skey).exists() or pathlib.Path(path_vkey).exists():
        return False
    
    # generate the keys
    key_pair = PaymentKeyPair.generate()
    key_pair.signing_key.save(str(path_skey))
    key_pair.verification_key.save(str(path_vkey))
    
    skey = key_pair.signing_key
    vkey = key_pair.verification_key

    # generate the address
    NETWORK = Network.TESTNET
    address = str(Address(vkey.hash(), network=NETWORK))
    
    arr_path = PROJECT_ROOT + "/" + dir + "/" + wallet_name + ".addr"
    
    f = open(arr_path, "w")
    f.write(address)

    return True


def loadKeys(dir, filename, PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))):
    '''
        function to load already generated keys (verification and signing)
    '''
    root = PROJECT_ROOT + "/" + dir
    skey = PaymentSigningKey.load(root + "/" + filename + ".skey")
    vkey = PaymentVerificationKey.from_signing_key(skey)

    return skey, vkey


def createMintTransaction( buyer_hex_address, nft_uid=random.randint(0, 9999999999) ):
    # blockchain context
    NETWORK = Network.TESTNET
    chain_context = BlockFrostChainContext(
        project_id=BLOCK_FROST_PROJECT_ID,
        base_url=ApiUrls.preprod.value,
    )

    # ticket creator wallet keys
    my_nft_skey, my_nft_vkey = loadKeys("main_nft_wallet", "wallet")
    main_nft_address = Address(my_nft_vkey.hash(), network=NETWORK)

    user_address=Address.from_primitive(bytes.fromhex(buyer_hex_address)) # bytes.fromhex(buyer_hex_address); address needs to be converted to bech32 format (addr_test1ftre7sasjdn)

    # set policy
    expiration_slot=getExpirationBlock("collection_ticket")
    policy=getPolicy("collection_ticket", expiration_slot) # getPolicy(<directory_name>, <expiration_slot>)
    must_before_slot = InvalidHereAfter(expiration_slot)
    policy_id = policy.hash()

    # define the nft
    nft_random_id = nft_uid

    my_asset = Asset()
    nft_name="MY_NFT_"+str(nft_random_id)
    nft1 = AssetName(nft_name.encode("utf8"))
    my_asset[nft1] = 1

    my_nft = MultiAsset()
    my_nft[policy_id] = my_asset
    native_scripts = [policy]

    auxiliary_data = getAuxiliaryData(policy, nft_random_id)

    # build the transaction
    builder = TransactionBuilder(chain_context)

    builder.add_input_address(user_address)
    builder.ttl = must_before_slot.after
    builder.mint = my_nft
    builder.native_scripts = native_scripts
    builder.auxiliary_data = auxiliary_data

    min_val = min_lovelace(
        chain_context, output=TransactionOutput(user_address, Value(0, my_nft))
    )

    # set nft price
    price=30*1000000

    # set one of the outputs (nft mint)
    builder.add_output(TransactionOutput(user_address, Value(min_val, my_nft)))

    # calculate the fees
    fee=builder._estimate_fee()

    # subtract the fee to the amount of money that the ticket creator will receive
    builder.add_output(TransactionOutput(main_nft_address, Value(price-min_val-fee)))

    tx_body = builder.build(change_address=user_address)

    return tx_body, nft_uid


def witnessWithPolicy(data):
    '''
        This function signs a mint transaction with the policy's signing key.
        data->transaction in cbor format signed and returned by user
    '''
    collection_ticket_skey, collection_ticket_vkey = loadKeys("collection_ticket", "policy")
    
    signature = collection_ticket_skey.sign(data)

    return VerificationKeyWitness(collection_ticket_skey.to_verification_key(), signature)


def witnessSellWithPolicy(data):
    '''
        When selling, the service needs to mint a "_info" NFT.
        This minting needs to be signed with the policy's signing key.
        data->transaction in cbor format signed and returned by user.
    '''
    collection_ticket_skey, collection_ticket_vkey = loadKeys("collection_info", "policy")
    
    signature = collection_ticket_skey.sign(data)

    return VerificationKeyWitness(collection_ticket_skey.to_verification_key(), signature)


def split_str_by_num(string, num):
    '''
        function used for string spliting
        string->text to be splitted
        num->number of chars to jump
    '''
    return [string[i:i+num] for i in range(0, len(string), num)]


def getAuxiliaryData(policy, nft_uid):
    '''
        generates the needed auxiliary data for the minting the launchpad token
        policy->nft policy generated by setup.py
        nft_uid->random integer; sufix of nft name

        Note: this is a static example
    '''

    policy_id = policy.hash()
    nft_name="MY_NFT_"+str(nft_uid)
    metadata = {
        721: {
            policy_id.payload.hex(): {
                nft_name: {
                    "description": "This is my nth NFT thanks to PyCardano",
                    "name": "PyCardano NFT example token "+str(nft_uid),
                    "id": 1,
                    "image": "ipfs://QmRhTTbUrPYEw3mJGGhQqQST9k86v1DPBiTTWJGKDJsVFw",
                },
            }
        }
    }
    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))

    return auxiliary_data


def getAuxiliaryDataForBurning(policy, asset_name_hex):
    '''
        generates the needed auxiliary data for the burning

        Note: this is a static example
    '''

    policy_id = policy.hash()
    nft_name=bytes.fromhex(asset_name_hex).decode("utf-8")
    metadata = {
        721: {
            policy_id.payload.hex(): {
                nft_name: {
                    "description": "This is my nth NFT thanks to PyCardano",
                    "name": "PyCardano NFT example token ",
                    "id": 1,
                    "image": "ipfs://QmRhTTbUrPYEw3mJGGhQqQST9k86v1DPBiTTWJGKDJsVFw",
                },
            }
        }
    }
    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))

    return auxiliary_data


def getInfoNftAuxiliaryData(info_nft_policy, nft_selling_asset_name, nft_selling_policy_id, nft_selling_price, seller_address, storage_wallet_name):
    '''
        generates the needed auxiliary data for the minting
        this NFT is minted to the project storage wallet

        Note: this is for the "_info" NFT
    '''

    policy_id = info_nft_policy.hash()
    nft_name=bytes.fromhex(nft_selling_asset_name).decode('utf-8')

    metadata = {
        721: {
            policy_id.payload.hex(): {
                nft_name: {
                    "asset_name": split_str_by_num(nft_selling_asset_name, 64),
                    "policy_id": split_str_by_num(nft_selling_policy_id, 64),
                    "price": nft_selling_price,
                    "seller_address":split_str_by_num(seller_address, 64),
                    "storage_wallet_name":storage_wallet_name,
                    "image": "ipfs://QmRhTTbUrPYEw3mJGGhQqQST9k86v1DPBiTTWJGKDJsVFw",
                },
            }
        }
    }

    auxiliary_data = AuxiliaryData(AlonzoMetadata(metadata=Metadata(metadata)))

    return auxiliary_data


def getPolicy(dir, expiration_block, PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))):
    '''
        this function loads the policy for a path
        dir->local directory
        expiration_block->integer determining the unix time in which the policy expires
        PROJECT_ROOT->root directory of the project
    '''
    skey, vkey = loadKeys(dir, "policy", PROJECT_ROOT)

    collection_ticket_policy = ScriptPubkey(vkey.hash())
    must_before_slot = InvalidHereAfter(expiration_block)
    policy = ScriptAll([collection_ticket_policy, must_before_slot])

    return policy


def createSellWallets():
    '''
        function used to create verification and signing keys for the wallet where the NFT being sold is going to be stored
    '''
    randomNumber = random.randint(0, 99999)
    wallet_name="storage_"+str(randomNumber)
    walletCreation = createKeys(wallet_name, "project_storage")

    while not walletCreation:
        randomNumber = random.randint(0, 99999)
        wallet_name="storage_"+str(randomNumber)
        walletCreation = createKeys(wallet_name, "project_storage")

    return wallet_name


def createSellTransaction( seller_address_hex, asset_policy_id, asset_name_hex, price):
    '''
        function used to generate the transaction the user needs to sign
        seller_address_hex->address from the seller, in hex format
        asset_policy_id->policy id form the NFT being sold
        asset_name_hex->name from the NFT being sold, in hex format

        in this step the "_info" nft is minted with the previous information in its metadata
    '''
    NETWORK = Network.TESTNET
    chain_context = BlockFrostChainContext(
        project_id=BLOCK_FROST_PROJECT_ID,
        base_url=ApiUrls.preprod.value,
    )

    seller_address=Address.from_primitive(bytes.fromhex(seller_address_hex))

    # load keys for project storage wallet
    project_storage_wallet_name = createSellWallets()
    project_storage_skey, project_storage_vkey = loadKeys("project_storage", project_storage_wallet_name)
    project_storage_address = Address(project_storage_vkey.hash(), network=NETWORK)

    # load collection "_info" keys
    expiration_slot=getExpirationBlock("collection_info")
    policy=getPolicy("collection_info", expiration_slot) # getPolicy(<directory_name>, <expiration_slot>)
    must_before_slot = InvalidHereAfter(expiration_slot)
    policy_id = policy.hash()

    auxiliary_data = getInfoNftAuxiliaryData(policy, asset_name_hex, asset_policy_id, price, str(seller_address), project_storage_wallet_name)

    assets_to_storage = MultiAsset() # container with all the assets (the asset being sold and the _info asset)
    
    # define the nft to be sold
    selling_asset = Asset()
    selling_asset_name=bytes.fromhex(asset_name_hex).decode("utf-8")
    nft1 = AssetName(bytes.fromhex(asset_name_hex))
    selling_asset[nft1] = 1

    asset_policy_id=hash.ScriptHash(bytes.fromhex(asset_policy_id))
    assets_to_storage[asset_policy_id] = selling_asset

    # define the nft to be minted
    info_asset = Asset()
    info_nft_name=bytes.fromhex(asset_name_hex).decode("utf-8")
    nft1 = AssetName(bytes.fromhex(asset_name_hex))
    info_asset[nft1] = 1

    info_nft = MultiAsset()
    info_nft[policy_id] = info_asset
    assets_to_storage[policy_id] = info_asset
    native_scripts = [policy]

    # build the transaction
    builder = TransactionBuilder(chain_context)

    builder.add_input_address(seller_address)
    builder.ttl = must_before_slot.after
    builder.mint = info_nft
    builder.native_scripts = native_scripts
    builder.auxiliary_data = auxiliary_data

    min_val = min_lovelace(
        chain_context, output=TransactionOutput(project_storage_address, Value(0, assets_to_storage))
    )

    # set output to nft project storage (the wallet that keeps the nfts being sold)
    builder.add_output(TransactionOutput(project_storage_address, Value(min_val + 3000000, assets_to_storage)))

    tx_body = builder.build(change_address=seller_address)

    return tx_body, project_storage_wallet_name


def getSellDetails(policy_id, asset_name):
    '''
        return the metadata from an asset. It's used to get the metadata from "_info" nft and return the
        policy id from the original NFT, the price set by the seller, seller address and the name of the 
        wallet in which the original NFT is being stored

        policy_id->policy id from the "_info" collection
        asset_name->asset name from the NFT being sold (as well as the corresponding "_info" NFT)
    '''
    policy_id=policy_id.payload.hex()

    print(str(policy_id)+asset_name)

    r = requests.get(
        url="https://cardano-preprod.blockfrost.io/api/v0/assets/"+str(policy_id)+asset_name,
        headers={"project_id":BLOCK_FROST_PROJECT_ID}
    )
    
    obj=r.json()

    if "error" in obj:
        return None

    policy_id = ''.join(obj["onchain_metadata"]["policy_id"])
    price = obj["onchain_metadata"]["price"]
    seller_address = ''.join(obj["onchain_metadata"]["seller_address"])
    storage_wallet_name = obj["onchain_metadata"]["storage_wallet_name"]

    return {"policy_id":policy_id, "price":price, "seller_address":seller_address, "storage_wallet_name":storage_wallet_name}


def createBuyTransaction(buyer_address, asset_name):
    """
        buyer_address->address from the buyer
        asset_name->name of the asset being bought

        both buyer_address and asset_name are in hex format
    """
    NETWORK = Network.TESTNET
    chain_context = BlockFrostChainContext(
        project_id=BLOCK_FROST_PROJECT_ID,
        base_url=ApiUrls.preprod.value,
    )
    
    buyer_address_decoded=Address.from_primitive(bytes.fromhex(buyer_address))

    # load collection "_info" keys
    expiration_slot=getExpirationBlock("collection_info")
    policy=getPolicy("collection_info", expiration_slot) # getPolicy(<directory_name>, <expiration_slot>)
    policy_id = policy.hash()

    # selling details (metadata from "_info" nft)
    selling_details = getSellDetails(policy_id, asset_name)
    
    # seller wallet
    seller_address=Address.from_primitive(selling_details["seller_address"])

    # buy price
    buy_price=int(float(selling_details["price"]) * 1000000)

    # build the transaction
    builder = TransactionBuilder(chain_context)

    builder.add_input_address(buyer_address_decoded)
    
    builder.add_output(TransactionOutput(seller_address, Value(buy_price))) # output for the ADA returning to seller 

    tx_body = builder.build(change_address=buyer_address_decoded)

    return tx_body


def deleteStorageAfterPurchase(storage_wallet_name):
    '''
        this function will delete the files of the generated wallet upon the sell of a NFT

        this is the third phase
    '''
    pass


def burnAndSendToBuyer(buyer_address_hex, asset_name_hex):
    """
        both buyer_address_hex and asset_name are in hex format

        * this function is the second phase of buying an NFT
        * after the buyer sends the required amount of ADA, "_info" NFT is burned and the purchased NFT is sent

    """
    NETWORK = Network.TESTNET
    chain_context = BlockFrostChainContext(
        project_id=BLOCK_FROST_PROJECT_ID,
        base_url=ApiUrls.preprod.value,
    )

    buyer_address=Address.from_primitive(bytes.fromhex(buyer_address_hex))

    # load collection "_info" keys
    expiration_slot=getExpirationBlock("collection_info")
    policy_skey, policy_vkey = loadKeys("collection_info", "policy")
    policy=getPolicy("collection_info", expiration_slot) # getPolicy(<directory_name>, <expiration_slot>)
    must_before_slot = InvalidHereAfter(expiration_slot)
    policy_id = policy.hash() # policy from "_info" nfts

    # get selling details
    selling_details = getSellDetails(policy_id, asset_name_hex)
    
    # load keys for project storage wallet
    project_storage_wallet_name = selling_details["storage_wallet_name"]
    project_storage_skey, project_storage_vkey = loadKeys("project_storage", project_storage_wallet_name)
    project_storage_address = Address(project_storage_vkey.hash(), network=NETWORK)

    # define the nft to be bought
    assets_to_buyer = MultiAsset() # container with the NFT being bought
    buying_asset = Asset()
    buying_asset_name=bytes.fromhex(asset_name_hex).decode("utf-8")
    nft1 = AssetName(bytes.fromhex(asset_name_hex))
    buying_asset[nft1] = 1

    asset_policy_id=hash.ScriptHash(bytes.fromhex(selling_details["policy_id"]))
    assets_to_buyer[asset_policy_id] = buying_asset

    # define the nft being burned; needs to be defined two times: 
    # one of them, with negative value to burn
    # the other with null (0) value to serve as output
    info_asset_output = Asset()
    info_asset_burn = Asset()

    info_nft_name=bytes.fromhex(asset_name_hex).decode("utf-8")
    nft1 = AssetName(bytes.fromhex(asset_name_hex))
    
    info_asset_output[nft1] = 0
    info_asset_burn[nft1] = -1

    info_nft_output = MultiAsset()
    info_nft_burn = MultiAsset()

    info_nft_output[policy_id] = info_asset_output
    info_nft_burn[policy_id] = info_asset_burn

    native_scripts = [policy]

    # auxiliary data for burning
    auxiliary_data = getAuxiliaryDataForBurning(policy, asset_name_hex)

    # build the transaction
    builder = TransactionBuilder(chain_context)

    builder.add_input_address(project_storage_address)
    builder.ttl = must_before_slot.after
    builder.mint = info_nft_burn
    builder.native_scripts = native_scripts
    builder.auxiliary_data = auxiliary_data

    min_val_puchase = min_lovelace(
        chain_context, output=TransactionOutput(buyer_address, Value(0, assets_to_buyer))
    )

    min_val_burn = min_lovelace(
        chain_context, output=TransactionOutput(project_storage_address, Value(0, info_nft_output))
    )
    
    # add outputs to simulate the full transaction
    output_for_burning=TransactionOutput(project_storage_address, Value(min_val_burn, info_nft_output))
    builder.add_output(output_for_burning)

    output_for_buyer=TransactionOutput(buyer_address, Value(min_val_puchase, assets_to_buyer))
    builder.add_output(output_for_buyer)
    
    # sign tx
    signed_tx = builder.build_and_sign([project_storage_skey, policy_skey], change_address=project_storage_address)

    # submit tx
    chain_context.submit_tx(signed_tx.to_cbor())
