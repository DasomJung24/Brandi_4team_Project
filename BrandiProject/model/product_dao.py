from sqlalchemy import text

class ProductDao:
    def __init__(self, database):
        self.db = database

    def insert_product_data(self, product_data):
        row = self.db.execute(text("""
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
        # code_number 업데이트
        code = self.db.execute(text("""
            UPDATE 
                products
            SET
                code_number = :code_number
            WHERE 
                id = :product_id
        """), {'code_number':int(row)*100, 'product_id':row})

        if code is None: return 'error'
       
        for option in product_data['options']:
            option_id = self.db.execute(text("""
                INSERT INTO options (
                    product_id,
                    color_id,
                    size_id,
                    is_inventory_manage,
                    count
                ) VALUES (
                    :product_id,
                    :color_id,
                    :size_id,
                    :is_inventory_manage,
                    :count
                )
            """), {
                    'product_id'          : row,
                    'color_id'            : option['color_id'],
                    'size_id'             : option['size_id'],
                    'is_inventory_manage' : option['is_inventory_manage'],
                    'count'               : option['count']}).lastrowid

            op = self.db.execute(text("""
                UPDATE
                    options
                SET
                    product_number = :product_number
                WHERE
                    id = :id
            """), {'id':option_id, 'product_number':int(option_id)*50})

            if op is None: return 'error'
        
        if product_data['image_list'] is not None:
            for image in product_data['image_list']:
                self.db.execute(text("""
                    INSERT INTO sub_images (
                        image,
                        product_id
                    ) VALUES (
                        :image,
                        :product_id
                    )
                """), {'product_id':row, 'image':image})     
        # 이력관리
        record = self.db.execute(text("""
            INSERT INTO product_records (
                seller_id,
                product_id,
                product_name,
                price,
                discount_rate,
                start_time,
                main_image
            ) VALUES (
                :seller_id,
                :product_id,
                :name,
                :price,
                :discount_rate,
                now(),
                :main_image
            )
        """), {'seller_id'      : product_data['seller_id'],
                'product_id'    : row,
                'name'          : product_data['name'],
                'price'         : product_data['price'],
                'discount_rate' : product_data['discount_rate'],
                'main_image'    : product_data['main_image']})
        
        if record is None: return 'error'

        return row if row else None

    def select_product_data(self, product_id):
        data = self.db.execute(text("""
            SELECT
                *
            FROM
                products
            WHERE
                id = :id
        """), {'id':product_id}).fetchone()

        options = self.db.execute(text("""
            SELECT
                *
            FROM
                options
            WHERE
                product_id = :product_id
        """), {'product_id':product_id}).fetchall()

        images = self.db.execute(text("""
            SELECT
                *
            FROM
                sub_images
            WHERE
                product_id = :product_id
        """), {'product_id':product_id}).fetchall()

        return {'product_data':data, 'options':[dict(row) for row in options], 'images':[dict(row) for row in images]} if data is not None else None

    def update_product_data(self, product_data):
        row = self.db.execute(text("""
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
            """), product_data)
        #이력관리
        self.db.execute(text("""
            INSERT INTO product_records (
                seller_id,
                product_id,
                product_name,
                price,
                discount_rate,
                start_time,
                main_image
            ) VALUES (
                :seller_id,
                :product_id,
                :name,
                :price,
                :discount_rate,
                now(),
                :main_image
            )
        """), product_data)

        records = self.db.execute(text("""
            SELECT
                id
            FROM 
                product_records
            WHERE
                product_id = :product_id
        """), product_data).fetchall()

        self.db.execute(text("""
            UPDATE 
                product_records
            SET
                close_time = now()
            WHERE
                id = :id
        """), {'id':records[-2]['id']})

        self.db.execute(text("""
            DELETE FROM 
                options
            WHERE
                product_id = :product_id
        """), product_data)

        for option in product_data['options']:
            self.db.execute(text("""
                INSERT INTO options (
                    product_id,
                    color_id,
                    size_id,
                    is_inventory_manage,
                    count
                ) VALUES (
                    :product_id,
                    :color_id,
                    :size_id,
                    :is_inventory_manage,
                    :count
                )
            """), {
                    'product_id'          : product_data['product_id'],
                    'color_id'            : option['color_id'],
                    'size_id'             : option['size_id'],
                    'is_inventory_manage' : option['is_inventory_manage'],
                    'count'               : option['count']})
        
        self.db.execute(text("""
            DELETE FROM 
                sub_images
            WHERE
                product_id = :product_id
        """), product_data)

        if product_data['image_list'] is not None:
            for image in product_data['image_list']:
                self.db.execute(text("""
                    INSERT INTO sub_images (
                        image,
                        product_id
                    ) VALUES (
                        :image,
                        :product_id
                    )
                """), {'product_id':product_data['product_id'], 'image':image})

        return row if row else None

    def select_product_list(self, seller_id):
        return self.db.execute(text("""
            SELECT 
                *
            FROM
                products a
            JOIN
                (
                    SELECT 
                        product_id, 
                        max(product_number) 
                    FROM 
                        options 
                    GROUP BY 
                        product_id
                )b
            ON 
                a.id = b.product_id
            WHERE
                a.seller_id = :seller_id 
        """), {'seller_id':seller_id}).fetchall()