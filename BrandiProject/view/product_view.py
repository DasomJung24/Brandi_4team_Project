from datetime import datetime as dt

from flask        import request, jsonify, g
from .seller_view import login_required

def product_endpoints(app, services):
    product_service = services.product_service

    @app.route("/product/register", methods=['POST'])
    @login_required
    def register_product():
        product_data              = request.json
        product_data['seller_id'] = g.seller_id
        product                   = product_service.post_register_product(product_data)

        if product == 'invalid request': return jsonify({'message':'INVALID_REQUEST'}), 400

        return jsonify({'message':'SUCCESS'}), 200
    # 상품상세페이지(수정) POST
    @app.route("/product/update", methods=['POST'])
    @login_required
    def update_product():
            product_data              = request.json
            product_data['seller_id'] = g.seller_id
            product                   = product_service.post_update_product(product_data)

            if product == 'invalid request': return jsonify({'message':'INVALID_REQUEST'}), 400

            return jsonify({'message':'SUCCESS'}), 200
    # 상품상세페이지(수정) GET
    @app.route("/product/update/<int:product_id>", methods=['GET'])
    @login_required
    def get_update_product(product_id):
        if product_id is None: return jsonify({'message':'PRODUCT_NOT_EXIST'}), 400

        product_data = product_service.get_product(product_id)
        
        if product_data is None: return jsonify({'message':'DATA_NOT_EXIST'}), 400

        return jsonify(product_data)

    @app.route("/product/management", methods=['GET'])
    @login_required
    def management_product():
        limit          = request.args.get('limit', None)
        offset         = request.args.get('offset', None)
        is_sell        = request.args.get('is_sell', None)
        is_discount    = request.args.get('is_discount', None)
        is_display     = request.args.get('is_display', None)
        name           = request.args.get('name', None)
        code_number    = request.args.get('code', None)
        product_number = request.args.get('number', None)
        create_start_date  = request.args.get('start_date', None)
        create_end_date    = request.args.get('end_date', None)

        product_list = product_service.get_product_list(g.seller_id)

        product_list = [product for product in product_list if product['is_sell']==int(is_sell)] if is_sell is not None else product_list
        product_list = [product for product in product_list if product['is_discount']==int(is_discount)] if is_discount is not None else product_list
        product_list = [product for product in product_list if product['is_display']==int(is_display)] if is_display is not None else product_list
        product_list = [product for product in product_list if product['name']==name] if name is not None else product_list
        product_list = [product for product in product_list if product['code_number']==code_number] if code_number is not None else product_list
        product_list = [product for product in product_list if product['product_number']==product_number] if product_number is not None else product_list
        product_list = [product for product in product_list if dt.strptime(product['created_at'],'%Y-%m-%d %H:%M:%S') > dt.strptime(create_start_date,'%Y-%m-%d')] \
                if create_start_date is not None else product_list
        product_list = [product for product in product_list if dt.strptime(product['created_at'],'%Y-%m-%d %H:%M:%S') > dt.strptime(create_end_date,'%Y-%m-%d')] \
                if create_end_date is not None else product_list

        total = len(product_list)
        offset = 0 if offset is None else offset
        limit = 10 if limit is None else limit 
        product_list = product_list[int(offset):int(offset+limit)] if (offset and limit) is not None else product_list
        
        return jsonify({'product_list':product_list, 'total':total})