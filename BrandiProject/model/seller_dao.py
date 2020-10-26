from sqlalchemy import text

class SellerDao:
    def __init__(self, database):
        self.db = database

    def insert_seller(self, seller):
        row_id = self.db.execute(text("""
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
        
        self.db.execute(text("""
            INSERT INTO manager_infomations (
                phone_number,
                seller_id
            ) VALUES (
                :phone_number,
                :seller_id
            )
        """), {'seller_id':row_id, 'phone_number':seller['phone_number']})
        
        self.db.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                1,
                :seller_id
            )
        """), {'seller_id':row_id})
        
        return row_id if row_id else None

    def get_seller_data(self, account):
        row = self.db.execute(text("""
            SELECT
                id,
                account,
                password,
                is_delete
            FROM sellers
            WHERE account = :account
        """), {'account' : account}).fetchone()

        return row if row else None

    def get_seller_information(self, seller_id):
        seller = self.db.execute(text("""
            SELECT
                a.id,
                a.seller_status_id,
                a.brand_name_korean,
                a.brand_name_english,
                a.account,
                a.brand_crm_number,
                b.phone_number
            FROM sellers a
            INNER JOIN manager_infomations b
            ON a.id = b.seller_id
            WHERE a.id = :id
        """), {'id':seller_id}).fetchone()
        
        seller_status = self.db.execute(text("""
            SELECT
                seller_status_id,
                update_time
            FROM seller_status_histories
            WHERE seller_id = :id
        """), {'id':seller_id}).fetchall()
        
        return {'seller':seller, 'seller_status':[dict(row) for row in seller_status]}    
    
    # def post_seller_information(self, seller_data, seller_id):   # 셀러정보관리 페이지 update
    #     self.db.execute(text("""
    #         UPDATE 
    #             manager_infomations
    #         SET 
    #             name = :name,
    #             phone_number = :phone_number,
    #             email = :email,
    #         WHERE seller_id = :seller_id
    #     """), {'seller_id', seller_id,
    #             'name':seller_data})
    #     return self.db.execute(text("""
    #     """))
    def is_master(self, seller_id):
        return self.db.execute(text("""
            SELECT
                is_master
            FROM sellers
            WHERE id = :id
        """), {'id':seller_id}).fetchone()

    def get_seller_list(self):
        return self.db.execute(text("""
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
            LEFT JOIN manager_infomations b 
            ON a.id = b.seller_id
        """)).fetchall()

    def status_change_two(self, seller_id):
        row = self.db.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 2
            WHERE
                id = :id
            """), {'id':seller_id})
        
        self.db.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                2,
                :seller_id
            )
        """), {'seller_id':seller_id})

        return row if row else None
        

    def status_change_four(self, seller_id):
        row = self.db.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 4
            WHERE
                id = :id
            """), {'id':seller_id})

        self.db.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                4,
                :seller_id
            )
        """), {'seller_id':seller_id})

        return row if row else None
        
    def status_change_three(self, seller_id):
        row = self.db.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 3
            WHERE
                id = :id
            """), {'id':seller_id})
            
        self.db.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                3,
                :seller_id
            )
        """), {'seller_id':seller_id})

        return row if row else None
        
    def status_change_six(self, seller_id):
        row = self.db.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 6,
                is_delete = True
            WHERE
                id = :id
            """), {'id':seller_id})

        self.db.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                6,
                :seller_id
            )
        """), {'seller_id':seller_id})

        return row if row else None
        
    def status_change_five(self, seller_id):
        row = self.db.execute(text("""
            UPDATE
                sellers
            SET 
                seller_status_id = 5,
                is_delete = True
            WHERE
                id = :id
            """), {'id':seller_id})

        self.db.execute(text("""
            INSERT INTO seller_status_histories (
                update_time,
                seller_status_id,
                seller_id
            ) VALUES (
                now(),
                5,
                :seller_id
            )
        """), {'seller_id':seller_id})

        return row if row else None  

    def get_status_id(self, seller_id):
        return self.db.execute(text("""
            SELECT
                seller_status_id
            FROM sellers
            WHERE 
                id = :id
            """), {'id':seller_id}).fetchone()