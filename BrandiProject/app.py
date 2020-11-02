import config

from flask import Flask, jsonify
from sqlalchemy import create_engine
from flask_cors import CORS
from flask_request_validator.exceptions import InvalidRequest
from model import SellerDao, ProductDao, OrderDao
from service import SellerService, ProductService, OrderService
from view import seller_endpoints, product_endpoints, order_endpoints
from sqlalchemy.orm import sessionmaker
from exceptions import InvalidUsage


class Services:
    pass

def create_app(test_config=None):

    def get_session():
        session = Session()
        return session

    app = Flask(__name__)

    CORS(app, resources={r'*': {'origins': '*'}})

    @app.errorhandler(Exception)
    def handle_invalid_usage(error):
        if isinstance(error, InvalidRequest):
            return {'message': str(error)}
        else:
            response = jsonify(error)
            response.status_code = error.status_code
            return response

    from contextlib import suppress
    from flask.json import JSONEncoder  
    
    class MyJSONEncoder(JSONEncoder):
        def default(self, obj):
            # Optional: convert datetime objects to ISO format
            with suppress(AttributeError):
                return obj.isoformat()
            return dict(obj)

    app.json_encoder = MyJSONEncoder

    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update(test_config)

    database = create_engine(app.config['DB_URL'], encoding='utf-8', max_overflow=0)
    Session = sessionmaker(bind=database, autocommit=False)
    # Persistence Layer
    seller_dao = SellerDao()
    product_dao = ProductDao()
    order_dao = OrderDao()

    # Business Layer
    services = Services
    services.seller_service = SellerService(seller_dao, app.config)
    services.product_service = ProductService(product_dao)
    services.order_service = OrderService(order_dao)

    seller_endpoints(app, services, get_session)
    product_endpoints(app, services, get_session)
    order_endpoints(app, services, get_session)

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host='192.168.7.6', port='5000', debug=True)


