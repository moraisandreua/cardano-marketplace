const BLOCKFROST_PROJECT_ID = "preprodeMB9jfka6qXsluxEhPLhKczRdaC5QKab";
const BLOCKFROST_API_URL = "https://cardano-preprod.blockfrost.io/api/v0/";

const getMintedAssets = async (policyId) => {
    const endpoint = "assets/policy/";

    var assets = [];
    await fetch(BLOCKFROST_API_URL+endpoint+policyId, {
        headers:{ "project_id":BLOCKFROST_PROJECT_ID }
    })
    .then((data)=>data.json())
    .then((data)=>{
        if(!data["error"])
            assets=data;
    });

    return assets;
}


const getAddressAssets = async (address) => {
    const endpoint = "addresses/";

    var assets = [];
    await fetch(BLOCKFROST_API_URL+endpoint+address, {
        headers:{ "project_id":BLOCKFROST_PROJECT_ID }
    })
    .then((data)=>data.json())
    .then((data)=>{
        assets=data;
    });

    return assets;
}


const getAssetsFromPolicy = async (policy) => {
    var endpoint="assets/policy/"+policy; // policy is defined in constants.js

    var assets = []
    await fetch(BLOCKFROST_API_URL + endpoint, {headers:{"project_id":BLOCKFROST_PROJECT_ID}})
    .then((data)=>data.json())
    .then((data)=>{
        /* 
            quantity needs to be greater than 0, because, when the token is burnt, the token is stil visible in 
            the blockchain but it's quantity is 0
        */
        assets=data.filter((e)=>e.quantity!="0"); 
    })

    return assets;
}


const getAssetDetails = async (asset) => {
    const endpoint = "assets/"+asset;

    var details = {};

    await fetch(BLOCKFROST_API_URL+endpoint, {
        headers:{ "project_id":BLOCKFROST_PROJECT_ID }
    })
    .then((data)=>data.json())
    .then((data)=>{
        details = data["onchain_metadata"];
    });

    return details;
}