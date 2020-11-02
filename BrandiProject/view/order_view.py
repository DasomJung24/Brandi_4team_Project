import re
from flask import request, jsonify, g
from flask_request_validator import Param, JSON, validate_params, Pattern
from .seller_view import login_required
from exceptions import NoDataException, NoAffectedRowException


def order_endpoints(app, services, get_session):
    order_service = services.order_service

    @app.route("/order/product/<int:product_id>", methods=['GET', 'POST'])
    @login_required
    def order_product(product_id):
        if request.method == 'GET':
            # 상품 구매하기 클릭시 뜨는 모달창에 상품 정보 가져오기
            session = None
            try:
                session = get_session()
                product_data = order_service.get_product_data(product_id, session)

                return jsonify({'product_data': product_data}), 200

            except Exception as e:
                session.rollback()
                return jsonify({'message': '{}'.format(e)}), 500

            finally:
                if session:
                    session.close()

        if request.method == 'POST':
            # 주문하기 클릭시 주문 정보 데이터에 저장하기
            session = None
            try:
                session = get_session()
                order_data = request.json

                # 있어야 하는 키값이 None 일 때 에러 발생
                if order_data['user_name'] is None or order_data['phone_number'] is None \
                        or order_data['zip_code'] is None or order_data['address'] is None \
                        or order_data['detail_address'] is None or order_data['count'] is None \
                        or order_data['color_id'] is None or order_data['size_id'] is None \
                        or order_data['total_price'] is None:
                    return jsonify({'message': 'invalid request'}), 400

                if re.match(r'^010-[0-9]{3,4}-[0-9]{4}$', order_data['phone_number']) is None:
                    return jsonify({'message': 'invalid phone number'}), 400

                order_service.order_product(order_data, product_id, g.seller_id, session)

                session.commit()
                return jsonify({'message': 'success'}), 200

            except NoAffectedRowException as e:
                session.rollback()
                return jsonify({'message': 'no affected row error {}'.format(e.message)}), e.status_code

            except NoDataException as e:
                session.rollback()
                return jsonify({'message': 'no data error {}'.format(e.message)}), e.status_code

            except Exception as e:
                session.rollback()
                return jsonify({'message': '{}'.format(e)}), 500

            finally:
                if session:
                    session.close()

    @app.route("/order/status/<int:order_status_id>", methods=['GET'])
    @login_required
    def order_prepare(order_status_id):

        # 셀러 상품준비 관리 -  셀러한테 등록되어 있는 상품 리스트 가져오기
        session = None
        try:
            session = get_session()
            # 쿼리스트링 받아오기
            limit = request.args.get('limit', None)
            offset = request.args.get('offset', None)
            start_date = request.args.get('start_date', None)
            end_date = request.args.get('end_date', None)
            order_number = request.args.get('number', None)
            detail_number = request.args.get('detail_number', None)
            user_name = request.args.get('user_name', None)
            phone_number = request.args.get('phone_number', None)
            product_name = request.args.get('product_name', None)
            order_by = request.args.get('order_by', None)

            """
            쿼리스트링으로 리스트 만들기
            order_by : a.created_at ASC / a.created_at DESC / d.update_time ASC / d.update_time DESC
            """

            query_string_list = {
                'limit': 50 if limit is None else int(limit),
                'offset': 0 if offset is None else int(offset),
                'start_date': start_date,
                'end_date': end_date,
                'order_number': order_number,
                'detail_number': detail_number,
                'user_name': user_name,
                'phone_number': phone_number,
                'product_name': product_name,
                'order_by': 'a.created_at ASC' if order_by is None else order_by,
                'order_status_id': order_status_id,
                'seller_id': g.seller_id
            }

            order_list = order_service.get_order_product_list(query_string_list, session)

            return jsonify(order_list)

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/order/shipment/<int:shipment_button>", methods=['POST'])
    @login_required
    def change_shipment_status(shipment_button):
        # 배송처리, 배송완료처리 버튼 눌렀을 때 배송 상태 변경하기
        session = None
        try:
            session = get_session()
            order_id_list = request.json

            order_service.change_order_status(order_id_list, shipment_button, session)

            session.commit()
            return jsonify({'message': 'success'}), 200

        except NoAffectedRowException as e:
            session.rollback()
            return jsonify({'message': 'no affected row error {}'.format(e)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/order/detail/<int:order_id>", methods=['GET'])
    @login_required
    def get_order_detail(order_id):
        # 주문 상세 페이지 정보 가져오기
        session = None
        try:
            session = get_session()

            order_details = order_service.get_details(order_id, session)

            return jsonify(order_details), 200

        except NoDataException as e:
            session.rollback()
            return jsonify({'message': 'no data error {}'.format(e)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/order/change_number", methods=['POST'])
    @login_required
    @validate_params(
        Param('phone_number', JSON, str, rules=[Pattern(r'^010-[0-9]{3,4}-[0-9]{4}$')]),
        Param('order_id', JSON, int)
    )
    def change_phone_number(phone_number, order_id):
        # 주문자 핸드폰 번호 수정하기
        session = None
        try:
            session = get_session()

            """
            {"order_id": 3, "phone_number":"010-456-7899"}
            """

            data = {'phone_number': phone_number, 'order_id': order_id}

            order_service.change_number(data, session)

            session.commit()
            return jsonify({'message': 'success'}), 200

        except NoAffectedRowException as e:
            session.rollback()
            return jsonify({'message': 'no affected row error {}'.format(e)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()
