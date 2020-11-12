from flask import jsonify, g
from .seller_view import login_required
from flask_request_validator import Param, PATH, validate_params, JSON, Enum, GET, Pattern
from exceptions import NoAffectedRowException, NoDataException


def product_endpoints(app, services, get_session):
    product_service = services.product_service

    @app.route("/product/register", methods=['GET'])
    @login_required
    def get_register_product():
        """ 상품 등록 API

        상품 등록 페이지에 들어갔을 때 불러오는 데이터

        Returns:
            200 : data_list ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            data_list = product_service.get_category_color_size(session)

            return jsonify(data_list), 200

        except NoDataException as e:
            session.rollback()
            return jsonify({'message': 'no data error {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/product/register", methods=['POST'])
    @login_required
    @validate_params(
        Param('sub_categories_id', JSON, int),
        Param('name', JSON, str),
        Param('main_image', JSON, str),
        Param('is_sell', JSON, int, rules=[Enum(0, 1)]),
        Param('is_display', JSON, int, rules=[Enum(0, 1)]),
        Param('is_discount', JSON, int, rules=[Enum(0, 1)]),
        Param('price', JSON, int),
        Param('detail', JSON, str),
        Param('maximum_sell_count', JSON, int),
        Param('minimum_sell_count', JSON, int),
        Param('options', JSON, list),
        Param('discount_rate', JSON, int, required=False),
        Param('discount_start_date', JSON, str, required=False),
        Param('discount_end_date', JSON, str, required=False),
        Param('simple_information', JSON, str, required=False),
        Param('manufacturer', JSON, str, required=False),
        Param('manufacture_date', JSON, str, required=False),
        Param('origin', JSON, str, required=False),
        Param('image_list', JSON, list, required=False)
    )
    def post_register_product(*args):
        """ 상품 등록 API

        Body 로 상품 데이터를 받아 상품 등록하기

        Args:
            *args:
                sub_categories_id   : 2차 카테고리 id
                name                : 상품명
                main_image          : 상품 메인 이미지
                is_sell             : 판매 여부
                is_display          : 진열 여부
                is_discount         : 할인 여부
                price               : 상품 가격
                detail              : 상품 상세정보
                maximum_sell_count  : 최대 판매 수량
                minimum_sell_count  : 최소 판매 수량
                options             : 리스트. [{ 컬러 id, 사이즈 id, 재고관리여부, 재고수량 }]
                discount_rate       : 할인율
                discount_start_date : 할인 시작 날짜
                discount_end_date   : 할인 마지막 날짜
                simple_information  : 한줄 상품 설명
                manufacturer        : 제조사
                manufacture_date    : 제조일자
                origin              : 원산지
                image_list          : 서브이미지 리스트

        Returns:
            200 : success, 상품 등록에 성공했을 때
            400 : key error , 옵션리스트 안에 컬러아이디, 사이즈아이디, 재고관리여부 중 하나라도 없을 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            # 바디에 담긴 부분 유효성 검사 후에 딕셔너리로 만들기
            product_data = {
                'sub_categories_id':    args[0],
                'name':                 args[1],
                'main_image':           args[2],
                'is_sell':              args[3],
                'is_display':           args[4],
                'is_discount':          args[5],
                'price':                args[6],
                'detail':               args[7],
                'maximum_sell_count':   args[8],
                'minimum_sell_count':   args[9],
                'options':              args[10],
                'discount_rate':        args[11],
                'discount_start_date':  args[12],
                'discount_end_date':    args[13],
                'simple_information':   args[14],
                'manufacturer':         args[15],
                'manufacture_date':     args[16],
                'origin':               args[17],
                'image_list':           args[18],
                'seller_id':            g.seller_id
            }

            # 옵션 안의 리스트의 키값들이 None 일 때 에러 발생
            for options in product_data['options']:
                if options['color_id'] is None or options['size_id'] is None or options['is_inventory_manage'] is None:
                    return jsonify({'message': 'option data not exist'}), 400

            product_service.post_register_product(product_data, session)

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

    @app.route("/category/<int:category_id>", methods=['GET'])
    @login_required
    def get_sub_category_list(category_id):
        """ 2차 카테고리 불러오기

        상품 등록 페이지에서 1차 카테고리를 선택했을 때 해당하는 2차 카테고리 리스트 불러오기

        Args:
            category_id: 1차 카테고리 id

        Returns:
            200 : category_list ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()
            category_list = product_service.get_sub_categories(category_id, session)

            return jsonify(category_list), 200

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/product/update/<int:product_id>", methods=['GET'])
    @login_required
    @validate_params(
        Param('product_id', PATH, int)
    )
    def get_update_product(product_id):
        """ 상품 상세페이지 ( 수정 )

        상품 수정 페이지 들어갔을 때 등록되어 있는 상품 데이터 가져오기

        Args:
            product_id: 상품 id

        Returns:
            200 : product_data ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            product_data = product_service.get_product(product_id, session)

            return jsonify(product_data)

        except NoDataException as e:
            session.rollback()
            return jsonify({'message': 'no data {}'.format(e.message)}), e.status_code

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()

    @app.route("/product/update/<int:product_id>", methods=['PUT'])
    @login_required
    @validate_params(
        Param('product_id', PATH, int),
        Param('sub_categories_id', JSON, int),
        Param('name', JSON, str),
        Param('main_image', JSON, str),
        Param('is_sell', JSON, int, rules=[Enum(0, 1)]),
        Param('is_display', JSON, int, rules=[Enum(0, 1)]),
        Param('is_discount', JSON, int, rules=[Enum(0, 1)]),
        Param('price', JSON, int),
        Param('detail', JSON, str),
        Param('maximum_sell_count', JSON, int),
        Param('minimum_sell_count', JSON, int),
        Param('options', JSON, list),
        Param('discount_rate', JSON, int, required=False),
        Param('discount_start_date', JSON, str, required=False),
        Param('discount_end_date', JSON, str, required=False),
        Param('simple_information', JSON, str, required=False),
        Param('manufacturer', JSON, str, required=False),
        Param('manufacture_date', JSON, str, required=False),
        Param('origin', JSON, str, required=False),
        Param('image_list', JSON, list, required=False)
    )
    def put_update_product(*args):
        """ 상품 데이터 수정 API

        Path parameter 로 상품 id를 받고 Body 로 상품 데이터를 받아 데이터 업데이트하기

        Args:
            *args:
                product_id          : 상품 id
                sub_categories_id   : 2차 카테고리 id
                name                : 상품명
                main_image          : 상품 메인 이미지
                is_sell             : 판매 여부
                is_display          : 진열 여부
                is_discount         : 할인 여부
                price               : 상품 가격
                detail              : 상품 상세 정보
                maximum_sell_count  : 최대 판매 수량
                minimum_sell_count  : 최소 판매 수량
                options             : 옵션리스트 ( 컬러아이디, 사이즈아이디, 재고관리여부, 재고수량 )
                discount_rate       : 할인율
                discount_start_date : 할인 시작 날짜
                discount_end_date   : 할인 마지막 날짜
                simple_information  : 상품 한줄 정보
                manufacturer        : 제조사
                manufacture_date    : 제조 날짜
                origin              : 원산지
                image_list          : 서브 이미지 리스트

        Returns:
            200 : success, 상품 데이터 업데이트에 성공했을 때
            400 : 옵션리스트에 컬러아이디, 사이즈아이디, 재고관리여부가 하나라도 없을 때
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            # 수정할 상품 데이터 딕셔너리로 만들기
            product_data = {
                'product_id':           args[0],
                'sub_categories_id':    args[1],
                'name':                 args[2],
                'main_image':           args[3],
                'is_sell':              args[4],
                'is_display':           args[5],
                'is_discount':          args[6],
                'price':                args[7],
                'detail':               args[8],
                'maximum_sell_count':   args[9],
                'minimum_sell_count':   args[10],
                'options':              args[11],
                'discount_rate':        args[12],
                'discount_start_date':  args[13],
                'discount_end_date':    args[14],
                'simple_information':   args[15],
                'manufacturer':         args[16],
                'manufacture_date':     args[17],
                'origin':               args[18],
                'image_list':           args[19],
                'seller_id':            g.seller_id
            }

            # 옵션 안의 키값들이 None 이면 에러 발생
            for options in product_data['options']:
                if options['color_id'] is None or options['size_id'] is None or options['is_inventory_manage'] is None:
                    return jsonify({'message': 'option data not exist'}), 400

            product_service.post_update_product(product_data, session)

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

    @app.route("/product/management", methods=['GET'])
    @login_required
    @validate_params(
        Param('limit', GET, int, required=False),
        Param('offset', GET, int, required=False),
        Param('is_sell', GET, int, rules=[Enum(0, 1)], required=False),
        Param('is_discount', GET, int, rules=[Enum(0, 1)], required=False),
        Param('is_display', GET, int, rules=[Enum(0, 1)], required=False),
        Param('name', GET, str, required=False),
        Param('code_number', GET, int, required=False),
        Param('product_number', GET, str, required=False),
        Param('start_date', GET, str, required=False),
        Param('end_date', GET, str, required=False),
        Param('seller_property_id', GET, int, required=False),
        Param('brand_name_korean', GET, str, required=False)
    )
    def management_product(*args):
        """ 상품 관리 리스트 API

        쿼리 파라미터로 필터링 조건들을 받아서 필터링 조건에 따라서 등록되어 있는 상품 리스트를 가져오기

        Args:
            *args:
                limit              : pagination 범위
                offset             : pagination 시작 번호
                is_sell            : 판매 여부
                is_discount        : 할인 여부
                is_display         : 진열 여부
                name               : 상품명
                code_number        : 상품 코드 번호
                product_number     : 상품 id
                start_date         : 해당날짜 이후에 등록된 상품
                end_date           : 해당날짜 이전에 등록된 상품
                seller_property_id : 셀러 속성 id ( 로드샵, 마켓 등 )
                brand_name_korean  : 브랜드명 ( 한글 )

        Returns:
            200 : product_list ( type : dict )
            500 : Exception

        """
        session = None
        try:
            session = get_session()

            # 쿼리스트링을 딕셔너리로 만들기
            query_string_list = {
                'limit':                10 if args[0] is None else args[0],
                'offset':               0 if args[1] is None else args[1],
                'is_sell':              args[2],
                'is_discount':          args[3],
                'is_display':           args[4],
                'name':                 args[5],
                'code_number':          args[6],
                'product_number':       args[7],
                'start_date':           args[8],
                'end_date':             args[9],
                'seller_property_id':   args[10],
                'brand_name_korean':    args[11],
                'seller_id':            g.seller_id
            }

            product_list = product_service.get_product_list(query_string_list, session)

            return jsonify(product_list)

        except Exception as e:
            session.rollback()
            return jsonify({'message': '{}'.format(e)}), 500

        finally:
            if session:
                session.close()
