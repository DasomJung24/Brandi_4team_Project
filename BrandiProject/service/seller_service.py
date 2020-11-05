import jwt
import bcrypt
from datetime import datetime, timedelta
from flask import current_app
from slack import WebClient
from slack.errors import SlackApiError
from config import slack_channel, status, action_button


class SellerService:
    def __init__(self, seller_dao, config):
        self.seller_dao = seller_dao
        self.config = config

    def create_new_seller(self, new_seller, session):
        """ 셀러 회원가입

        Args:
            new_seller: 회원가입에 필요한 셀러 정보
            session: db 연결

        Returns:
            new_seller_id : 회원가입 성공
            already exist : 같은 계정이 존재할 때

        """
        seller = self.seller_dao.get_seller_data(new_seller['account'], session)

        # 아이디가 존재하면 None 리턴
        if seller is not None:
            return 'already exist'

        new_seller['password'] = bcrypt.hashpw(new_seller['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        new_seller_id = self.seller_dao.insert_seller(new_seller, session)

        return new_seller_id

    def enter_login(self, seller, session):
        """ 셀러 로그인

        Args:
            seller: 셀러의 계정과 비밀번호
            session: db 연결

        Returns:
            access token    : 로그인 성공시 발행
            not exist       : 계정이 존재하지 않을 때
            not authorized  : 셀러의 상태가 입점 대기 상태 일 때
            wrong password  : 비밀번호가 틀렸을 때
            deleted account : 소프트 딜리트 된 계정일 때

        """
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
        if seller_data['is_delete'] == 1:
            return 'deleted account'

        expire = datetime.utcnow() + timedelta(hours=24)
        access_token = jwt.encode({'seller_id': seller_data['id'], 'exp': expire},
                                  current_app.config['JWT_SECRET_KEY'], current_app.config['ALGORITHM'])
        
        return access_token.decode('utf-8')

    def get_my_page(self, seller_id, session):
        """ 셀러 정보 관리 데이터 불러오기

        Args:
            seller_id : 셀러 id
            session   : db 연결

        Returns:
            seller_data : 데이터베이스에 저장된 셀러의 정보

        """
        # 셀러상세페이지에 등록된 셀러 데이터 불러오기
        seller = self.seller_dao.get_seller_information(seller_id, session)
        manager = self.seller_dao.get_manager_information(seller_id, session)
        seller_status_histories = self.seller_dao.get_seller_status_histories(seller_id, session)

        seller_data = {
            'id':                           seller['id'],
            'image':                        seller['image'],
            'background_image':             seller['background_image'],
            'simple_introduce':             seller['simple_introduce'],
            'detail_introduce':             seller['detail_introduce'],
            'brand_crm_open':               seller['brand_crm_open'],
            'brand_crm_end':                seller['brand_crm_end'],
            'is_brand_crm_holiday':         seller['is_brand_crm_holiday'],
            'zip_code':                     seller['zip_code'],
            'address':                      seller['address'],
            'detail_address':               seller['detail_address'],
            'delivery_information':         seller['delivery_information'],
            'refund_exchange_information':  seller['refund_exchange_information'],
            'seller_status_id':             seller['seller_status_id'],
            'brand_name_korean':            seller['brand_name_korean'],
            'brand_name_english':           seller['brand_name_english'],
            'account':                      seller['account'],
            'brand_crm_number':             seller['brand_crm_number'],
            'manager_information':          [dict(row) for row in manager]
        }

        status_histories = []

        # 셀러 상태 변경 히스토리는 1개 이상이기 때문에 배열로 받아옴
        for history in seller_status_histories:
            seller_status = {
                'seller_status_id': history['seller_status_id'],
                'update_time':      history['update_time'].strftime('%Y-%m-%d %H:%M:%S')
            }
            status_histories.append(seller_status)

        seller_data['status_histories'] = status_histories

        return seller_data

    def post_my_page(self, seller_data, session):
        """ 셀러 정보 관리 업데이트 하기

        Args:
            seller_data : 업데이트할 셀러의 데이터
            session     : db 연결

        Returns:

        """
        # 셀러상세페이지 셀러의 정보 데이터베이스에 넣기
        manager_information = seller_data['manager_information']

        self.seller_dao.update_seller_information(seller_data, session)

        ordering = 1
        for manager in manager_information:
            manager['ordering'] = ordering
            manager['seller_id'] = seller_data['id']
            self.seller_dao.update_manager_information(manager, session)
            ordering += 1

    def get_seller_list(self, query_string_list, seller_id, session):
        """ 마스터가 셀러 리스트 불러오기

        Args:
            query_string_list : 필터링 조건 리스트
            seller_id         : 셀러 id
            session           : db 연결

        Returns:
            seller_list    : 필터링된 셀러 리스트
            not authorized : 마스터 계정이 아닐 때

        """
        # 셀러 아이디를 이용해 마스터인지 아닌지 체크하기
        is_master = self.seller_dao.is_master(seller_id, session)

        # 마스터 계정이 아닐 때 에러 발생
        if is_master['is_master'] == 0:
            return 'not authorized'

        seller_list = self.seller_dao.select_seller_list(query_string_list, session)

        seller = seller_list['seller_list']

        for seller_data in seller:
            seller_data['created_at'] = seller_data['created_at'].strftime('%Y-%m-%d %H:%M:%S')

        return seller_list

    def post_seller_status(self, seller_id, button, session):
        """ 마스터의 셀러 계정관리 - 셀러 status 변경

        Args:
            seller_id : 셀러 id
            button    : 셀러의 상태를 변경하는 버튼
            session   : db 연결

        Returns:
            invalid request : 버튼과 버튼이 눌리는 셀러의 상태가 맞지 않을 때
            message fail    : 슬랙봇 메세지 전송이 실패되었을 때


        status - 입점대기:1 입점:2 휴점:3 퇴점대기:4 퇴점:5 입점거절:6
        button - 입점거절:1 입점승인:2 휴점처리:3 휴점해제:4 퇴점대기:5 퇴점철회:6 퇴점확정:7
        """

        # 셀러의 상태 체크하기
        seller_status = self.seller_dao.get_status_id(seller_id, session)

        # 슬랙 api 토큰을 실행할 웹클라이언트를 변수에 저장
        client = WebClient(token=current_app.config['SLACK_API_TOKEN'])

        # 입점승인, 퇴점철회, 휴점해제 버튼이 눌린 셀러의 상태가 입점이면 에러 발생
        if button == action_button['STORE_BUTTON'] or \
                button == action_button['CANCELED_CLOSED_BUTTON'] or \
                button == action_button['CANCELED_TEMP_CLOSED_BUTTON']:
            if seller_status['seller_status_id'] == status['STORE']:
                return 'invalid request'

            self.seller_dao.status_change_store(seller_id, session)

            try:
                client.chat_postMessage(
                    channel=slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 입점으로 변경되었습니다.'
                )
            except SlackApiError:
                return 'message fail'

        # 퇴점대기 버튼이 눌린 셀러의 상태가  입점대기, 퇴점대기이면 에러 발생
        if button == action_button['CLOSED_WAIT_BUTTON']:
            if seller_status['seller_status_id'] == status['STORE_WAIT'] or\
                    seller_status['seller_status_id'] == status['CLOSED_WAIT']:
                return 'invalid request'

            self.seller_dao.status_change_closed_wait(seller_id, session)

            try:
                client.chat_postMessage(
                    channel=slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 퇴점대기로 변경되었습니다.'
                )
            except SlackApiError:
                return 'message fail'

        # 휴점처리 버튼이 눌린 셀러의 상태가 입점대기, 휴점이면 에러 발생
        if button == action_button['TEMP_CLOSED_BUTTON']:
            if seller_status['seller_status_id'] == status['STORE_WAIT'] or \
                    seller_status['seller_status_id'] == status['TEMP_CLOSED']:
                return 'invalid request'

            self.seller_dao.status_change_temporarily_closed(seller_id, session)

            try:
                client.chat_postMessage(
                    channel=slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 휴점으로 변경되었습니다.'
                )
            except SlackApiError:
                return 'message fail'

        # 입점거절 버튼이 눌린 셀러의 상태가 입점대기가 아니면 에러 발생
        if button == action_button['REFUSE_STORE_BUTTON']:
            if seller_status['seller_status_id'] != status['STORE_WAIT']:
                return 'invalid request'

            self.seller_dao.status_change_refused_store(seller_id, session)

            try:
                client.chat_postMessage(
                    channel=slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 입점거절로 변경되었습니다.'
                )
            except SlackApiError:
                return 'message fail'

        # 퇴점확정 버튼이 눌린 셀러의 상태가 퇴점대기가 아니라면 에러 발생
        if button == action_button['CONFIRM_CLOSED_BUTTON']:
            if seller_status['seller_status_id'] != status['CLOSED_WAIT']:
                return 'invalid request'

            self.seller_dao.status_change_closed_store(seller_id, session)

            try:
                client.chat_postMessage(
                    channel=slack_channel['CHANNEL'],
                    text=f'id {seller_id}번 셀러의 상태가 퇴점으로 변경되었습니다.'
                )
            except SlackApiError:
                return 'message fail'

    def get_home_data(self, seller_id, session):
        """ 홈 (셀러) 데이터 가져오기

        Args:
            seller_id : 셀러 id
            session   : db 연결

        Returns:
            home_data : 홈(셀러) 데이터 정보

        """
        # 한달 전 날짜 구하기
        date = datetime.now()-timedelta(days=30)
        date = date.strftime('%Y%m%d')

        home_data = self.seller_dao.select_home_data(seller_id, date, session)

        return home_data

    def get_seller_page(self, seller_id, session):
        """ 셀러계정관리(마스터) - 셀러의 데이터 가져오기

        Args:
            seller_id : 셀러 id
            session   : db 연결

        Returns:
            seller_data    : 셀러의 데이터
            not authorized : 마스터 계정이 아닐 때

        """
        # 마스터 계정인지 체크하기
        is_master = self.seller_dao.is_master(seller_id, session)

        # 마스터 계정이 아닐 때 에러 발생
        if is_master['is_master'] == 0:
            return 'not authorized'

        seller = self.seller_dao.get_seller_information(seller_id, session)
        manager = self.seller_dao.get_manager_information(seller_id, session)
        seller_status_histories = self.seller_dao.get_seller_status_histories(seller_id, session)

        seller_data = {
            'id':                           seller['id'],
            'image':                        seller['image'],
            'background_image':             seller['background_image'],
            'simple_introduce':             seller['simple_introduce'],
            'detail_introduce':             seller['detail_introduce'],
            'brand_crm_open':               seller['brand_crm_open'],
            'brand_crm_end':                seller['brand_crm_end'],
            'is_brand_crm_holiday':         seller['is_brand_crm_holiday'],
            'zip_code':                     seller['zip_code'],
            'address':                      seller['address'],
            'detail_address':               seller['detail_address'],
            'delivery_information':         seller['delivery_information'],
            'refund_exchange_information':  seller['refund_exchange_information'],
            'seller_status_id':             seller['seller_status_id'],
            'brand_name_korean':            seller['brand_name_korean'],
            'brand_name_english':           seller['brand_name_english'],
            'seller_property_id':           seller['seller_property_id'],
            'account':                      seller['account'],
            'brand_crm_number':             seller['brand_crm_number'],
            'manager_information':          [dict(row) for row in manager]
        }

        status_histories = []

        # 셀러 상태 변경 히스토리는 1개 이상이기 때문에 배열로 받아옴
        for history in seller_status_histories:
            seller_status = {
                'account':          seller['account'],
                'seller_status_id': history['seller_status_id'],
                'update_time':      history['update_time'].strftime('%Y-%m-%d %H:%M:%S')
            }
            status_histories.append(seller_status)

        seller_data['status_histories'] = status_histories

        return seller_data

    def put_master_seller_page(self, seller_data, session):
        """ 셀러계정관리 (마스터) - 셀러 정보 업데이트 할 때

        Args:
            seller_data : 셀러의 정보
            session     : db 연결

        Returns:

        """
        manager_information = seller_data['manager_information']

        # 셀러 정보 업데이트 하기
        self.seller_dao.update_seller_information_master(seller_data, session)

        ordering = 1
        for manager in manager_information:
            manager['ordering'] = ordering
            manager['seller_id'] = seller_data['id']
            ordering += 1

        # 담당자 정보 업데이트 하기
        self.seller_dao.update_manager_information(manager_information, seller_data['id'], session)