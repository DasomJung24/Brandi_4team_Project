from config import product_record


class ProductService:
    def __init__(self, product_dao):
        self.product_dao = product_dao

    def get_category_color_size(self, session):
        """ 상품등록 페이지에 1차카테고리, 컬러, 사이즈 리스트 받아오기

        Args:
            session: db 연결

        Returns:
            data_list : 카테고리, 컬러, 사이즈 리스트

        """
        # 1차 카테고리 리스트 가져오기
        category_list = self.product_dao.select_category_list(session)

        # 컬러 리스트 가져오기
        color_list = self.product_dao.select_color_list(session)

        # 사이즈 리스트 가져오기
        size_list = self.product_dao.select_size_list(session)

        return {'categories': [dict(row) for row in category_list],
                'colors': [dict(row) for row in color_list],
                'sizes': [dict(row) for row in size_list]}

    def post_register_product(self, product_data, session):
        """ 상품 등록하기

        Args:
            product_data : 상품 데이터
            session      : db 연결

        Returns:

        """
        # 선분이력 close_time 값 넣어주기
        product_data['close_time'] = product_record['CLOSE_TIME']
        product_id = self.product_dao.insert_product_data(product_data, session)

        # 옵션리스트에 ordering 을 지정해서 데이터베이스에 넣어주기
        ordering = 1
        for option in product_data['options']:
            option['product_id'] = product_id
            option['ordering'] = ordering
            self.product_dao.insert_data_option(option, session)
            ordering += 1

        # 서브 이미지 리스트가 있는 경우 for 문으로 하나씩 넣어주기
        if product_data['image_list'] is not None:
            for image in product_data['image_list']:
                image['product_id'] = product_id
                self.product_dao.insert_data_sub_image(image, session)

    def get_sub_categories(self, category_id, session):
        """ 1차 카테고리 클릭했을 때 그에 해당하는 2차 카테고리 불러오기

        Args:
            category_id : 1차 카테고리 id
            session     : db 연결

        Returns:
            sub_category_list : 2차 카테고리 리스트

        """
        sub_category_list = self.product_dao.select_sub_categories(category_id, session)

        return sub_category_list

    def get_product(self, product_id, session):
        """ 상품 상세페이지 들어갔을 때 등록된 상품 정보 가져오기

        Args:
            product_id : 상품 id
            session    : db 연결

        Returns:
            product : 상품 데이터

        """
        # 상품 데이터 가져오기
        product_data = self.product_dao.select_product_data(product_id, session)

        # 상품에 해당하는 옵션들 가져오기
        option_list = self.product_dao.select_product_options(product_id, session)

        # 상품에 해당하는 서브 이미지들 가져오기
        sub_images = self.product_dao.select_product_images(product_id, session)

        # 새로운 상품 데이터 리스트 만들면서 할인가, 시간 형식 수정
        product = {
            'is_sell':              product_data['is_sell'],
            'is_display':           product_data['is_display'],
            'sub_categories_id':    product_data['sub_categories_id'],
            'manufacturer':         product_data['manufacturer'],
            'manufacture_date':     product_data['manufacture_date'].strftime('%Y-%m-%d %H:%M:%S')
                                    if product_data['manufacture_date'] is not None else None,
            'origin':               product_data['origin'],
            'name':                 product_data['name'],
            'simple_information':   product_data['simple_information'],
            'main_image':           product_data['main_image'],
            'detail':               product_data['detail'],
            'price':                product_data['price'],
            'discount_rate':        product_data['discount_rate'],
            'is_discount':          product_data['is_discount'],
            'discount_price':       round(int(product_data['price']*(100-product_data['discount_rate'])/100), -1)
                                    if product_data['discount_rate'] != 0 else 0,
            'discount_start_date':  product_data['discount_start_date'].strftime('%Y-%m-%d %H:%M:%S')
                                    if product_data['discount_start_date'] is not None else None,
            'discount_end_date':    product_data['discount_end_date'].strftime('%Y-%m-%d %H:%M:%S')
                                    if product_data['discount_end_date'] is not None else None,
            'minimum_sell_count':   product_data['minimum_sell_count'],
            'maximum_sell_count':   product_data['maximum_sell_count'],
            'code_number':          product_data['code_number'],
            'options':              [dict(row) for row in option_list],
            'image_list':           [dict(row) for row in sub_images]
        }

        return product

    def post_update_product(self, product_data, session):
        """ 상품 상세페이지 수정하기

        Args:
            product_data : 상품 데이터
            session      : db 연결

        Returns:

        """
        # 선분이력 close_time 값 넣어주기
        product_data['close_time'] = product_record['CLOSE_TIME']

        # 옵션에 상품 id 값 넣어주기
        options = product_data['options']
        for option in options:
            option['product_id'] = product_data['product_id']

        self.product_dao.update_option(options, session)

        # 서브 이미지 리스트가 비어있지 않으면 이미지리스트에 상품 id 값 넣어주어 데이터에 넣기
        if product_data['image_list'] is not None:
            image_list = product_data['image_list']
            for image in image_list:
                image['product_id'] = product_data['product_id']

            self.product_dao.update_sub_image(image_list, session)

        self.product_dao.update_product_data(product_data, session)

    def get_product_list(self, query_string_list, session):
        """ 상품 리스트 가져오기

        Args:
            query_string_list : 필터링 조건 쿼리스트링 리스트
            session           : db 연결

        Returns:
            product_list : 상품리스트 및 상품리스트의 총 개수

        """
        products_data = self.product_dao.select_product_list(query_string_list, session)
        products_list = products_data['product_list']
        product_list = []

        # 등록시간과 할인가격을 수정/추가하면서 새로운 리스트를 만듬
        for product in products_list:
            product_data = {
                'name':                 product['name'],
                'product_id':           product['id'],
                'main_image':           product['main_image'],
                'created_at':           product['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'code_number':          product['code_number'],
                'price':                product['price'],
                'discount_rate':        product['discount_rate'],
                'discount_price':       round(int(product['price']*(100-product['discount_rate'])/100), -1),
                'is_sell':              product['is_sell'],
                'is_display':           product['is_display'],
                'is_discount':          product['is_discount'],
                'product_number':       product['id'],
                'seller_property_id':   product['seller_property_id'],
                'brand_name_korean':    product['brand_name_korean']}

            product_list.append(product_data)

        return {'product_list': product_list, 'total_count': products_data['total_count']}
