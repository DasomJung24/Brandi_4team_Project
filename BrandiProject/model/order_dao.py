from datetime import datetime
from sqlalchemy import text
from exceptions import NoAffectedRowException, NoDataException


class OrderDao:

    def select_product_data(self, product_id, session):
        # 상품 구매할 때 상품 정보 가져오기
        product_data = session.execute(text("""
            SELECT 
                id,
                price,
                discount_rate
            FROM products
            WHERE
                id = :id
        """), {'id': product_id}).fetchone()

        return product_data

    def select_product_option(self, product_id, session):
        # 상품 구매할 때 옵션 정보 가져오기
        options = session.execute(text("""
            SELECT
                color_id,
                size_id,
                is_inventory_manage,
                count
            FROM options 
            WHERE
                product_id = :product_id
        """), {'product_id': product_id}).fetchall()

        return options

    def select_color_name(self, color_id, session):
        # 상품 구매할때 컬러 이름 가져오기
        color_name = session.execute(text("""
            SELECT
                name
            FROM colors
            WHERE
                id = :id
        """), {'id': color_id}).fetchone()

        return color_name

    def select_size_name(self, size_id, session):
        # 상품 구매할 때 사이즈 이름 가져오기
        size_name = session.execute(text("""
            SELECT
                name
            FROM sizes
            WHERE
                id = :id
        """), {'id': size_id}).fetchone()

        return size_name

    def change_option_inventory(self, order_data, product_id, session):
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
        """), {
            'size_id': order_data['size_id'],
            'color_id': order_data['color_id'],
            'product_id': product_id}).fetchone()

        if option is None:
            raise NoDataException(500, 'change_option_inventory select error')

        if option['is_inventory_manage'] is True:
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

    def insert_order_data(self, order_data, product_id, option_id, seller_id, session):
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
        """), {'order_id': order_id, 'product_id': product_id,
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
        sql = """
            SELECT
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
                e.color_id
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
            WHERE
                b.seller_id = :seller_id
            AND
                b.order_status_id = :order_status_id
        """

        if query_string_list['start_date']:
            sql += """
            AND
                d.update_time > :start_date """

        if query_string_list['end_date']:
            sql += """
            AND
                d.update_time < :end_date """

        if query_string_list['order_number']:
            sql += """
            AND
                a.number = :order_number """

        if query_string_list['detail_number']:
            sql += """
            AND
                b.detail_number = :detail_number """

        if query_string_list['user_name']:
            sql += """
            AND
                a.user_name = :user_name """

        if query_string_list['phone_number']:
            sql += """
            AND
                a.phone_number = :phone_number """

        if query_string_list['product_name']:
            sql += """
            AND
                c.name = :product_name """

        total_count = len(session.execute(text(sql), query_string_list).fetchall())

        sql += """
        ORDER BY :order_by
        LIMIT :limit
        OFFSET :offset """

        order_list = session.execute(text(sql), query_string_list).fetchall()

        return {'order_list': [dict(row) for row in order_list], 'total_count': total_count}

    def order_status_change_shipment(self, order_id, session):
        # 배송처리 버튼 눌러서 배송중으로 상태 바꾸기
        status_row = session.execute(text("""
            UPDATE
                order_details
            SET
                order_status_id = 2
            WHERE
                order_id = :order_id
        """), {'order_id': order_id}).rowcount

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
        """), {'order_id': order_id}).rowcount

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
        """), {'order_id': order_id}).rowcount

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
        """), {'order_id': order_id}).rowcount

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
                e.color_id
            FROM orders a
            JOIN order_details b
            ON a.id = b.order_id
            JOIN products c
            ON b.product_id = c.id
            JOIN sellers d 
            ON d.id = c.seller_id 
            JOIN OPTIONS e 
            ON b.option_id = e.id
            WHERE 
                a.id = :order_id
        """), {'order_id': order_id}).fetchone()

        if order_data is None:
            raise NoDataException(500, 'select_order_details select error')

        return order_data

    def select_order_histories(self, order_id, session):
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
        update_row = session.execute(text("""
            UPDATE
                orders
            SET
                phone_number = :phone_number
            WHERE
                id = :order_id
        """), data).rowcount

        if update_row == 0:
            raise NoAffectedRowException
