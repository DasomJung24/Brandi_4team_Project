from datetime import datetime
from sqlalchemy import text
from exceptions import NoAffectedRowException, NoDataException


class OrderDao:

    def select_product_data_for_order(self, product_id, session):
        # 상품 구매할 때 상품 정보 가져오기
        product_data = session.execute(text("""
            SELECT 
                id,
                price,
                discount_rate,
                maximum_sell_count,
                minimum_sell_count
            FROM products
            WHERE
                id = :id
        """), {'id': product_id}).fetchone()

        return product_data

    def select_product_option(self, product_id, session):
        # 상품 구매할 때 옵션 정보와 컬러이름, 사이즈 이름 가져오기
        options = session.execute(text("""
            SELECT 
                a.size_id, 
                a.color_id, 
                a.is_inventory_manage, 
                a.count, 
                b.name as color_name, 
                c.name as size_name 
            FROM options a 
            JOIN colors b 
            ON a.color_id = b.id 
            JOIN sizes c ON c.id=a.size_id 
            WHERE 
                a.product_id = :product_id
        """), {'product_id': product_id}).fetchall()

        if options is None:
            raise NoDataException(500, 'select_product_option select error')

        return options

    def check_product_stock(self, product_id, color_id, size_id, session):
        # 상품 재고 수량 확인하기
        stock = session.execute(text("""
            SELECT
                count,
                is_inventory_manage
            FROM 
                options
            WHERE
                product_id = :product_id
            AND 
                size_id = :size_id
            AND 
                color_id = :color_id
        """), {'product_id': product_id,
               'size_id': size_id,
               'color_id': color_id}).fetchone()

        if stock is None:
            NoDataException(500, 'check_product_stock select error')

        return stock

    def change_option_inventory(self, order_data, session):
        # 옵션의 재고 수량 수정하기
        option = session.execute(text("""
            SELECT
                id,
                count,
                is_inventory_manage
            FROM options
            WHERE
                size_id = :size_id 
            AND 
                color_id = :color_id
            AND 
                product_id = :product_id
        """), order_data).fetchone()

        if option is None:
            raise NoDataException(500, 'change_option_inventory select error')

        if option['is_inventory_manage'] is True:
            # 재고관리여부가 True 이면 재고 수량 수정하기
            option_row = session.execute(text("""
                UPDATE
                    options
                SET
                    count = :count
                WHERE
                    id = :id
            """), {'id': option['id'], 'count': int(option['count']) - order_data['count']}).rowcount

            if option_row == 0:
                raise NoAffectedRowException(500, 'change_option_inventory update error')

        return option['id']

    def insert_order_data(self, order_data, option_id, seller_id, session):
        # 주문 정보 데이터에 저장하기
        order_id = session.execute(text("""
            INSERT INTO orders (
                user_name,
                phone_number,
                zip_code,
                address,
                detail_address
            ) VALUES (
                :user_name,
                :phone_number,
                :zip_code,
                :address,
                :detail_address
            )
        """), order_data).lastrowid

        if order_id is None:
            raise NoAffectedRowException(500, 'insert_order_data insert error')

        # 주문 아이디 이용하여 주문 번호 등록 하기
        order_number = session.execute(text("""
            UPDATE
                orders
            SET
                number = :number
            WHERE
                id = :id
        """), {'id': order_id,
               'number': datetime.today().strftime("%Y%m%d")+'%05d' % order_id}).rowcount

        if order_number == 0:
            raise NoAffectedRowException(500, 'insert_order_data update error')

        # 주문 상세 정보 저장하기
        order_detail_row = session.execute(text("""
            INSERT INTO order_details (
                order_id,
                product_id,
                detail_number,
                count,
                order_status_id,
                option_id,
                total_price,
                seller_id
            ) VALUES (
                :order_id,
                :product_id,
                :detail_number,
                :count,
                1,
                :option_id,
                :total_price,
                :seller_id
            )
        """), {'order_id': order_id, 'product_id': order_data['product_id'],
               'detail_number': datetime.today().strftime("%Y%m%d") + '%06d' % order_id,
               'count': order_data['count'], 'seller_id': seller_id,
               'option_id': option_id, 'total_price': order_data['total_price']}).rowcount

        if order_detail_row == 0:
            raise NoAffectedRowException(500, 'insert_order_data detail insert error')

        # 주문 상태 히스토리 저장하기
        order_history = session.execute(text("""
            INSERT INTO order_status_histories (
                update_time,
                order_status_id,
                order_id
            ) VALUES (
                now(),
                1,
                :order_id
            )
        """), {'order_id': order_id}).rowcount

        if order_history == 0:
            raise NoAffectedRowException(500, 'insert_order_data history insert error')

    def select_order_products(self, query_string_list, session):
        # 준비완료, 배송중, 배송완료, 구매확정 상품 리스트 가져오기
        data = """
            SELECT
                a.id,
                a.created_at,
                a.number,
                b.detail_number,
                b.product_id,
                b.count,
                a.user_name,
                a.phone_number,
                b.order_status_id,
                c.name,
                d.update_time,
                e.size_id,
                e.color_id,
                f.brand_name_korean,
                b.total_price,
                g.name as size_name,
                h.name as color_name
            """

        count = """
            SELECT
                count(*) as cnt
            """

        sql = """
            FROM orders a
            JOIN order_details b
            ON a.id = b.order_id
            JOIN products c
            ON b.product_id = c.id
            JOIN order_status_histories d
            ON b.order_status_id = d.order_status_id
            AND d.order_id = a.id
            JOIN options e
            ON e.id = b.option_id
            JOIN sellers f
            ON f.id = b.seller_id
            JOIN sizes g
            ON g.id = e.size_id
            JOIN colors h
            ON h.id = e.color_id
            WHERE
                b.order_status_id = :order_status_id
        """

        # 시작 날짜
        if query_string_list['start_date']:
            sql += """
            AND
                d.update_time > :start_date """

        # 끝나는 날짜
        if query_string_list['end_date']:
            sql += """
            AND
                d.update_time < :end_date """

        # 주문 번호
        if query_string_list['order_number']:
            sql += """
            AND
                a.number = :order_number """

        # 주문 상세 번호
        if query_string_list['detail_number']:
            sql += """
            AND
                b.detail_number = :detail_number """

        # 주문자
        if query_string_list['user_name']:
            sql += """
            AND
                a.user_name = :user_name """

        # 핸드폰 번호
        if query_string_list['phone_number']:
            sql += """
            AND
                a.phone_number = :phone_number """

        # 상품명
        if query_string_list['product_name']:
            sql += """
            AND
                c.name = :product_name """

        """
        정렬하기 ( 닐짜순, 날짜 역순 )
        order_by : a.created_at ASC / a.created_at DESC / d.update_time ASC / d.update_time DESC
                       1           /           2        /        3          /         4
        """
        if query_string_list['order_by']:
            # 결제일순 정렬
            if query_string_list['order_by'] == 1:
                sql += """
                ORDER BY a.created_at ASC """

            # 결제일 역순 정렬
            if query_string_list['order_by'] == 2:
                sql += """
                ORDER BY a.created_at DESC """

            # 업데이트순 정렬
            if query_string_list['order_by'] == 3:
                sql += """
                ORDER BY d.update_time ASC """

            # 업데이트 역순 정렬
            if query_string_list['order_by'] == 4:
                sql += """
                ORDER BY d.update_time DESC """

        total_count = session.execute(text(count+sql), query_string_list).fetchone()

        sql += """
        LIMIT :limit
        OFFSET :offset """

        order_list = session.execute(text(data+sql), query_string_list).fetchall()

        return {'order_list': [dict(row) for row in order_list], 'total_count': total_count['cnt']}

    def order_status_change_shipment(self, order_id, session):
        # 배송처리 버튼 눌러서 배송중으로 상태 바꾸기
        status_row = session.execute(text("""
            UPDATE
                order_details
            SET
                order_status_id = 2
            WHERE
                order_id = :order_id
        """), order_id).rowcount

        if status_row == 0:
            raise NoAffectedRowException(500, 'order_status_change_shipment update error')

        # 배송 상태 변화 이력 저장하기
        history_row = session.execute(text("""
            INSERT INTO order_status_histories (
                update_time,
                order_status_id,
                order_id
            ) VALUES (
                now(),
                2,
                :order_id
            )
        """), order_id).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'order_status_change_shipment insert error')

    def order_status_change_complete(self, order_id, session):
        # 배송완료 처리 버튼 눌러서 배송완료로 상태 바꾸기
        status_row = session.execute(text("""
            UPDATE
                order_details
            SET
                order_status_id = 3
            WHERE
                order_id = :order_id
        """), order_id).rowcount

        if status_row == 0:
            raise NoAffectedRowException(500, 'order_status_change_complete update error')

        # 배송 상태 변화 이력 저장하기
        history_row = session.execute(text("""
            INSERT INTO order_status_histories (
                update_time,
                order_status_id,
                order_id
            ) VALUES (
                now(),
                3,
                :order_id
            )
        """), order_id).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'order_status_change_complete insert error')

    def select_order_details(self, order_id, session):
        # 주문 상세페이지 정보 가져오기
        order_data = session.execute(text("""
            SELECT 
                a.number,
                a.created_at,
                a.address,
                a.detail_address,
                a.zip_code,
                a.user_name,
                a.phone_number,
                b.order_status_id,
                b.count,
                b.detail_number,
                b.total_price,
                c.name,
                c.price,
                c.discount_rate,
                c.id,
                d.brand_name_korean,
                e.size_id,
                e.color_id,
                f.name as color_name,
                g.name as size_name
            FROM orders a
            JOIN order_details b
            ON a.id = b.order_id
            JOIN products c
            ON b.product_id = c.id
            JOIN sellers d 
            ON d.id = c.seller_id 
            JOIN options e 
            ON b.option_id = e.id
            JOIN colors f
            ON f.id = e.color_id
            JOIN sizes g
            ON g.id = e.size_id
            WHERE 
                a.id = :order_id
        """), {'order_id': order_id}).fetchone()

        if order_data is None:
            raise NoDataException(500, 'select_order_details select error')

        return order_data

    def select_order_histories(self, order_id, session):
        # 주문 상태 변화 히스토리 목록 가져오기
        histories = session.execute(text("""
            SELECT
                update_time,
                order_status_id
            FROM order_status_histories
            WHERE
                order_id = :order_id
        """), {'order_id': order_id}).fetchall()

        return histories

    def update_phone_number(self, data, session):
        # 핸드폰 번호 수정하기
        update_row = session.execute(text("""
            UPDATE
                orders
            SET
                phone_number = :phone_number
            WHERE
                id = :order_id
        """), data).rowcount

        if update_row == 0:
            raise NoAffectedRowException(500, 'update_phone_number update error')
