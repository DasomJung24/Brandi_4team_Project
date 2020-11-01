import jwt
import bcrypt
import re
from datetime import datetime, timedelta
from flask import current_app
from slack import WebClient
from slack.errors import SlackApiError


class SellerService:
    def __init__(self, seller_dao, config):
        self.seller_dao = seller_dao
        self.config = config

    def create_new_seller(self, new_seller, session):
        seller = self.seller_dao.get_seller_data(new_seller['account'], session)

        # 아이디가 존재하면 None 리턴
        if seller is not None:
            return 'already exist'

        new_seller['password'] = bcrypt.hashpw(new_seller['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_seller_id = self.seller_dao.insert_seller(new_seller, session)

        return new_seller_id

    def enter_login(self, seller, session):
        try:
            seller_account = seller['account']
            # 셀러의 계정으로 데이터를 받아와서 계정이 있는지 확인
            seller_data = self.seller_dao.get_seller_data(seller_account, session)
            
            if seller_data is None:
                return 'not exist'

            # 셀러 상태가 입점대기일 때 에러 발생
            if seller_data['seller_status_id'] == 1:
                return 'not authorized'

            if not bcrypt.checkpw(seller['password'].encode('utf-8'), seller_data['password'].encode('utf-8')):
                return 'wrong password'

            # 소프트 딜리트된 계정일 때 에러 발생
            if seller_data['is_delete'] is True:
                return 'deleted account'

        except KeyError:
            return 'key error'

        expire = datetime.utcnow() + timedelta(hours=24)
        access_token = jwt.encode({'seller_id': seller_data['id'], 'exp': expire},
                                  current_app.config['JWT_SECRET_KEY'], current_app.config['ALGORITHM'])
        
        return access_token.decode('utf-8')

    def get_my_page(self, seller_id, session):
        # 셀러상세페이지에 등록된 셀러 데이터 불러오기
        seller = self.seller_dao.get_seller_information(seller_id, session)
        
        # 셀러 상태 변경 히스토리는 1개 이상이기 때문에 배열로 받아옴
        for history in seller['status_histories']:
            history['update_time'] = history['update_time'].strftime('%Y-%m-%d %H:%M:%S')

        return seller

    def post_my_page(self, seller_data, session):
        # 셀러상세페이지 셀러의 정보 데이터베이스에 넣기
        seller = seller_data['seller']
        manager_information = seller_data['manager_information']

        self.seller_dao.update_seller_information(seller, session)

        ordering = 1
        for manager in manager_information:
            manager['ordering'] = ordering
            manager['seller_id'] = seller['id']
            self.seller_dao.update_manager_information(manager, session)
            ordering += 1

    def get_seller_list(self, query_string_list, seller_id, session):
        # 마스터 셀러 계정 관리 가져오기
        is_master = self.seller_dao.is_master(seller_id, session)

        # 마스터 계정이 아닐 때 에러 발생
        if is_master['is_master'] is False:
            return 'not authorizated'

        seller_list = self.seller_dao.select_seller_list(query_string_list, session)

        seller = seller_list['seller_list']

        for seller_data in seller:
            seller_data['created_at'] = seller_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        return seller_list

    def post_seller_status(self, seller_id, button, session):
        # 마스터 셀러 계정관리 셀러 status 변경
        seller_status = self.seller_dao.get_status_id(seller_id, session)
        """
        status - 입점대기:1 입점:2 휴점:3 퇴점대기:4 퇴점:5 입점거절:6        
        button - 입점거절:1 입점승인:2 휴점처리:3 휴점해제:4 퇴점대기:5 퇴점철회:6 퇴점확정:7
        """
        client = WebClient(token=current_app.config['SLACK_API_TOKEN'])

        # 입점승인, 퇴점철회, 휴점해제 버튼이 눌린 셀러의 상태가 입점이면 에러 발생
        if button == current_app.config.action_button['STORE_BUTTON'] or \
                button == current_app.config.action_button['CANCELED_CLOSED_BUTTON'] or \
                button == current_app.config.action_button['CANCELED_TEMP_CLOSED_BUTTON']:
            if seller_status['seller_status_id'] == current_app.config.status['STORE']:
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel=current_app.config.slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 입점으로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'

            self.seller_dao.status_change_store(seller_id, session)

        # 퇴점대기 버튼이 눌린 셀러의 상태가  입점대기, 퇴점대기이면 에러 발생
        if button == current_app.config.action_button['CLOSED_WAIT_BUTTON']:
            if seller_status['seller_status_id'] == current_app.config.status['STORE_WAIT'] or\
                    seller_status['seller_status_id'] == current_app.config.status['CLOSED_WAIT']:
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel=current_app.config.slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 퇴점대기로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            self.seller_dao.status_change_closed_wait(seller_id, session)

        # 휴점처리 버튼이 눌린 셀러의 상태가 입점대기, 휴점이면 에러 발생
        if button == current_app.config.action_button['TEMP_CLOSED_BUTTON']:
            if seller_status['seller_status_id'] == current_app.config.status['STORE_WAIT'] or \
                    seller_status['seller_status_id'] == current_app.config.status['TEMP_CLOSED']:
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel=current_app.config.slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 휴점으로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            self.seller_dao.status_change_temporarily_closed(seller_id, session)

        # 입점거절 버튼이 눌린 셀러의 상태가 입점대기가 아니면 에러 발생
        if button == current_app.config.action_button['REFUSE_STORE_BUTTON']:
            if seller_status['seller_status_id'] != current_app.config.status['STORE_WAIT']:
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel=current_app.config.slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 입점거절로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            self.seller_dao.status_change_refused_store(seller_id, session)

        # 퇴점확정 버튼이 눌린 셀러의 상태가 퇴점대기가 아니라면 에러 발생
        if button == current_app.config.action_button['CONFIRM_CLOSED_BUTTON']:
            if seller_status['seller_status_id'] != current_app.config.status['CLOSED_WAIT']:
                return 'invalid request'
            
            try:
                client.chat_postMessage(
                    channel=current_app.config.slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 퇴점으로 변경되었습니다.',
                )
            except SlackApiError:
                return 'message fail'
            
            self.seller_dao.status_change_closed_store(seller_id, session)

    def get_home_data(self, seller_id, session):
        home_data = self.seller_dao.select_home_data(seller_id, session)

        return home_data
