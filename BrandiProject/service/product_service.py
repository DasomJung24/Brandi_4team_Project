class ProductService:
    def __init__(self, product_dao):
        self.product_dao = product_dao

    # 상품등록 
    def post_register_product(self, product_data):
        if product_data['sub_categories_id'] is None or product_data['name'] is None or product_data['main_image'] is None or\
            product_data['is_sell'] is None or product_data['is_display'] is None or product_data['is_discount'] is None or \
            product_data['price'] is None or  product_data['detail'] is None or product_data['maximum_sell_count'] is None or\
            product_data['minimum_sell_count'] is None:
            return 'invalid request'

        if product_data['options'] is None: return 'invalid request'

        for options in product_data['options']:
            if options['color_id'] is None or options['size_id'] is None or options['is_inventory_manage'] is None:
                return 'invalid request'
 
        return self.product_dao.insert_product_data(product_data)

    # 상품수정
    def post_update_product(self, product_data):
        if product_data['sub_categories_id'] is None or product_data['name'] is None or product_data['product_id'] is None or\
            product_data['is_sell'] is None or product_data['is_display'] is None or product_data['is_discount'] is None or \
            product_data['price'] is None or product_data['main_image'] is None or product_data['detail'] is None or \
            product_data['minimum_sell_count'] is None or product_data['maximum_sell_count'] is None:
            return 'invalid request'

        if product_data['options'] is None: return 'invalid request'

        for options in product_data['options']:
            if options['color_id'] is None or options['size_id'] is None or options['is_inventory_manage'] is None:
                return 'invalid request'
        
        return self.product_dao.update_product_data(product_data)

    # 상품관리 GET
    def get_product_list(self, seller_id):
        products_data = self.product_dao.select_product_list(seller_id)
        product_list = []
        
        for product in products_data:
            product_data = {}
            product_data['name']           = product['name']
            product_data['product_id']     = product['id']
            product_data['main_image']     = product['main_image']
            product_data['created_at']     = product['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            product_data['code_number']    = product['code_number']
            product_data['price']          = int(product['price'])
            product_data['discount_rate']  = product['discount_rate']
            product_data['discount_price'] = round(int(int(product['price'])*(100-product['discount_rate'])/100), -1)
            product_data['is_sell']        = product['is_sell']
            product_data['is_display']     = product['is_display']
            product_data['is_discount']    = product['is_discount']
            product_data['product_number'] = product['max(product_number)']
            product_list.append(product_data)

        return product_list