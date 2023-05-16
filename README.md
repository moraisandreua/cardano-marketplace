# Overview

The goal is to test some key features for marketplace workflow.

Features:
* Connect wallet
* Mint nft
* Put NFT for sale
* Buy NFT in the marketplace
* Doesn't require Smart Contracts
* Doesn't requires a dedicated Cardano node

**Workflow:**

* put diagrams here

**Some directories are required:**
* collection_ticket -> to store the policy keys for the launchpad collection (the one that is being minted)
* collection_info -> to store the policy keys for "_info" collection (which NFTs store information about the NFT being sold)
* project_storage -> to store the wallet for where the NFTs being sold are sent
* main_nft_wallet -> The selling profits from launchpad come to this wallet. 

**How to Run**
* create a virtual environment
```bash
    python3 -m venv venv
```

* enter virtual environment (in linux)
```bash
    source venv/bin/activate
```

* enter virtual environment (in windows)
```bash
    venv\Scripts\activate.bat
```

* install dependencies
```bash
    pip3 install -r requirements.txt
```

* setup all the required files/directories
```bash
    python3 setup.py
```
Note: this will create all the required directories

* you can run the server by calling the file
```bash
    python3 server.py
```

* Run the website in a server. It can be used the "Live Server" extension from Visual Studio Code (which i used for testing).

