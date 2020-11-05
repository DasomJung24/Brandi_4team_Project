from config import shipment_button, order_status


class OrderService:
    def __init__(self, order_dao, seller_dao):
        self.order_dao = order_dao
        self.seller_dao = seller_dao

    def get_product_data(self, product_id, session):
        """ 상품 구매할 때 구매하려는 상품의 정보 가져오기

        Args:
            product_id : 상품 id
            session    : db 연결

        Returns:
            product : 상품 데이터

        """
        product_data = self.order_dao.select_product_data_for_order(product_id, session)
        product = dict()
        product['id'] = product_data['id']

        if product_data['discount_rate'] != 0:
            # 할인 금액은 10단위부터라고 되어 있음
            product['price'] = round(int(product_data['price']*(100-product_data['discount_rate'])/100), -1)
        else:
            product['price'] = product_data['price']

        # 옵션 정보, 컬러 id 와 이름, 사이즈 id 와 이름 가져오기
        option_data = self.order_dao.select_product_option(product_id, session)

        product['options'] = [dict(row) for row in option_data]

        return product

    def order_product(self, order_data, seller_id, session):
        """ 상품 주문하기

        Args:
            order_data : 주문 데이터
            seller_id  : 셀러 id
            session    : db 연결

        Returns:
            invalid count : 주문수량과 재고수량이 맞지 않을 때

        """
        # 상품 최소 판매 수량, 최대 판매 수량 데이터 가져오기
        product_data = self.order_dao.select_product_data_for_order(order_data['product_id'], session)

        # 상품의 재고 수량, 재고관리여부 가져오기
        stock = self.order_dao.check_product_stock(order_data['product_id'], order_data['color_id'],
                                                   order_data['size_id'], session)

        # 재고관리여부를 확인하여 재고관리를 한다면
        # 재고수량과 비교하여 주문수량이 더 많은 경우 에러 발생 (마이너스 재고는 없다 가정)
        if stock['is_inventory_manage'] == 1:
            if stock['count'] < order_data['count']:
                return 'invalid count'

        # 설정한 최대 판매수량과 비교하여 주문수량이 더 많은 경우 에러 발생
        # 설정한 최소 판매 수량과 비교하여 주문수량이 더 적은 경우 에러 발생
        if product_data['maximum_sell_count'] < order_data['count'] \
                or product_data['minimum_sell_count'] > order_data['count']:
            return 'invalid count'

        # 주문할 때 옵션의 재고수량 변경 후에 옵션 아이디 가져와서 주문 테이블에 넣기
        option_id = self.order_dao.change_option_inventory(order_data, session)

        self.order_dao.insert_order_data(order_data, option_id, seller_id, session)

    def get_order_product_list(self, query_string_list, session):
        """ 주문 리스트 가져오기

        Args:
            query_string_list : 필터링 조건 쿼리스트링 리스트
            session           : db 연결

        Returns:
            order_list : 필터링된 주문 리스트 및 리스트의 총 개수


        상품 준비 관리 : 1  / 배송중 관리 : 2  / 배송완료 관리 : 3  / 구매확정 관리 : 4
        """
        order_products = self.order_dao.select_order_products(query_string_list, session)
        orders = order_products['order_list']
        order_list = []

        for order in orders:
            order_data = {
                'order_id':             order['id'],
                'order_date':           order['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
                'order_number':         order['number'],
                'order_detail_number':  order['detail_number'],
                'product_name':         order['name'],
                'user_name':            order['user_name'],
                'product_id':           order['product_id'],
                'phone_number':         order['phone_number'],
                'order_status_id':      query_string_list['order_status_id'],
                'brand_name_korean':    order['brand_name_korean'],
                'total_price':          order['total_price']
            }

            # 배송중, 배송완료, 구매확정 관리에는 배송시작날짜 or 배송완료날짜 or 구매확정날짜가 필요함
            # 상품 준비 관리가 아닐때는 상태이력의 업데이트된 날짜를 가져옴
            if query_string_list['order_status_id'] != order_status['PREPARE_PRODUCT']:
                order_data['shipment_date'] = order['update_time'].strftime('%Y-%m-%d %H:%M:%S')

            # 상품준비, 구매확정에는 사이즈이름, 컬러이름, 수량이 필요함
            if query_string_list['order_status_id'] == order_status['PREPARE_PRODUCT'] \
                    or query_string_list['order_status_id'] == order_status['CONFIRM_ORDER']:
                order_data['size_name'] = order['size_name']
                order_data['color_name'] = order['color_name']
                order_data['count'] = order['count']

            order_list.append(order_data)

        return {'order_list': [dict(row) for row in order_list], 'total_count': order_products['total_count']}

    def change_order_status(self, order_list, session):
        """ 마스터가 배송 처리 버튼을 눌러서 상품의 주문 상태 변경하기

        Args:
            order_list : 상태 변경하려는 주문의 id 리스트, 배송 처리 버튼
            session    : db 연결

        Returns:


        배송 처리 버튼 : 1 / 배송 완료 처리 버튼 : 2
        """
        if order_list['shipment_button'] == shipment_button['SHIPMENT']:
            for order_id in order_list['order_id_list']:
                # 상품의 주문상태 id 가져오기
                order_status_id = self.order_dao.get_order_status_id(order_id, session)

                # 상품의 주문상태 id 가 상품 준비 상태가 맞으면 업데이트
                if order_status_id['order_status_id'] == order_status['PREPARE_PRODUCT']:
                    self.order_dao.order_status_change_shipment(order_id, session)
                else:
                    return f'order_id : {order_id} is not invalid'

        elif order_list['shipment_button'] == shipment_button['SHIPMENT_COMPLETE']:
            for order_id in order_list['order_id_list']:
                # 상품의 주문상태 id 가져오기
                order_status_id = self.order_dao.get_order_status_id(order_id, session)

                # 상품의 주문상태 id 가 상품 배송중이 맞으면 업데이트
                if order_status_id['order_status_id'] == order_status['SHIPPING']:
                    self.order_dao.order_status_change_complete(order_id, session)
                else:
                    return f'order_id : {order_id} is not invalid'

    def get_details(self, order_id, session):
        """ 주문 상세페이지 데이터 가져오기

        Args:
            order_id : 주문 id
            session  : db 연결

        Returns:
            order_data : 주문 상세 데이터

        """
        order = self.order_dao.select_order_details(order_id, session)

        order_data = {
            'detail_number':    order['detail_number'],
            'number':           order['number'],
            'order_date':       order['created_at'].strftime('%Y-%m-%d %H:%M:%S'),
            'address':          order['address'] + ' ' + order['detail_address'],
            'zip_code':         order['zip_code'],
            'order_status_id':  order['order_status_id'],
            'product_name':     order['name'],
            'price':            order['price'],
            'discount_rate':    order['discount_rate'],
            'discount_price':   round(int(order['price']*(100-order['discount_rate'])/100), -1)
                                if order['discount_rate'] != 0 else 0,
            'count':            order['count'],
            'user_name':        order['user_name'],
            'phone_number':     order['phone_number'],
            'product_number':   order['id'],
            'total_price':      order['total_price'],
            'brand_name':       order['brand_name_korean'],
            'size_name':        order['size_name'],
            'color_name':       order['color_name']
        }

        # 주문 상태 변경 이력 가져오기
        histories = self.order_dao.select_order_histories(order_id, session)
        data = []

        # 히스토리 시간 형태 바꾸기 위해서 for 문 실행
        for history in histories:
            order_history = {
                'order_status_id':  history['order_status_id'],
                'update_time':      history['update_time'].strftime('%Y-%m-%d %H:%M:%S')
            }
            data.append(order_history)

        # 주문 데이터에 이력 리스트 넣어주기
        order_data['order_histories'] = [dict(row) for row in data]

        return order_data

    def change_number(self, data, account_id, session):
        """ 주문 상세페이지 주문자 핸드폰 번호 수정하기

        Args:
            data       : 변경하려는 핸드폰 번호, 주문 id
            account_id : 계정의 id
            session    : db 연결

        Returns:

        """
        # 마스터 계정인지 확인하기
        is_master = self.seller_dao.is_master(account_id, session)

        # 마스터 계정이 아닐 때 에러 발생
        if is_master['is_master'] == 0:
            return 'not authorized'

        self.order_dao.update_phone_number(data, session)
