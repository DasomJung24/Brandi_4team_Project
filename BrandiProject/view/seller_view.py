import jwt
import re
from flask import request, jsonify, g, current_app
from flask_request_validator import Param, Pattern, validate_params, JSON, MinLength, Enum, GET, PATH
from functools import wraps
from exceptions import NoAffectedRowException, NoDataException


# access_token decorator
def login_required(func):
    @wraps(func)
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decode(access_token, current_app.config['JWT_SECRET_KEY'], current_app.config['ALGORITHM'])
            except jwt.InvalidTokenError:
                payload = None 

            if payload is None: 
                return jsonify({'message': 'INVALID TOKEN'}), 400

            seller_id = payload['seller_id']
            g.seller_id = seller_id
        else:
            return jsonify({'message': 'NOT EXIST TOKEN'}), 401
        
        return func(*args, **kwargs)
    
    return decorated_function


def seller_endpoints(app, services, get_session):
    seller_service = services.seller_service

    @app.route("/signup", methods=['POST'])
    @validate_params(
        Param('brand_crm_number', JSON, str, rules=[Pattern(r'^[0-9]{2,3}-[0-9]{3,4}-[0-9]{4}$')]),
        Param('password', JSON, str, rules=[Pattern(r'^(?=.*[0-9])(?=.*[A-Za-z])(?=.*[^a-zA-Z0-9]).{8,20}$')]),
        Param('phone_number', JSON, str, rules=[Pattern(r'^010-[0-9]{3,4}-[0-9]{4}$')]),
        Param('account', JSON, str, rules=[MinLength(5)]),
        Param('brand_name_korean', JSON, str),
        Param('brand_name_english', JSON, str),
        Param('seller_property_id', JSON, str)
    )
    def sign_up(*args):
        """ 회원가입 API

        회원가입을 위한 정보를 Body 에 받음

        Args:
            *args:
                brand_crm_number   : 브랜드 고객센터 번호
                password           : 비밀번호
                phone_number       : 담당자 핸드폰 번호
                account            : 계정
                brand_name_korean  : 브랜드명 ( 한글 )
                brand_name_english : 브랜드명 ( 영어 )
                seller_property_id : 셀러 속성 id ( 로드샵, 마켓 등 )

        Returns:
            200 : success , 회원가입 성공 시
            400 : 같은 계정이 존재할 때, key error
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            new_seller = {
                'brand_crm_number':     args[0],
                'password':             args[1],
                'phone_number':         args[2],
                'account':              args[3],
                'brand_name_korean':    args[4],
                'brand_name_english':   args[5],
                'seller_property_id':   args[6]
            }

            new_seller = seller_service.create_new_seller(new_seller, session)

            # 같은 계정이 이미 존재할 때
            if new_seller == 'already exist':
                return jsonify({'message': 'account already exist'}), 400

            session.commit()
            return jsonify({'message': 'success'}), 200

        except KeyError:
            return jsonify({'message': 'key error'}), 400

        except NoAffectedRowException as e:
            session.rollback()
            return jsonify({'message': 'no affected row error {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/login", methods=['POST'])
    @validate_params(
        Param('account', JSON, str),
        Param('password', JSON, str)
    )
    def log_in(*args):
        """

        Args:
            *args:
                account  : 계정
                password : 비밀번호

        Returns:
            200 : 로그인 성공 하면 access token 발행
            400 : 계정이 존재하지 않을 때, 비밀번호가 틀렸을 때, soft delete 된 계정일 때,
                셀러의 상태가 입점 대기 상태일 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            seller = {
                'account': args[0],
                'password': args[1]
            }
            token = seller_service.enter_login(seller, session)

            # 계정이 존재하지 않을 때
            if token == 'not exist':
                return jsonify({'message': 'account not exist'}), 400

            # 비밀번호가 틀렸을 때
            if token == 'wrong password':
                return jsonify({'message': 'wrong password'}), 400

            # 소프트 딜리트 된 계정일 때
            if token == 'deleted account':
                return jsonify({'message': 'account deleted'}), 400

            # 셀러 상태가 입점 대기 일 때 ( seller_status_id = 1 )
            if token == 'not authorized':
                return jsonify({'message': 'not authorized'}), 400

            return jsonify({'access_token': token})

        except KeyError:
            return jsonify({'message': 'key error'}), 400

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/mypage", methods=['GET'])
    @login_required
    def get_my_page():
        """ 셀러정보관리(셀러)

        셀러가 셀러 정보 관리를 들어갔을 때 등록된 셀러의 데이터 가져오기

        Returns:
            200 : seller_data ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            seller_data = seller_service.get_my_page(g.seller_id, session)

            return jsonify(seller_data)

        except NoDataException as e:
            session.rollback()
            return jsonify({'message': 'no data {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/mypage", methods=['PUT'])
    @login_required
    @validate_params(
        Param('image', JSON, str),
        Param('simple_introduce', JSON, str),
        Param('brand_crm_number', JSON, str, rules=[Pattern(r'^[0-9]{2,3}-[0-9]{3,4}-[0-9]{4}$')]),
        Param('zip_code', JSON, int),
        Param('address', JSON, str),
        Param('detail_address', JSON, str),
        Param('brand_crm_open', JSON, str),
        Param('brand_crm_end', JSON, str),
        Param('delivery_information', JSON, str),
        Param('refund_exchange_information', JSON, str),
        Param('seller_status_id', JSON, int),
        Param('background_image', JSON, str, required=False),
        Param('detail_introduce', JSON, str, required=False),
        Param('is_brand_crm_holiday', JSON, int, rules=[Enum(0, 1)], required=False),
        Param('brand_name_korean', JSON, str),
        Param('brand_name_english', JSON, str),
        Param('manager_information', JSON, list)
    )
    def put_my_page(*args):
        """ 셀러 정보 관리 (셀러 )

        셀러의 정보를 Body 로 받아서 데이터에 업데이트하기

        Args:
            *args:
                image                       : 셀러 프로필 이미지
                simple_introduce            : 셀러 한줄 소개
                brand_crm_number            : 브랜드 고객센터 번호
                zip_code                    : 우편번호
                address                     : 주소
                detail_address              : 상세 주소
                brand_crm_open              : 고객센터 오픈시간
                brand_crm_end               : 고객센터 마감시간
                delivery_information        : 배송 정보
                refund_exchange_information : 교환/환불 정보
                seller_status_id            : 셀러 상태 id ( 입점, 입점대기 등 )
                background_image            : 셀러페이지 배경이미지
                detail_introduce            : 셀러 상세 소개
                is_brand_crm_holiday        : 고객센터 주말 및 공휴일 운영 여부
                brand_name_korean           : 브랜드명 ( 한글 )
                brand_name_english          : 브랜드명 ( 영어 )
                manager_information         : 담당자 정보 ( 이름, 핸드폰 번호, 이메일 )

        Returns:
            200 : success, 셀러 데이터 업데이트 성공 시
            400 : 담당자 정보 안에 이름, 핸드폰 번호, 이메일 중 하나라도 없을 때,
                담당자 이메일 형식 맞지 않을 때, 담당자 핸드폰 번호 형식 맞지 않을 때
            500 : Exception

        """
        # 입력한 셀러 정보 받아서 데이터베이스에 넣기
        session = None
        try:
            session = get_session()
            seller = {
                'image':                        args[0],
                'simple_introduce':             args[1],
                'brand_crm_number':             args[2],
                'zip_code':                     args[3],
                'address':                      args[4],
                'detail_address':               args[5],
                'brand_crm_open':               args[6],
                'brand_crm_end':                args[7],
                'delivery_information':         args[8],
                'refund_exchange_information':  args[9],
                'seller_status_id':             args[10],
                'background_image':             args[11],
                'detail_introduce':             args[12],
                'is_brand_crm_holiday':         args[13],
                'brand_name_korean':            args[14],
                'brand_name_english':           args[15],
                'manager_information':          args[16],
                'id':                           g.seller_id
            }

            for manager in seller['manager_information']:
                # 담당자 정보 안에 이름, 번호, 이메일이 없으면 에러 발생
                if manager['name'] is None or manager['phone_number'] is None or manager['email'] is None:
                    return jsonify({'message': 'no manager information data'}), 400

                # 이메일 형식이 맞지 않을 때 에러 발생
                if re.match(r'^([0-9a-zA-Z_-]+)@([0-9a-zA-Z_-]+)\.([0-9a-zA-Z_-]+)$', manager['email']) is None:
                    return jsonify({'message': 'invalid email'}), 400

                # 핸드폰 번호 형식이 맞지 않을 때 에러 발생
                if re.match(r'^010-[0-9]{3,4}-[0-9]{4}$', manager['phone_number']) is None:
                    return jsonify({'message': 'invalid phone number'}), 400

            seller_service.post_my_page(seller, session)

            session.commit()
            return jsonify({'message': 'success'}), 200

        except NoAffectedRowException as e:
            session.rollback()
            return jsonify({'message': 'no affected row error {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/master/management-seller", methods=['GET'])
    @login_required
    @validate_params(
        Param('limit', GET, int, required=False),
        Param('offset', GET, int, required=False),
        Param('number', GET, int, required=False),
        Param('account', GET, str, required=False),
        Param('brand_name_korean', GET, str, required=False),
        Param('brand_name_english', GET, str, required=False),
        Param('manager_name', GET, str, required=False),
        Param('manager_number', GET, str, rules=[Pattern(r'^010-[0-9]{3,4}-[0-9]{4}$')], required=False),
        Param('manager_email', GET, str, rules=[Pattern(r'^([0-9a-zA-Z_-]+)@([0-9a-zA-Z_-]+)\.([0-9a-zA-Z_-]+)$')],
              required=False),
        Param('status_id', GET, int, required=False),
        Param('property_id', GET, int, required=False),
        Param('start_date', GET, str, required=False),
        Param('end_date', GET, str, required=False)
    )
    def get_management_seller(*args):
        """ 셀러 계정 관리 ( 마스터 ) API

        쿼리 파라미터로 필터링 될 값을 받아서 필터링 한 후 리스트를 보내줌

        Args:
            *args:
                limit              : pagination 범위
                offset             : pagination 시작 번호
                number             : 셀러의 id
                account            : 셀러의 계정
                brand_name_korean  : 브랜드명 ( 한글 )
                brand_name_english : 브랜드명 ( 영어 )
                manager_name       : 담당자명
                manager_number     : 담당자 핸드폰 번호
                manager_email      : 담당자 이메일
                status_id          : 셀러의 상태 id ( 입점, 입점대기 등 )
                property_id        : 셀러의 속성 id ( 로드샵, 마켓 등 )
                start_date         : 해당 날짜 이후로 등록한 셀러 검색
                end_date           : 해당 날짜 이전에 등록한 셀러 검색

        Returns:
            200 : seller_list ( type : dict )
            400 : 마스터 계정이 아닌 경우
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            # 쿼리스트링을 딕셔너리로 만들어 줌
            query_string_list = {
                'limit':                10 if args[0] is None else args[0],
                'offset':               0 if args[1] is None else args[1],
                'number':               args[2],
                'account':              args[3],
                'brand_name_korean':    args[4],
                'brand_name_english':   args[5],
                'manager_name':         args[6],
                'manager_number':       args[7],
                'email':                args[8],
                'seller_status_id':     args[9],
                'seller_property_id':   args[10],
                'start_date':           args[11],
                'end_date':             args[12]
            }

            seller_list = seller_service.get_seller_list(query_string_list, g.seller_id, session)

            # 마스터 계정이 아닐 때 에러 발생
            if seller_list == 'not authorized':
                return jsonify({'message': 'no master'}), 400

            return jsonify(seller_list)

        except NoDataException as e:
            session.rollback()
            return jsonify({'message': 'no data {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/master/management-seller", methods=['PUT'])
    @login_required
    @validate_params(
        Param('seller_id', JSON, int),
        Param('button', JSON, int)
    )
    def put_management_seller(seller_id, button):
        """ 마스터 셀러계정관리 API

        마스터가 버튼을 눌러 셀러의 상태를 변경함
        셀러의 상태가 변경될 때마다 슬랙 채널로 "(seller_id)번 셀러의 상태가 (status)로 변경되었습니다" 라는 메세지 전송

        Args:
            seller_id: 셀러의 id
            button: 셀러의 상태 변경 버튼 ( 입점으로 변경, 휴점으로 변경 등 )

        Returns:
            200 : success, 셀러의 상태가 정상적으로 변경되었을 때
            400 : 눌린 버튼과 셀러의 상태가 맞지 않을 때, 슬랙봇 메세지가 전송 실패되었을 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            status = seller_service.post_seller_status(seller_id, button, session)

            # 버튼과 버튼이 눌리는 셀러의 속성이 맞지 않을 때
            if status == 'invalid request':
                return jsonify({'message': 'invalid request'}), 400

            # 슬랙봇 메세지가 전송실패되었을 때
            if status == 'message fail':
                return jsonify({'message': 'message failed'}), 400

            session.commit()
            return jsonify({'message': 'success'}), 200

        except NoAffectedRowException as e:
            session.rollback()
            return jsonify({'message': 'no affected row error {}'.format(e.message)}), e.status_code

        except NoDataException as e:
            session.rollback()
            return jsonify({'message': 'no data {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/home", methods=['GET'])
    @login_required
    def get_home_seller():
        """ 홈 API

        로그인했을 때 나오는 홈 화면의 데이터 보내주기

        Returns:
            200 : data ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            data = seller_service.get_home_data(session)

            return jsonify(data), 200

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/master/management-seller/<int:seller_id>", methods=['GET'])
    @login_required
    @validate_params(
        Param('seller_id', PATH, int)
    )
    def get_master_seller_page(seller_id):
        """ 셀러계정관리 ( 마스터 )

        마스터가 셀러의 데이터 가져오기

        Args:
            seller_id: 셀러 id

        Returns:
            200 : seller_data ( type : dict )
            400 : 마스터 계정이 아닐 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            seller_data = seller_service.get_seller_page(seller_id, session)

            # 마스터 계정이 아닐 때 에러 발생
            if seller_data == 'not authorized':
                return jsonify({'message': 'not authorized'}), 400

            return jsonify(seller_data)

        except NoDataException as e:
            session.rollback()
            return jsonify({'message': 'no data {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/master/management-seller/<int:seller_id>", methods=['PUT'])
    @login_required
    @validate_params(
        Param('seller_id', PATH, int),
        Param('image', JSON, str),
        Param('simple_introduce', JSON, str),
        Param('brand_crm_number', JSON, str, rules=[Pattern(r'^[0-9]{2,3}-[0-9]{3,4}-[0-9]{4}$')]),
        Param('zip_code', JSON, int),
        Param('address', JSON, str),
        Param('detail_address', JSON, str),
        Param('brand_crm_open', JSON, str),
        Param('brand_crm_end', JSON, str),
        Param('delivery_information', JSON, str),
        Param('refund_exchange_information', JSON, str),
        Param('seller_status_id', JSON, int),
        Param('background_image', JSON, str, required=False),
        Param('detail_introduce', JSON, str, required=False),
        Param('is_brand_crm_holiday', JSON, int, rules=[Enum(0, 1)]),
        Param('brand_name_korean', JSON, str),
        Param('brand_name_english', JSON, str),
        Param('manager_information', JSON, list),
        Param('seller_property_id', JSON, int)
    )
    def put_master_seller_page(*args):
        """ 셀러 계정 관리 ( 마스터 )

        Path parameter 로 셀러의 아이디를 받고 Body 로 셀러의 수정 데이터 받아서 수정하기

        Args:
            *args:
                seller_id : 셀러 id
                image : 셀러의 프로필 이미지
                simple_introduce : 셀러 한줄 소개
                brand_crm_number : 고객센터 전화번호
                zip_code : 우편번호
                address : 주소
                detail_address : 상세주소
                brand_crm_open : 고객센터 오픈시간
                brand_crm_end : 고객센터 마감시간
                delivery_information : 배송 정보
                refund_exchange_information : 교환/환불 정보
                seller_status_id : 셀러 상태 id ( 입점, 입점 대기 등 )
                background_image : 셀러 배경 이미지
                detail_introduce : 셀러 상세 정보
                is_brand_crm_holiday : 고객센터 휴일/공휴일 영업 여부
                brand_name_korean : 브랜드명 ( 한글 )
                brand_name_english : 브랜드명 ( 영어 )
                manager_information : 담당자 정보 ( 이름, 핸드폰 번호, 이메일 )
                seller_property_id : 셀러 속성 id ( 마켓, 로드샵 등 )

        Returns:
            200 : success, 데이터 수정하기 성공했을 때
            400 : 담당자 정보에 이름, 핸드폰 번호, 이메일 중 하나라도 없을 때 ,
                  이메일 형식이 맞지 않을 때, 핸드폰번호 형식이 맞지 않을 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            # 셀러 데이터 받아서 딕셔너리로 만들기
            seller = {
                'id':                           args[0],
                'image':                        args[1],
                'simple_introduce':             args[2],
                'brand_crm_number':             args[3],
                'zip_code':                     args[4],
                'address':                      args[5],
                'detail_address':               args[6],
                'brand_crm_open':               args[7],
                'brand_crm_end':                args[8],
                'delivery_information':         args[9],
                'refund_exchange_information':  args[10],
                'seller_status_id':             args[11],
                'background_image':             args[12],
                'detail_introduce':             args[13],
                'is_brand_crm_holiday':         args[14],
                'brand_name_korean':            args[15],
                'brand_name_english':           args[16],
                'manager_information':          args[17],
                'seller_property_id':           args[18]
            }

            # 담당자 정보 안에 이름, 번호, 이메일이 없으면 에러 발생
            for manager in seller['manager_information']:
                if manager['name'] is None or manager['phone_number'] is None or manager['email'] is None:
                    return jsonify({'message': 'no manager information data'}), 400

                # 이메일 형식이 맞지 않을 때 에러 발생
                if re.match(r'^([0-9a-zA-Z_-]+)@([0-9a-zA-Z_-]+)\.([0-9a-zA-Z_-]+)$', manager['email']) is None:
                    return jsonify({'message': 'invalid email'}), 400

                # 핸드폰 번호 형식이 맞지 않을 때 에러 발생
                if re.match(r'^010-[0-9]{3,4}-[0-9]{4}$', manager['phone_number']) is None:
                    return jsonify({'message': 'invalid phone number'}), 400

            seller_service.put_master_seller_page(seller, session)

            session.commit()
            return jsonify({'message': 'success'}), 200

        except NoAffectedRowException as e:
            session.rollback()
            return jsonify({'message': 'no affected row error {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()