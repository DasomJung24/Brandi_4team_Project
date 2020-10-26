import jwt
import math
from datetime import datetime as dt

from flask      import request, jsonify, g, current_app
from functools  import wraps

# access_token decorator
def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decode(access_token, current_app.config['JWT_SECRET_KEY'], current_app.config['ALGORITHM'])
            except jwt.InvalidTokenError:
                payload = None 

            if payload is None: return jsonify({'message':'INVALID TOKEN'}),400

            seller_id   = payload['seller_id']
            g.seller_id = seller_id
        else:
            return jsonify({'message':'NOT EXIST TOKEN'}),401
        
        return func(*args, **kwargs)
    return decorated_function

def seller_endpoints(app, services):
    seller_service = services.seller_service

    @app.route("/signup", methods=['POST'])
    def sign_up():
        new_seller = request.json
        new_seller = seller_service.create_new_seller(new_seller)
        
        if new_seller == 'already exist':    return jsonify({'message':'ALREADY_EXIST'}), 400
        if new_seller == 'invalid request':  return jsonify({'message':'INVALID_REQUEST'}), 400
        if new_seller == 'short account':    return jsonify({'message':'SHORT_ACCOUNT'}), 400
        if new_seller == 'invalid password': return jsonify({'message':'INVALID_PASSWORD'}), 400 
        if new_seller == 'key error':        return jsonify({'message':'KEY_ERROR'}), 400

        return jsonify({'message':'SUCCESS'}), 200

    @app.route("/login", methods=['POST'])
    def log_in():
        seller = request.json
        token = seller_service.login(seller)
        
        if token == 'not exist':       return jsonify({'message':'NOT_EXIST'}), 400
        if token == 'wrong password':  return jsonify({'message':'WRONG_PASSWORD'}), 400
        if token == 'deleted account': return jsonify({'message':'INVALID_ACCOUNT'}), 400
        if token == 'key error':       return jsonify({'message':'KEY_ERROR'}), 400
        
        return jsonify({'access_token':token})

    @app.route("/mypage", methods=['GET', 'POST'])
    @login_required
    def my_page():  # 회원관리-셀러정보관리(셀러)
        if request.method == 'GET':
            seller_data = seller_service.get_my_page(g.seller_id)
            
            return jsonify(seller_data)

        if request.method == 'POST':
            seller_data = request.json
            seller_data = seller_service.post_my_page(seller_data, g.seller_id)
            
            if seller_data is None:
                return jsonify({'message':'INVALID REQUEST'}), 400
            
            return jsonify({'message':'SUCCESS'}), 200

    @app.route("/master/management-seller", methods=['GET', 'POST'])
    @login_required
    def management_seller():     # 셀러계정관리(마스터)
        if request.method == 'GET':        
            limit              = request.args.get('limit', None)
            offset             = request.args.get('offset', None)
            number             = request.args.get('number', None)
            account            = request.args.get('account', None)
            brand_name_korean  = request.args.get('brand_name_ko', None)
            brand_name_english = request.args.get('brand_name_en', None)
            manager_name       = request.args.get('manager_name', None)
            manager_number     = request.args.get('manager_number', None)
            manager_email      = request.args.get('manager_email', None)
            seller_status_id   = request.args.get('status', None)
            seller_property_id = request.args.get('property', None)
            create_start_date  = request.args.get('start_date', None)
            create_end_date    = request.args.get('end_date', None)


            seller_list = seller_service.get_seller_list(g.seller_id)
            
            if seller_list == 'not authorizated': return jsonify({'message':'NOT_AUTHORIZATED'}), 400

            seller_list = [seller for seller in seller_list if seller['number']==int(number)] if number is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['account']==account] if account is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['brand_name_korean']==brand_name_korean] if brand_name_korean is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['brand_name_english']==brand_name_english] if brand_name_english is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['name']==manager_name] if manager_name is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['phone_number']==manager_number] if manager_number is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['email']==manager_email] if manager_email is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['seller_status_id']==int(seller_status_id)] if seller_status_id is not None else seller_list
            seller_list = [seller for seller in seller_list if seller['seller_property_id']==int(seller_property_id)] if seller_property_id is not None else seller_list
            seller_list = [seller for seller in seller_list if dt.strptime(seller['created_at'],'%Y-%m-%d %H:%M:%S') > dt.strptime(create_start_date,'%Y-%m-%d')] \
                if create_start_date is not None else seller_list
            seller_list = [seller for seller in seller_list if dt.strptime(seller['created_at'],'%Y-%m-%d %H:%M:%S') > dt.strptime(create_end_date,'%Y-%m-%d')] \
                if create_end_date is not None else seller_list

            total       = len(seller_list)
            limit       = 10 if limit is None else limit
            offset      = 0 if limit is None else offset
            seller_list = seller_list[offset:offset+limit] if (offset and limit) is not None else seller_list
            
            return jsonify({'seller_list':seller_list, 'total':total, 'page':math.ceil(total/view)})

        if request.method == 'POST':
            seller_status = request.json
            seller_id     = seller_status['id']
            button        = seller_status['button']
            status        = seller_service.post_seller_status(seller_id, button)

            if status == 'invalid request': return jsonify({'message' : 'INVALID_REQUEST'}), 400
            if status == 'message fail':    return jsonify({'message' : 'MESSAGE_FAILED'}), 400
            
            return jsonify({'message':'SUCCESS'}), 200