import jwt
import bcrypt
import re
from datetime     import datetime, timedelta
from flask        import current_app
from slack        import WebClient
from slack.errors import SlackApiError

class SellerService:
    def __init__(self, seller_dao, config):
        self.seller_dao = seller_dao
        self.config     = config

    def create_new_seller(self, new_seller):
        try:
            seller = self.seller_dao.get_seller_data(new_seller['account'])

            if seller is not None:  # 아이디가 존재하면 None 리턴
                return 'already exist'

            if new_seller['account'] is None or new_seller['password'] is None or new_seller['brand_name_korean'] is None or \
                new_seller['brand_name_english'] is None or new_seller['brand_crm_number'] is None or new_seller['seller_property_id'] is None or \
                new_seller['phone_number'] is None:
                return 'invalid request'
            
            if len(new_seller['account']) < 5:
                return 'short account'

            if re.search((r'^(?=.*[0-9])(?=.*[A-Za-z])(?=.*[^a-zA-Z0-9]).{8,20}$'), new_seller['password']) is None:
                return 'invalid password' 
        except KeyError:
            return 'key error'
        
        new_seller['password'] = bcrypt.hashpw(new_seller['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_seller_id          = self.seller_dao.insert_seller(new_seller)

        return new_seller_id

    def login(self, seller):
        try:
            seller_account = seller['account']
            seller_data    = self.seller_dao.get_seller_data(seller_account)
            
            if seller_data is None:
                return 'not exist'

            if seller_data['seller_status_id'] == 1:
                return 'not authorized'

            if not bcrypt.checkpw(seller['password'].encode('utf-8'), seller_data['password'].encode('utf-8')):
                return 'wrong password'

            if seller_data['is_delete'] == True:
                return 'deleted account'
        except KeyError:
            return 'key error'

        expire       = datetime.utcnow() + timedelta(hours=24)
        access_token = jwt.encode({'seller_id':seller_data['id'], 'exp':expire}, current_app.config['JWT_SECRET_KEY'], current_app.config['ALGORITHM'])
        
        return access_token.decode('utf-8')

    def get_my_page(self, seller_id):   # 셀러정보관리(셀러)
        seller = self.seller_dao.get_seller_information(seller_id)
        for history in seller['status_histories']:
            history['update_time'] = history['update_time'].strftime(('%Y-%m-%d %H:%M:%S'))

        return seller
    
    def post_my_page(self, seller_data, seller_id):  # 아직 미완성
        seller = seller_data['seller']

        if seller['image'] is None or seller['simple_introduce'] is None or seller['brand_crm_number'] is None or \
            seller['zip_code'] is None or seller['address'] is None or seller['detail_address'] is None or seller['brand_crm_open'] is None or \
            seller['brand_crm_end'] is None or seller['delivery_information'] is None or seller['refund_exchange_information'] is None:
            return None
        
        if seller_data['manager_information'] is None:
            return None

        for manager in seller_data['manager_information']:
            if manager['name'] is None or manager['phone_number'] is None or manager['email'] is None: 
                return None
        
        seller['id'] = seller_id
        manager_information = seller_data['manager_information']

        return self.seller_dao.update_seller_information(seller, manager_information)

    def get_seller_list(self, seller_id):   # 마스터 셀러 계정 관리 GET
        is_master = self.seller_dao.is_master(seller_id)
        
        if is_master['is_master'] == False:
            return 'not authorizated'
        
        seller_list = [dict(row) for row in self.seller_dao.get_seller_list()]
        
        for seller in seller_list:
            seller['created_at'] = seller['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            seller['number']     = seller['id'] * 33

        return seller_list

    def post_seller_status(self, seller_id, button):    # 마스터 셀러 계정관리 status 변경
        seller_status = self.seller_dao.get_status_id(seller_id)
        """
        status - 입점대기:1 입점:2 휴점:3 퇴점대기:4 퇴점:5 입점거절:6        
        입점거절:1 입점승인:2 휴점신청:3 휴점해제:4 퇴점철회:6 퇴점확정:7
        """
        client = WebClient(token=current_app.config['SLACK_API_TOKEN'])

        if button == '2' or button == '6' or button == '4':
            if seller_status['seller_status_id'] == '2':
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel = '#labs-위코드인턴십-6-4팀',
                    text    = f'id {seller_id}번 셀러의 상태가 입점으로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'

            return self.seller_dao.status_change_two(seller_id)
        
        if button == '5':
            if seller_status['seller_status_id'] == '1' or seller_status['seller_status_id'] == '4':
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel = '#labs-위코드인턴십-6-4팀',
                    text    = f'id {seller_id}번 셀러의 상태가 퇴점대기로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            return self.seller_dao.status_change_four(seller_id)

        if button == '3':
            if seller_status['seller_status_id'] == '1' or seller_status['seller_status_id'] == '3':
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel = '#labs-위코드인턴십-6-4팀',
                    text    = f'id {seller_id}번 셀러의 상태가 휴점으로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            return self.seller_dao.status_change_three(seller_id)

        if button == '1':
            if seller_status['seller_status_id'] != '1':
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel = '#labs-위코드인턴십-6-4팀',
                    text    = f'id {seller_id}번 셀러의 상태가 입점거절로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            return self.seller_dao.status_change_six(seller_id)
        
        if button == '7':
            if seller_status['seller_status_id'] != '4':
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel = '#labs-위코드인턴십-6-4팀',
                    text    = f'id {seller_id}번 셀러의 상태가 퇴점으로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            return self.seller_dao.status_change_five(seller_id)