import config

from flask             import Flask
from sqlalchemy        import create_engine
from flask_cors        import CORS

from model             import SellerDao, ProductDao
from service           import SellerService, ProductService
from view              import seller_endpoints, product_endpoints

class Services:
    pass

def create_app(test_config=None):
    app = Flask(__name__)

    CORS(app, resources={r'*': {'origins': '*'}})

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

    # Persistence Layer
    seller_dao = SellerDao(database)
    product_dao = ProductDao(database)

    # Business Layer
    services = Services
    services.seller_service = SellerService(seller_dao, app.config)
    services.product_service = ProductService(product_dao)

    seller_endpoints(app, services)
    product_endpoints(app, services)

    return app