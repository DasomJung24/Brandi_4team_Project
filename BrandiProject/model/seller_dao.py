from sqlalchemy import text
from exceptions import NoAffectedRowException, NoDataException


class SellerDao:

    def insert_seller(self, seller, session):
        seller_id = session.execute(text("""
            INSERT INTO sellers (
                account,
                password,
                brand_name_korean,
                brand_name_english,
                brand_crm_number,
                seller_property_id
            ) VALUES (
                :account,
                :password,
                :brand_name_korean,
                :brand_name_english,
                :brand_crm_number,
                :seller_property_id
            )
        """), seller).lastrowid

        if seller_id is None:
            raise NoAffectedRowException(500, 'insert_seller insert error')

        # 담당자 정보 입력하기
        manager_row = session.execute(text("""
            INSERT INTO manager_informations (
                phone_number,
                seller_id,
                ordering
            ) VALUES (
                :phone_number,
                :seller_id,
                1
            )
        """), {'seller_id': seller_id, 'phone_number': seller['phone_number']}).rowcount

        if manager_row == 0:
            raise NoAffectedRowException(500, 'insert_seller manager information insert error')

        # 계정 이력 관리
        history_row = session.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                1,
                :seller_id
            )
        """), {'seller_id': seller_id}).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'insert_seller status history insert error')

        return seller_id

    def get_seller_data(self, account, session):
        seller = session.execute(text("""
            SELECT
                id,
                account,
                password,
                is_delete,
                seller_status_id
            FROM sellers
            WHERE account = :account
        """), {'account': account}).fetchone()

        return seller if seller else None

    # 셀러 정보 관리 - 셀러 정보 가져오기
    def get_seller_information(self, seller_id, session):
        seller = session.execute(text("""
            SELECT
                id,
                image,
                background_image,
                simple_introduce,
                detail_introduce,
                brand_crm_open,
                brand_crm_end,
                is_brand_crm_holiday,
                zip_code,
                address,
                detail_address,
                delivery_information,
                refund_exchange_information,
                seller_status_id,
                brand_name_korean,
                brand_name_english,
                account,
                brand_crm_number,
                seller_property_id
            FROM sellers
            WHERE 
                id = :id
        """), {'id': seller_id}).fetchone()

        if seller is None:
            raise NoDataException(500, 'get_seller_information select error')

        return seller

    def get_manager_information(self, seller_id, session):
        # 담당자 정보는 1개 이상이라 모두 가져와서 배열로 보내기
        managers = session.execute(text("""
            SELECT
                name,
                email,
                phone_number
            FROM manager_informations
            WHERE
                seller_id = :seller_id
        """), {'seller_id': seller_id}).fetchall()

        if managers is None:
            raise NoDataException(500, 'get_seller_information manager information select error')

        return managers

    def get_seller_status_histories(self, seller_id, session):
        # 셀러 상태 변경 히스토리 가져오기
        seller_status = session.execute(text("""
            SELECT
                seller_status_id,
                update_time
            FROM seller_status_histories
            WHERE seller_id = :id
        """), {'id': seller_id}).fetchall()

        if seller_status is None:
            raise NoDataException(500, 'get_seller_information seller status select error')
        
        return seller_status

    # 셀러정보관리 페이지 업데이트
    def update_seller_information(self, seller, session):   # 셀러정보관리 페이지 update
        update_row = session.execute(text("""
            UPDATE
                sellers
            SET
                image                       = :image,
                background_image            = :background_image,
                simple_introduce            = :simple_introduce,
                detail_introduce            = :detail_introduce,
                brand_crm_open              = :brand_crm_open,
                brand_crm_end               = :brand_crm_end,
                is_brand_crm_holiday        = :is_brand_crm_holiday,
                zip_code                    = :zip_code,
                address                     = :address,
                detail_address              = :detail_address,
                delivery_information        = :delivery_information,
                refund_exchange_information = :refund_exchange_information,
                seller_status_id            = :seller_status_id,
                brand_name_korean           = :brand_name_korean,
                brand_name_english          = :brand_name_english,
                account                     = :account,
                brand_crm_number            = :brand_crm_number
            WHERE
                id = :id
        """), seller).rowcount

        # update 성공하면 해당하는 row 의 수 반환 실패하면 0 반환
        if update_row == 0:
            raise NoAffectedRowException(500, 'update_seller_information seller update error')

    def update_manager_information(self, manager, session):
        delete_row = session.execute(text("""
            DELETE FROM
                manager_informations
            WHERE
                seller_id = :seller_id
        """), {'seller_id': manager['seller_id']}).rowcount

        # delete 성공하면 해당하는 row 의 수 반환 실패하면 0 반환
        if delete_row == 0:
            raise NoAffectedRowException(500, 'update_seller_information manager information delete error')

        manager_row = session.execute(text("""
            INSERT INTO manager_informations(
                name,
                phone_number,
                email,
                seller_id,
                ordering
            ) VALUES (
                :name,
                :phone_number,
                :email,
                :seller_id,
                :ordering
            )
        """), manager).rowcount

        if manager_row == 0:
            raise NoAffectedRowException(500, 'update_seller_information manager information insert error')

    # 마스터인지 아닌지 확인하는 함수
    def is_master(self, seller_id, session):
        is_master = session.execute(text("""
            SELECT
                is_master
            FROM sellers
            WHERE id = :id
        """), {'id': seller_id}).fetchone()

        if is_master is None:
            raise NoDataException(500, 'is_master select error')

        return is_master

    # 마스터 셀러계정관리에서 셀러 계정 가져오기
    def select_seller_list(self, query_string_list, session):
        sql = """
            SELECT
                a.id, 
                a.account, 
                a.brand_name_korean, 
                a.brand_name_english,
                a.seller_property_id, 
                a.seller_status_id,
                a.created_at, 
                b.name, 
                b.phone_number, 
                b.email              
            FROM sellers a 
            INNER JOIN manager_informations b 
            ON a.id = b.seller_id
            WHERE 
             b.ordering = 1
            AND
             a.is_master = 0
            """

        if query_string_list['brand_name_korean']:
            sql += """
            AND
                a.brand_name_korean = :brand_name_korean """

        if query_string_list['number']:
            sql += """
            AND
                a.id = :number """

        if query_string_list['account']:
            sql += """
            AND
                a.account = :account """

        if query_string_list['brand_name_english']:
            sql += """
            AND
                a.brand_name_english = :brand_name_english """

        if query_string_list['manager_name']:
            sql += """
            AND
                b.name = :manager_name """

        if query_string_list['manager_number']:
            sql += """
            AND
                b.phone_number = :manager_number """

        if query_string_list['email']:
            sql += """
            AND
                b.email = :email """

        if query_string_list['seller_status_id']:
            sql += """
            AND
                a.seller_status_id = :seller_status_id """

        if query_string_list['seller_property_id']:
            sql += """
            AND
                a.seller_property_id = :seller_property_id """

        if query_string_list['start_date']:
            sql += """
            AND
                a.created_at > :start_date """

        if query_string_list['end_date']:
            sql += """
            AND
                a.created_at < :end_date """

        total_count = len(session.execute(text(sql), query_string_list).fetchall())

        sql += """
            LIMIT :limit
            OFFSET :offset """

        seller_list = session.execute(text(sql), query_string_list).fetchall()

        return {'seller_list': [dict(row) for row in seller_list], 'total_count': total_count}

    # 셀러 상태 입점으로 변경
    def status_change_store(self, seller_id, session):
        update_row = session.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 2
            WHERE
                id = :id
            """), {'id': seller_id}).rowcount

        if update_row == 0:
            raise NoAffectedRowException(500, 'status_change_store update error')

        history_row = session.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                2,
                :seller_id
            )
        """), {'seller_id': seller_id}).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'status_change_store insert error')

    # 셀러 상태 퇴점 대기 상태로 변경
    def status_change_closed_wait(self, seller_id, session):
        update_row = session.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 4
            WHERE
                id = :id
            """), {'id': seller_id}).rowcount

        if update_row == 0:
            raise NoAffectedRowException(500, 'status_change_closed_wait update error')

        history_row = session.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                4,
                :seller_id
            )
        """), {'seller_id': seller_id}).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'status_change_closed_wait insert error')

    # 셀러상태 휴점 상태로 변경
    def status_change_temporarily_closed(self, seller_id, session):
        update_row = session.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 3
            WHERE
                id = :id
            """), {'id': seller_id}).rowcount

        if update_row == 0:
            raise NoAffectedRowException(500, 'status_change_temporarily_closed update error')
            
        history_row = session.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                3,
                :seller_id
            )
        """), {'seller_id': seller_id}).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'status_change_temporarily_closed insert error')

    # 셀러상태 입점 거절로 변경
    def status_change_refused_store(self, seller_id, session):
        update_row = session.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 6,
                is_delete = True
            WHERE
                id = :id
            """), {'id': seller_id}).rowcount

        if update_row == 0:
            raise NoAffectedRowException(500, 'status_change_refused_store update error')

        history_row = session.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                6,
                :seller_id
            )
        """), {'seller_id': seller_id}).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'status_change_refused_store insert error')

    def status_change_closed_store(self, seller_id, session):
        # 셀러상태 퇴점으로 변경
        update_row = session.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 5,
                is_delete = True
            WHERE
                id = :id
            """), {'id': seller_id}).rowcount

        if update_row == 0:
            raise NoAffectedRowException(500, 'status_change_closed_store update error')

        # 셀러 상태 히스토리 등록 하기
        history_row = session.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                5,
                :seller_id
            )
        """), {'seller_id': seller_id}).rowcount

        if history_row == 0:
            raise NoAffectedRowException(500, 'status_change_closed_store insert error')

    def get_status_id(self, seller_id, session):
        # 셀러 입점상태 가져오기
        seller_status_id = session.execute(text("""
            SELECT
                seller_status_id
            FROM sellers
            WHERE 
                id = :id
            """), {'id': seller_id}).fetchone()

        if seller_status_id is None:
            raise NoDataException(500, 'get_status_id select error')

        return seller_status_id

    def select_home_data(self, seller_id, session):
        total_products = session.execute(text("""
            SELECT
                count(*)
            FROM products
            WHERE
                seller_id = :seller_id
        """), {'seller_id': seller_id}).fetchone()

        display_products = session.execute(text("""
            SELECT 
                count(*) 
            FROM products	
            WHERE 
                is_display = 1
            AND 
                seller_id = :seller_id
        """), {'seller_id': seller_id}).fetchone()

        prepare_shipment = session.execute(text("""
            SELECT
                count(*)
            FROM order_details
            WHERE
                order_status_id = 1
            AND
                seller_id = :seller_id
        """), {'seller_id': seller_id}).fetchone()

        complete_shipment = session.execute(text("""
            SELECT
                count(*)
            FROM order_details
            WHERE
                order_status_id = 3
            AND
                seller_id = :seller_id
        """), {'seller_id': seller_id}).fetchone()

        return {'total_count': total_products['count'],
                'display_count': display_products['count'],
                'prepare_count': prepare_shipment['count'],
                'complete_count': complete_shipment['count']}

    def update_seller_information_master(self, seller, session):
        # 마스터가 셀러정보를 업데이트할 때
        update_row = session.execute(text("""
            UPDATE
                sellers
            SET
                image                       = :image,
                background_image            = :background_image,
                simple_introduce            = :simple_introduce,
                detail_introduce            = :detail_introduce,
                brand_crm_open              = :brand_crm_open,
                brand_crm_end               = :brand_crm_end,
                is_brand_crm_holiday        = :is_brand_crm_holiday,
                zip_code                    = :zip_code,
                address                     = :address,
                detail_address              = :detail_address,
                delivery_information        = :delivery_information,
                refund_exchange_information = :refund_exchange_information,
                seller_status_id            = :seller_status_id,
                brand_name_korean           = :brand_name_korean,
                brand_name_english          = :brand_name_english,
                brand_crm_number            = :brand_crm_number,
                seller_property_id          = :seller_property_id
            WHERE
                id = :id
        """), seller).rowcount

        # update 성공하면 해당하는 row 의 수 반환 실패하면 0 반환
        if update_row == 0:
            raise NoAffectedRowException(500, 'update_seller_information seller update error')
