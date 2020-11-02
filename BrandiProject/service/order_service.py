from flask import current_app


class OrderService:
    def __init__(self, order_dao):
        self.order_dao = order_dao

    def get_product_data(self, product_id, session):
        """구매할때 상품 정보 가져오기
        :param product_id:
        :param session:
        :return: {
                    "price":10000,
                    "id":30,
                    "options": [{"size_id":1, "size_name":"free", "color_id":1,
                                "color_name":"Black", "is_inventory_manage":1,
                                "count":100},{"size_id":1, "size_name":"free",
                                "color_id":2, "color_name":"White",
                                "is_inventory_manage":1, "count":50}]
                }
        """
        product_data = self.order_dao.select_product_data(product_id, session)
        product = dict()
        product['id'] = product_data['id']

        if product_data['discount_rate'] != 0:
            product['price'] = round(int(product_data['price']*(100-product_data['discount_rate'])/100), -1)
        else:
            product['price'] = product_data['price']

        option_data = []

        # 옵션 정보 가져와서 컬러 이름이랑 사이즈 이름 가져오기
        option_list = self.order_dao.select_product_option(product_id, session)

        for options in option_list:
            option = dict()
            option['size_id'] = options['size_id']
            option['color_id'] = options['color_id']
            option['is_inventory_manage'] = options['is_inventory_manage']
            option['count'] = options['count']
            color_name = self.order_dao.select_color_name(options['color_id'], session)
            option['color_name'] = color_name['name']
            size_name = self.order_dao.select_size_name(options['size_id'], session)
            option['size_name'] = size_name['name']
            option_data.append(option)

        product['options'] = option_data

        return product

    def order_product(self, order_data, product_id, seller_id, session):
        # 주문할 때 옵션의 재고수량 변경 후에 옵션 아이디 가져와서 주문 테이블에 넣기
        option_id = self.order_dao.change_option_inventory(order_data, product_id, session)

        self.order_dao.insert_order_data(order_data, product_id, option_id, seller_id, session)

    def get_order_product_list(self, query_string_list, session):
        """ 셀러 상품 리스트 가져오기
        :param query_string_list:
        :param session:
        :return: {
                    "order_date": "2020-10-30 03:31:10",
                    "shipment_date":"",     # 상품준비외에는 들어감
                    "order_number": "202010300005",
                    "order_detail_number": "20201030000005",
                    "product_name": "시계",
                    "size_name":"free",     # 상품 준비관리랑 구매확정관리
                    "color_name":"yellow",  # 상품 준비관리랑 구매확정관리
                    "count":3,              # 상품 준비관리랑 구매확정관리
                    "user_name":"김땡땡",
                    "phone_number":"010-2225-5555",
                    "order_status": ""
                }
        """

        # 셀러의 상품들의 리스트 가져오기
        order_products = self.order_dao.select_order_products(query_string_list, session)
        orders = order_products['order_list']
        order_list = []

        for order in orders:
            order_data = dict()
            order_data['order_date'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            order_data['order_number'] = order['number']
            order_data['order_detail_number'] = order['detail_number']
            order_data['product_name'] = order['name']
            order_data['user_name'] = order['user_name']
            order_data['product_id'] = order['product_id']
            order_data['phone_number'] = order['phone_number']
            order_data['order_status_id'] = query_string_list['order_status_id']

            # 배송중, 배송완료, 구매확정 관리에는 배송시작날짜 or 배송완료날짜 or 구매확정날짜가 필요함
            if query_string_list['order_status_id'] != 1:
                order_data['shipment_date'] = order['update_time'].strftime('%Y-%m-%d %H:%M:%S')

            # 상품준비, 구매확정에는 사이즈이름, 컬러이름, 수량이 필요함
            if query_string_list['order_status_id'] == 1 or query_string_list['order_status_id'] == 4:
                size_name = self.order_dao.select_size_name(order['size_id'], session)
                order_data['size_name'] = size_name['name']
                color_name = self.order_dao.select_color_name(order['color_id'], session)
                order_data['color_name'] = color_name['name']
                order_data['count'] = order['count']

            order_list.append(order_data)

        return {'order_list': [dict(row) for row in order_list]}

    def change_order_status(self, order_id_list, shipment_button, session):
        """ 셀러가 주문 상태 변화 버튼 눌렀을 때 주문 상태 데이터 업데이트 하기
        셀러가 누르는 주문 상태 변화 버튼
        배송 처리 버튼 : 1  -> SHIPMENT
        배송 완료 처리 버튼 : 2   -> SHIPMENT_COMPLETE
        """
        if shipment_button == current_app.config.shipment_button['SHIPMENT']:
            for order_id in order_id_list['order_id_list']:
                self.order_dao.order_status_change_shipment(order_id, session)

        if shipment_button == current_app.config.shipment_button['SHIPMENT_COMPLETE']:
            for order_id in order_id_list['order_id_list']:
                self.order_dao.order_status_change_complete(order_id, session)

    def get_details(self, order_id, session):
        """ 주문 상세 페이지 정보 가져오기
        {"detail_number":, "number":, "order_date":,
         "address":, "detail_address":, "zip_code":,
         "order_status_id":, "order_status_histories":,
         "product_name":, "price":, "discount_price":,
         "discount_rate":, "count":, "user_name":,
         "size_name":, "color_name":, "phone_number":,
         "product_number":, "total_price":, "brand_name":}
         ## 주문일시 -> 변동 있는지 있는 거면 추가
         ## 요청사항?
        """
        order = self.order_dao.select_order_details(order_id, session)

        order_data = dict()
        order_data['detail_number'] = order['detail_number']
        order_data['number'] = order['number']
        order_data['order_date'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
        order_data['address'] = order['address'] + ' ' + order['detail_address']
        order_data['zip_code'] = order['zip_code']
        order_data['order_status_id'] = order['order_status_id']
        order_data['product_name'] = order['name']
        order_data['price'] = order['price']
        order_data['discount_rate'] = order['discount_rate']
        order_data['discount_price'] = round(int(order['price']*(100-order['discount_rate'])/100), -1) \
            if order['discount_rate'] != 0 else 0
        order_data['count'] = order['count']
        order_data['user_name'] = order['user_name']
        order_data['phone_number'] = order['phone_number']
        order_data['product_number'] = order['id']
        order_data['total_price'] = order['price'] if order_data['discount_price'] == 0 \
            else order_data['discount_price']
        order_data['brand_name'] = order['brand_name_korean']
        size = self.order_dao.select_size_name(order['size_id'], session)
        order_data['size_name'] = size['name']
        color = self.order_dao.select_color_name(order['color_id'], session)
        order_data['color_name'] = color['name']
        histories = self.order_dao.select_order_histories(order_id, session)
        order_data['order_histories'] = [dict(row) for row in histories]

        return order_data

    def change_number(self, data, session):
        # 핸드폰 번호 수정하기
        self.order_dao.update_phone_number(data, session)
