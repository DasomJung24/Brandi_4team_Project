from flask import current_app


class ProductService:
    def __init__(self, product_dao):
        self.product_dao = product_dao

    def post_register_product(self, product_data, session):
        # 상품 등록하기
        # 상품 선분이력 close_time 설정하기
        product_data['close_time'] = current_app.config['CLOSE_TIME']
        product_id = self.product_dao.insert_product_data(product_data, session)

        ordering = 1
        for option in product_data['options']:
            option['product_id'] = product_id
            option['ordering'] = ordering
            self.product_dao.insert_data_option(option, session)
            ordering += 1

        if product_data['image_list'] is not None:
            for image in product_data['image_list']:
                image['product_id'] = product_id
                self.product_dao.insert_data_sub_image(image, session)

    def get_product(self, product_id, session):
        # 상품 수정 페이지 들어갔을 때 등록된 상품 정보 가져오기
        product_data = self.product_dao.select_product_data(product_id, session)
        option_list = self.product_dao.select_product_options(product_id, session)
        sub_images = self.product_dao.select_product_images(product_id, session)

        # 새로운 상품 데이터 리스트 만들면서 할인가, 시간 형식 수정
        product = {}
        product['is_sell'] = product_data['is_sell']
        product['is_display'] = product_data['is_display']
        product['sub_categories_id'] = product_data['sub_categories_id']
        product['manufacturer'] = product_data['manufacturer']
        product['manufacture_date'] = product_data['manufacture_date'].strftime('%Y-%m-%d %H:%M:%S') \
            if product_data['manufacture_date'] is not None else None
        product['origin'] = product_data['origin']
        product['name'] = product_data['name']
        product['simple_information'] = product_data['simple_information']
        product['main_image'] = product_data['main_image']
        product['detail'] = product_data['detail']
        product['price'] = product_data['price']
        product['discount_rate'] = product_data['discount_rate']
        product['is_discount'] = product_data['is_discount']
        product['discount_price'] = round(int(product_data['price']*(100-product_data['discount_rate'])/100), -1)
        product['discount_start_date'] = product_data['discount_start_date'].strftime('%Y-%m-%d %H:%M:%S') \
            if product_data['discount_start_date'] is not None else None
        product['discount_end_date'] = product_data['discount_end_date'].strftime('%Y-%m-%d %H:%M:%S') \
            if product_data['discount_end_date'] is not None else None
        product['minimum_sell_count'] = product_data['minimum_sell_count']
        product['maximum_sell_count'] = product_data['maximum_sell_count']
        product['code_number'] = product_data['code_number']
        product['options'] = [dict(row) for row in option_list]
        product['image_list'] = [dict(row) for row in sub_images]

        return product

    def post_update_product(self, product_data, session):
        # 상품 데이터 업데이트 하기
        product_data['close_time'] = current_app.config['CLOSE_TIME']

        options = product_data['options']
        for option in options:
            option['product_id'] = product_data['product_id']

        self.product_dao.update_option(options, session)

        if product_data['image_list'] is not None:
            image_list = product_data['image_list']
            for image in image_list:
                image['product_id'] = product_data['product_id']

            self.product_dao.update_sub_image(image_list, session)

        self.product_dao.update_product_data(product_data, session)

    def get_product_list(self, query_string_list, session):
        # 상품관리 셀러한테 등록된 상품들 가져오기
        products_data = self.product_dao.select_product_list(query_string_list, session)
        products_list = products_data['product_list']
        product_list = []

        # 등록시간과 할인가격을 수정/추가하면서 새로운 리스트를 만듬
        for product in products_list:
            product_data = {}
            product_data['name'] = product['name']
            product_data['product_id'] = product['id']
            product_data['main_image'] = product['main_image']
            product_data['created_at'] = product['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            product_data['code_number'] = product['code_number']
            product_data['price'] = product['price']
            product_data['discount_rate'] = product['discount_rate']
            product_data['discount_price'] = round(int(product['price']*(100-product['discount_rate'])/100), -1)
            product_data['is_sell'] = product['is_sell']
            product_data['is_display'] = product['is_display']
            product_data['is_discount'] = product['is_discount']
            product_data['product_number'] = product['id']
            product_list.append(product_data)

        return {'product_list': product_list, 'total_count': products_data['total_count']}
