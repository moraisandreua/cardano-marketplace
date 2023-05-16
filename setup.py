import os
import re
from pycardano import *
from utils import getExpirationBlock
import time

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

def createKeys(dir, name):
    '''
        function used to create and return the key files
        dir->local directory
        name->file name. the result will be <name>.skey and <name>.vkey
    '''
    path_skey=PROJECT_ROOT + "/" + dir + "/" + name + ".skey"
    path_vkey=PROJECT_ROOT + "/" + dir + "/" + name + ".vkey"
    
    key_pair = PaymentKeyPair.generate()
    key_pair.signing_key.save(str(path_skey))
    key_pair.verification_key.save(str(path_vkey))

    return key_pair.signing_key, key_pair.verification_key


def generatePolicyFiles(dir):
    '''
        function used to create the requested policy
        dir->directory name that will store the policy files
    '''
    path_policyid=PROJECT_ROOT + "/" + dir + "/" + "policy.id"

    # get the current time
    current_unix_time = int(time.time())
    oneYearInUnix=31536000
    expiration_block=current_unix_time+oneYearInUnix

    # save unix time
    f=open(PROJECT_ROOT + "/" + dir + "/" + "expiration.block", "w")
    f.write(str(expiration_block))

    # create keys
    skey, vkey=createKeys(dir, "policy")

    # generate policy id
    collection_ticket_policy = ScriptPubkey(vkey.hash())
    must_before_slot = InvalidHereAfter(expiration_block)
    policy = ScriptAll([collection_ticket_policy, must_before_slot])
    policy_id=policy.hash().payload.hex()

    # save policy id
    f=open(path_policyid, "w")
    f.write(policy_id)  


def generateNormalWallet(dir):
    skey, vkey = createKeys("main_nft_wallet", "wallet")
    address = Address(vkey.hash(), network=Network.TESTNET)

    f=open(PROJECT_ROOT + "/" + dir + "/wallet.addr", "w")
    f.write(str(address))


def getConstantsPolicyDefinition(variable_name, constants_js_content):
    '''
        function to return the saved policy id
    '''

    # get the start and finish position
    policy_span = re.search(r'('+variable_name+')(.*)(=)(.[^"]*)(")(.[^"]*)(")', constants_js_content).span()

    # get the substring
    policy_text = constants_js_content[policy_span[0]:policy_span[1]]

    # get the deprecated policy id
    policy_line = re.split(r'('+variable_name+')(.*)(=)(.[^"]*)(")(.[^"]*)(")', policy_text)
    policy_id = policy_line[6]

    return policy_id


def getNewPolicies():
    '''
        function to return the policy id from the current collections
    '''

    dirs=["collection_info", "collection_ticket"]
    policies=[]

    for dir in dirs:
        path=PROJECT_ROOT+"/"+dir+"/policy.id"
        if os.path.exists(path):
            f=open(path, "r")
            policy=f.read()
            policies.append(policy)
        else:
            policies.append("")
    
    return policies[0], policies[1]


'''
    start by checking if the folders (used to store the policy) already exist
    if not, create the folders andr/or its keys
'''
required_dirs=["collection_info", "collection_ticket"]
for dir in required_dirs:
    # check if directory already exists
    if os.path.exists(PROJECT_ROOT+"/"+dir):
        if not os.path.exists(PROJECT_ROOT + "/" + dir + "/" + "policy.id"):
            generatePolicyFiles(dir)
            print("["+dir+"] The directory already existed and the files were now generated")
    else:
        os.mkdir(PROJECT_ROOT + "/" + dir)
        generatePolicyFiles(dir)
        print("["+dir+"] Neither directories nor the files existed. They exist now.")

'''
    then, check if the folder used to store the earning from minting already exist
    if not, create the folders andr/or its keys
'''
if os.path.exists(PROJECT_ROOT+"/main_nft_wallet"):
    if not os.path.exists(PROJECT_ROOT + "/main_nft_wallet/" + "wallet.addr"):
        generateNormalWallet("main_nft_wallet")
        print("[main_nft_wallet] The directory already existed and the files were now generated")
else:
    os.mkdir(PROJECT_ROOT + "/main_nft_wallet")
    generateNormalWallet("main_nft_wallet")
    print("[main_nft_wallet] Neither directories nor the files existed. They exist now.")


'''
    then, check/create the project_storage directory where it will be stored all the temporary wallets
'''
if not os.path.exists(PROJECT_ROOT+"/project_storage"):
    os.mkdir(PROJECT_ROOT + "/project_storage")
    print("[project_storage] The directory didn't exist. It exists now.")

'''
    get constants.js content as well as the defined policies
'''
f_contants = open(PROJECT_ROOT+"/website/assets/js/constants.js", "r")
constants_js_content = f_contants.read()

info_nft_policy_id = getConstantsPolicyDefinition("INFO_NFT_POLICY", constants_js_content)
main_nft_policy_id = getConstantsPolicyDefinition("MAIN_NFT_POLICY", constants_js_content)

'''
    replace the previous policies with the new ones
'''
new_info_nft_policy_id, new_main_nft_policy_id = getNewPolicies()

new_constants_js_content = constants_js_content.replace(info_nft_policy_id, new_info_nft_policy_id).replace(main_nft_policy_id, new_main_nft_policy_id)

'''
    update constants.js
'''
f=open(PROJECT_ROOT+"/website/assets/js/constants.js", "w")
f.write(new_constants_js_content)

print("Completed.")
