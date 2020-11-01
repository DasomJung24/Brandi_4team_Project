from sqlalchemy import text
from exceptions import NoAffectedRowException, NoDataException


class ProductDao:

    def select_category_list(self, session):
        category_list = session.execute(text("""
            SELECT 
                id, 
                name
            FROM categories
        """)).fetchall()

        return category_list

    def select_color_list(self, session):
        color_list = session.execute(text("""
                    SELECT 
                        id, 
                        name
                    FROM colors
                """)).fetchall()

        return color_list

    def select_size_list(self, session):
        size_list = session.execute(text("""
                    SELECT 
                        id, 
                        name
                    FROM sizes
                """)).fetchall()

        return size_list

    def select_sub_categories(self, category_id, session):
        # 1차 카테고리 아이디로 2차 카테고리 목록 불러오기
        sub_list = session.execute(text("""
            SELECT
                id,
                name
            FROM sub_categories
            WHERE
                categories_id = :categories_id
        """), {'categories_id': category_id}).fetchall()

        return {'sub_category_list': [dict(row) for row in sub_list]}

    def insert_product_data(self, product_data, session):
        # 상품 등록하기
        product_id = session.execute(text("""
            INSERT INTO products (
                name,
                seller_id,
                is_sell,
                is_display,
                is_discount,
                sub_categories_id,
                price,
                discount_rate,
                discount_start_date,
                discount_end_date,
                simple_information,
                main_image,
                detail,
                minimum_sell_count,
                maximum_sell_count,
                manufacturer,
                manufacture_date,
                origin
            ) VALUES (
                :name,
                :seller_id,
                :is_sell,
                :is_display,
                :is_discount,
                :sub_categories_id,
                :price,
                :discount_rate,
                :discount_start_date,
                :discount_end_date,
                :simple_information,
                :main_image,
                :detail,
                :minimum_sell_count,
                :maximum_sell_count,
                :manufacturer,
                :manufacture_date,
                :origin
            )
        """), product_data).lastrowid

        if product_id is None:
            raise NoAffectedRowException(500, 'insert_product_data insert error')

        # 등록한 상품 Id 를 받아서 그 상품의 code_number 등록하기
        code = session.execute(text("""
            UPDATE 
                products
            SET
                code_number = :code_number
            WHERE 
                id = :product_id
        """), {'code_number': int(product_id)*100, 'product_id': product_id}).rowcount

        if code == 0:
            raise NoAffectedRowException(500, 'insert_product_data code number update error')

        # 상품 등록 이력관리
        record = session.execute(text("""
               INSERT INTO product_records (
                   seller_id,
                   product_id,
                   product_name,
                   price,
                   discount_rate,
                   start_time,
                   close_time,
                   main_image
               ) VALUES (
                   :seller_id,
                   :product_id,
                   :name,
                   :price,
                   :discount_rate,
                   now(),
                   :close_time,
                   :main_image
               )
           """), {'seller_id': product_data['seller_id'], 'product_id': product_id, 'name': product_data['name'],
                  'price': product_data['price'], 'discount_rate': product_data['discount_rate'],
                  'main_image': product_data['main_image'], 'close_time': product_data['close_time']}).rowcount

        if record == 0:
            raise NoAffectedRowException(500, 'insert_product_data record insert error')

        return product_id

    # 옵션 데이터 등록하기
    def insert_data_option(self, option, session):
        option = session.execute(text("""
            INSERT INTO options (
                product_id,
                color_id,
                size_id,
                is_inventory_manage,
                count,
                ordering
            ) VALUES (
                :product_id,
                :color_id,
                :size_id,
                :is_inventory_manage,
                :count,
                :ordering
            )
        """), option).rowcount

        if option == 0:
            raise NoAffectedRowException(500, 'insert_data_option insert error')

    # 서브 이미지 등록하기
    def insert_data_sub_image(self, image, session):
        image = session.execute(text("""
            INSERT INTO sub_images (
                image,
                product_id
            ) VALUES (
                :image,
                :product_id
            )
        """), image).rowcount

        if image == 0:
            raise NoAffectedRowException(500, 'insert_data_sub_image insert error')

    # 상품 데이터 가져오기
    def select_product_data(self, product_id, session):
        product_data = session.execute(text("""
            SELECT
                *
            FROM products
            WHERE
                id = :id
        """), {'id': product_id}).fetchone()

        if product_data is None:
            raise NoDataException(500, 'select_product_data select error')

        return product_data

    # 상품의 옵션 정보 가져오기
    def select_product_options(self, product_id, session):
        options = session.execute(text("""
            SELECT
                *
            FROM options
            WHERE
                product_id = :product_id
        """), {'product_id': product_id}).fetchall()

        if options is None:
            raise NoDataException(500, 'select_product_options select error')

        return options

    # 상품의 이미지 리스트 가져오기
    def select_product_images(self, product_id, session):
        images = session.execute(text("""
            SELECT
                *
            FROM sub_images
            WHERE
                product_id = :product_id
        """), {'product_id': product_id}).fetchall()

        return images

    # 상품데이터 업데이트하기
    def update_product_data(self, product_data, session):
        product = session.execute(text("""
            UPDATE
                products
            SET
                name                = :name,
                seller_id           = :seller_id,
                is_sell             = :is_sell,
                is_display          = :is_display,
                is_discount         = :is_discount,
                sub_categories_id   = :sub_categories_id,
                price               = :price,
                discount_rate       = :discount_rate,
                discount_start_date = :discount_start_date,
                discount_end_date   = :discount_end_date,
                simple_information  = :simple_information,
                main_image          = :main_image,
                detail              = :detail,
                minimum_sell_count  = :minimum_sell_count,
                maximum_sell_count  = :maximum_sell_count,
                manufacturer        = :manufacturer,
                manufacture_date    = :manufacture_date,
                origin              = :origin
            WHERE 
                id = :product_id
            """), product_data).rowcount

        if product == 0:
            raise NoAffectedRowException(500, 'update_product_data update error')

        # 상품 이력관리
        product_record = session.execute(text("""
            INSERT INTO product_records (
                seller_id,
                product_id,
                product_name,
                price,
                discount_rate,
                start_time,
                close_time,
                main_image
            ) VALUES (
                :seller_id,
                :product_id,
                :name,
                :price,
                :discount_rate,
                now(),
                :close_time,
                :main_image
            )
        """), product_data).rowcount

        if product_record == 0:
            raise NoAffectedRowException(500, 'update_product_data record insert error')

        # 바로 전 이력 close_time 현재 시간으로 수정하기
        update_prerecord = session.execute(text("""
            UPDATE
                product_records
            SET 
                close_time = now()
            WHERE
                product_id = :product_id
            AND
                close_time = :close_time
        """), product_data).rowcount

        if update_prerecord == 0:
            raise NoAffectedRowException(500, 'update_product_data pre-record update error')

    def update_option(self, options, session):
        delete_option = session.execute(text("""
            DELETE FROM 
                options
            WHERE
                product_id = :product_id
        """), {'product_id': options[0]['product_id']}).rowcount

        if delete_option == 0:
            raise NoAffectedRowException(500, 'update_option delete error')

        for idx, option in enumerate(options):
            insert_option = session.execute(text("""
                INSERT INTO options (
                    product_id,
                    color_id,
                    size_id,
                    is_inventory_manage,
                    count,
                    ordering
                ) VALUES (
                    :product_id,
                    :color_id,
                    :size_id,
                    :is_inventory_manage,
                    :count,
                    :ordering
                )
            """), {'product_id': option['product_id'], 'color_id': option['color_id'],
                   'size_id': option['size_id'], 'is_inventory_manage': option['is_inventory_manage'],
                   'count': option['count'], 'ordering': idx+1}).rowcount

            if insert_option == 0:
                raise NoAffectedRowException(500, 'update_option insert error')

    def update_sub_image(self, image_list, session):
        image_data = session.execute(text("""
            SELECT 
                *
            FROM sub_images
            WHERE
                product_id = :product_id
        """), {'product_id': image_list[0]['product_id']}).fetchall()

        if image_data is not None:
            delete_row = session.execute(text("""
                DELETE FROM 
                    sub_images
                WHERE
                    product_id = :product_id
            """), {'product_id': image_list[0]['product_id']}).rowcount

            if delete_row == 0:
                raise NoAffectedRowException(500, 'update_sub_image delete error')

        for image in image_list:
            insert_image = session.execute(text("""
                INSERT INTO sub_images (
                    image,
                    product_id
                ) VALUES (
                    :image,
                    :product_id
                )
            """), image).rowcount

            if insert_image == 0:
                raise NoAffectedRowException(500, 'update_sub_image insert error')

    # 셀러가 자신의 등록 상품들을 가져오기
    def select_product_list(self, query_string_list, session):
        sql = """
            SELECT
                id,
                created_at,
                main_image,
                name,
                code_number,
                price,
                discount_rate,
                is_sell,
                is_display,
                is_discount
            FROM products
            WHERE
                seller_id = :seller_id """

        if query_string_list['is_sell']:
            sql += """
            AND
                is_sell = :is_sell """

        if query_string_list['is_discount']:
            sql += """
            AND
                is_discount = :is_discount """

        if query_string_list['is_display']:
            sql += """
            AND
                is_display = :is_display """

        if query_string_list['name']:
            sql += """
            AND
                name = :name """

        if query_string_list['code_number']:
            sql += """
            AND 
                code_number = :code_number """

        if query_string_list['start_date']:
            sql += """
            AND
                created_at > :start_date """

        if query_string_list['end_date']:
            sql += """
            AND
                created_at < :end_date """

        total_count = len(session.execute(text(sql), query_string_list).fetchall())

        sql += """
            LIMIT :limit
            OFFSET :offset
        """

        product_list = session.execute(text(sql), query_string_list).fetchall()

        return {'product_list': [dict(row) for row in product_list], 'total_count': total_count}
