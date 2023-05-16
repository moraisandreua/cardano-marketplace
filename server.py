from flask import Flask, request
from flask_restful import Resource, Api
from flask_cors import CORS
from endpoints.Mint import Mint
from endpoints.Wallet import Wallet
from endpoints.Sell import Sell
from endpoints.Buy import Buy

app = Flask(__name__)
api = Api(app)
cors = CORS(app, resources={r"/*": {"origins": "*"}})
app.config['CORS_HEADERS'] = 'Content-Type'

api.add_resource(Mint, '/mint')
api.add_resource(Wallet, '/wallet')
api.add_resource(Sell, '/sell')
api.add_resource(Buy, '/buy')

if __name__ == '__main__':
    app.run(debug=True)