from flask import jsonify, g
from flask_request_validator import Param, JSON, validate_params, Pattern, PATH, GET
from .seller_view import login_required
from exceptions import NoDataException, NoAffectedRowException
from config import shipment_button


def order_endpoints(app, services, get_session):
    order_service = services.order_service

    @app.route("/order/product/<int:product_id>", methods=['GET'])
    @login_required
    @validate_params(
        Param('product_id', PATH, int)
    )
    def get_order_product(product_id):
        """ 상품 구매하기 API

        상품 구매하기 클릭할 때 상품 id를 path parameter 로 받아 모달창에 상품 정보 가져오기

        Args:
            product_id: 상품 id

        Returns:
            200 : product_data ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            product_data = order_service.get_product_data(product_id, session)

            return jsonify(product_data), 200

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/order/product/<int:product_id>", methods=['POST'])
    @login_required
    @validate_params(
        Param('product_id', PATH, int),
        Param('user_name', JSON, str),
        Param('phone_number', JSON, str, rules=[Pattern(r'^010-[0-9]{3,4}-[0-9]{4}$')]),
        Param('zip_code', JSON, int),
        Param('address', JSON, str),
        Param('detail_address', JSON, str),
        Param('count', JSON, int),
        Param('color_id', JSON, int),
        Param('size_id', JSON, int),
        Param('total_price', JSON, int)
    )
    def post_order_product(*args):
        """ 상품 주문하기 API

        Body 로 주문한 상품 데이터를 받아 데이터베이스에 저장하기

        Args:
            *args:
                product_id     : 상품 id
                user_name      : 주문자명
                phone_number   : 주문자의 핸드폰 번호
                zip_code       : 주문자 우편번호
                address        : 주문자 주소
                detail_address : 주문자 상세주소
                count          : 주문 수량
                color_id       : 컬러 id
                size_id        : 사이즈 id
                total_price    : 총 결제금액

        Returns:
            200 : success, 주문 데이터를 데이터베이스 저장에 성공했을 때
            400 : 재고수량에 맞지 않는 수량을 주문했을 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            # validation params 을 통해 들어온 데이터를 딕셔너리로 만들기
            order_data = {
                'product_id':       args[0],
                'user_name':        args[1],
                'phone_number':     args[2],
                'zip_code':         args[3],
                'address':          args[4],
                'detail_address':   args[5],
                'count':            args[6],
                'color_id':         args[7],
                'size_id':          args[8],
                'total_price':      args[9]
            }

            order_data = order_service.order_product(order_data, g.seller_id, session)

            # 재고 수량에 맞지 않는 수량을 주문했을 때 에러 발생
            if order_data == 'invalid count':
                return jsonify({'message': "invalid count"}), 400

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
    @validate_params(
        Param('order_status_id', PATH, int),
        Param('limit', GET, int, required=False),
        Param('offset', GET, int, required=False),
        Param('start_date', GET, str, required=False),
        Param('end_date', GET, str, required=False),
        Param('order_number', GET, int, required=False),
        Param('detail_number', GET, int, required=False),
        Param('user_name', GET, str, required=False),
        Param('phone_number', GET, str, required=False),
        Param('product_name', GET, str, required=False),
        Param('order_by', GET, int, required=False)
    )
    def order_prepare(*args):
        """ 주문리스트 API

        path 파라미터로 주문 상태 id ( 배송중, 결제완료 등 ) 를 받아서 쿼리 파라미터로 받은 필터링 조건에 맞게 주문 리스트를 가져오기

        Args:
            *args:
                order_status_id : 주문 상태 id ( 결제완료, 배송중 등 )
                limit           : pagination 범위
                offset          : pagination 시작 번호
                start_date      : 해당날짜 이후의 주문 상품 리스트
                end_date        : 해당날짜 이전의 주문 상품 리스트
                order_number    : 주문 번호
                detail_number   : 주문 상세 번호
                user_name       : 주문자명
                phone_number    : 주문자 핸드폰 번호
                product_name    : 주문한 상품명
                order_by        : 정렬 순서

        Returns:
            200 : order_list ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            # 쿼리스트링으로 리스트 만들기
            query_string_list = {
                'order_status_id':  args[0],
                'limit':            50 if args[1] is None else args[1],
                'offset':           0 if args[2] is None else args[2],
                'start_date':       args[3],
                'end_date':         args[4],
                'order_number':     args[5],
                'detail_number':    args[6],
                'user_name':        args[7],
                'phone_number':     args[8],
                'product_name':     args[9],
                'order_by':         1 if args[10] is None else args[10]
            }

            order_list = order_service.get_order_product_list(query_string_list, session)

            return jsonify(order_list)

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/order/shipment", methods=['POST'])
    @login_required
    @validate_params(
        Param('order_id_list', JSON, list),
        Param('shipment_button', JSON, int)
    )
    def change_shipment_status(*args):
        """ 배송 처리 버튼 API

        배송 처리, 배송완료 처리 버튼을 눌렀을 때 Body 로 주문상품 데이터와 버튼 데이터를 받아 배송상태 변경하기

        Args:
            *args:
                order_id_list   : 주문 상품들이 id 리스트
                shipment_button : 배송처리버튼

        Returns:
            200 : success, 주문 상품의 배송처리 상태가 정상적으로 성공했을 때
            400 : 버튼이 잘못 눌렸을 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            order_list = {
                'order_id_list': args[0],
                'shipment_button': args[1]
            }

            # 버튼이 잘못 눌렸을 때 에러 발생
            if order_list['shipment_button'] != shipment_button['SHIPMENT'] \
                    or order_list['shipment_button'] != shipment_button['SHIPMENT_COMPLETE']:
                return jsonify({'message': 'invalid button error'}), 400

            order_service.change_order_status(order_list,  session)

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

    @app.route("/order/<int:order_id>", methods=['GET'])
    @login_required
    @validate_params(
        Param('order_id', PATH, int)
    )
    def get_order_detail(order_id):
        """ 주문 상세페이지 API

        path parameter 로 주문 id 를 받아와서 주문 상세 데이터 가져오기

        Args:
            order_id: 주문 id

        Returns:
            200 : order_details ( type : dict )
            500 : Exception

        """
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

    @app.route("/order/change_number", methods=['PUT'])
    @login_required
    @validate_params(
        Param('phone_number', JSON, str, rules=[Pattern(r'^010-[0-9]{3,4}-[0-9]{4}$')]),
        Param('order_id', JSON, int)
    )
    def change_phone_number(*args):
        """ 핸드폰 번호 변경 API

        주문 상세페이지에서 핸드폰 번호 변경할 때 변경 데이터 가져와서 핸드폰 번호 업데이트하기

        Args:
            *args:
                phone_number : 변경하려는 핸드폰 번호
                order_id     : 주문 id

        Returns:
            200 : success, 성공적으로 핸드폰 데이터를 변경하였을 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            data = {
                'phone_number': args[0],
                'order_id': args[1]
            }

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
