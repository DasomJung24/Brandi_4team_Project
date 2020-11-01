import jwt
import re
from flask import request, jsonify, g, current_app
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
    def sign_up():
        session = None
        try:
            session = get_session()
            new_seller = request.json

            # 필수 입력값이 들어있지 않을 때 에러 발생
            if new_seller['account'] is None or new_seller['password'] is None or \
                    new_seller['brand_name_korean'] is None or new_seller['brand_name_english'] is None or \
                    new_seller['brand_crm_number'] is None or new_seller['seller_property_id'] is None or \
                    new_seller['phone_number'] is None:
                return jsonify({'message': 'invalid request'}), 400

            # 전화번호 형식이 맞지 않을 때 에러 발생
            if re.match(r'^[0-9]{2,3}-[0-9]{3,4}-[0-9]{4}$', new_seller['brand_crm_number']) is None:
                return jsonify({'message': 'invalid crm number'}), 400

            # 계정의 길이가 5 미만일 때 에러 발생
            if len(new_seller['account']) < 5:
                return jsonify({'message': 'short account'}), 400

            # 비밀번호에 영문, 숫자, 기호가 최소 1개씩 포함되어야 하고 길이가 8-20이 아니면 에러 발생
            if re.search(r'^(?=.*[0-9])(?=.*[A-Za-z])(?=.*[^a-zA-Z0-9]).{8,20}$', new_seller['password']) is None:
                return jsonify({'message': 'invalid password'}), 400

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
    def log_in():
        session = None
        try:
            session = get_session()
            seller = request.json
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

            if token == 'key error':
                return jsonify({'message': 'key error'}), 400

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

    @app.route("/mypage", methods=['GET', 'POST'])
    @login_required
    def my_page():
        # 회원관리-셀러정보관리(셀러)
        # 셀러가 셀러 정보 관리 들어갔을 때 등록된 정보 가져오기
        if request.method == 'GET':
            session = None
            try:
                session = get_session()
                seller_data = seller_service.get_my_page(g.seller_id, session)

                return jsonify(seller_data)

            except NoDataException as e:
                session.rollback()
                return jsonify({'message': 'no data {}'.format(e)}), e.status_code

            except Exception as e:
                session.rollback()
                return jsonify({'message': '{}'.format(e)}), 500

            finally:
                if session:
                    session.close()

        # 입력한 셀러 정보 받아서 데이터베이스에 넣기
        if request.method == 'POST':
            session = None
            try:
                session = get_session()
                seller_data = request.json
                seller = seller_data['seller']

                # 셀러 정보에 입력되는 필수값중에 None 이 있으면 에러 발생
                if seller['image'] is None or seller['simple_introduce'] is None or seller['brand_crm_number'] is None \
                        or seller['zip_code'] is None or seller['address'] is None or seller['detail_address'] is None \
                        or seller['brand_crm_open'] is None or seller['brand_crm_end'] is None \
                        or seller['delivery_information'] is None or seller['refund_exchange_information'] is None:
                    return jsonify({'message': 'invalid request'}), 400

                # 전화번호 형식이 맞지 않을 때 에러 발생
                if re.match(r'^[0-9]{2,3}-[0-9]{3,4}-[0-9]{4}$', seller['brand_crm_number']) \
                        is None:
                    return jsonify({'message': 'invalid crm number'}), 400

                # 담당자 정보가 없으면 에러 발생
                if seller_data['manager_information'] is None:
                    return jsonify({'message': 'manager information not found'}), 400

                # 담당자 정보 안에 이름, 번호, 이메일이 없으면 에러 발생
                for manager in seller_data['manager_information']:
                    if manager['name'] is None or manager['phone_number'] is None or manager['email'] is None:
                        return jsonify({'message': 'no manager information data'}), 400

                    # 이메일 형식이 맞지 않을 때 에러 발생
                    if re.match(r'^([0-9a-zA-Z_-]+)@([0-9a-zA-Z_-]+)\.([0-9a-zA-Z_-]+)$', manager['email']) is None:
                        return jsonify({'message': 'invalid email'}), 400

                    # 핸드폰 번호 형식이 맞지 않을 때 에러 발생
                    if re.match(r'^010-[0-9]{3,4}-[0-9]{4}$', manager['phone_number']) is None:
                        return jsonify({'message': 'invalid phone number'}), 400

                seller_service.post_my_page(seller_data, session)

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

    @app.route("/master/management-seller", methods=['GET', 'POST'])
    @login_required
    def management_seller():
        # 셀러계정관리(마스터)
        if request.method == 'GET':
            # 셀러 계정들을 가져오기
            session = None
            try:
                session = get_session()
                # 쿼리스트링 받아오기
                limit = request.args.get('limit', None)
                offset = request.args.get('offset', None)
                number = request.args.get('number', None)
                account = request.args.get('account', None)
                brand_name_korean = request.args.get('brand_name_korean', None)
                brand_name_english = request.args.get('brand_name_english', None)
                manager_name = request.args.get('manager_name', None)
                manager_number = request.args.get('manager_number', None)
                manager_email = request.args.get('manager_email', None)
                seller_status_id = request.args.get('status_id', None)
                seller_property_id = request.args.get('property_id', None)
                start_date = request.args.get('start_date', None)
                end_date = request.args.get('end_date', None)

                # 쿼리스트링을 딕셔너리로 만들어 줌
                query_string_list = {
                    'limit': 10 if limit is None else int(limit),
                    'offset': 0 if offset is None else int(offset),
                    'number': number,
                    'account': account,
                    'brand_name_korean': brand_name_korean,
                    'brand_name_english': brand_name_english,
                    'manager_name': manager_name,
                    'manager_number': manager_number,
                    'email': manager_email,
                    'seller_status_id': seller_status_id,
                    'seller_property_id': seller_property_id,
                    'start_date': start_date,
                    'end_date': end_date
                }

                seller_list = seller_service.get_seller_list(query_string_list, g.seller_id, session)

                # 마스터 계정이 아닐 때 에러 발생
                if seller_list == 'not authorizated':
                    return jsonify({'message': 'no master'}), 400

                return jsonify(seller_list)

            except NoDataException as e:
                session.rollback()
                return jsonify({'message': 'no data {}'.format(e)}), e.status_code

            except Exception as e:
                session.rollback()
                return jsonify({'message': '{}'.format(e)}), 500

            finally:
                if session:
                    session.close()

        if request.method == 'POST':
            # 셀러 status 변경하기 ( 입점상태 )
            session = None
            try:
                session = get_session()
                seller_status = request.json
                seller_id = seller_status['seller_id']
                button = seller_status['button']
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
                return jsonify({'message': 'no data {}'.format(e)}), e.status_code

            except Exception as e:
                session.rollback()
                return jsonify({'message': '{}'.format(e)}), 500

            finally:
                if session:
                    session.close()

    @app.route("/home", methods=['GET'])
    @login_required
    def get_home_seller():
        session = None
        try:
            session = get_session()

            data = seller_service.get_home_data(g.seller_id, session)

            return jsonify(data), 200

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()
