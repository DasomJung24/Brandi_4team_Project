## Brandi Admin Clone

![](https://images.velog.io/images/dnpxm387/post/3f0e4e0b-2d92-42be-85c3-ebea39c77353/%E1%84%89%E1%85%B3%E1%84%8F%E1%85%B3%E1%84%85%E1%85%B5%E1%86%AB%E1%84%89%E1%85%A3%E1%86%BA%202020-11-19%20%E1%84%8B%E1%85%A9%E1%84%92%E1%85%AE%2010.47.08.png)


#### 🗓 프로젝트 기간 
2020.10.19 - 2020.11.12

#### 🛠 Skills
- Python
- Flask
- SQLalchemy
- PyJWT
- Bcrypt
- Aquery
- MySQL

#### ✂️ Tools
- Git & Github
- trello
- postman

#### 📌 구현사항
**< backend - python / flask >**
- Aquerytool을 사용하여 modeling
- 초기 세팅 : config.py 에 데이터베이스 정의, secret key, algorithm 작성 / app.py에 데이터베이스 연결, Session을 이용한 db 접속 & 해제 설정
- MVC layered pattern(Dao, Service, View)
- Flask-request-validator 를 이용한 유효성 검사
- error handler 데코레이터를 사용한 validate-params 에러 잡아줌
- session을 사용하여 db connection 관리
- docstring을 사용하여 함수에 대한 설명 추가
- Seller의 입점 상태, 배송 상태, 버튼, 선분이력 close time 등 상수로 지정하여 config.py에 작성
- Seller Home 화면 구현
- Seller 로그인, 회원가입 구현
- Bcrypt를 사용하여 비밀번호 암호화
- JWT로 access token 발행
- Seller 상세페이지 구현
- Query string을 통한 Seller 계정 리스트 (Master) 구현
- Seller 입점상태 변경 (Master) 구현
- Seller 입점 상태 변경시마다 Slack Bot 메세지 보내기 구현
- 상품 등록 / 수정 - 선분이력 구현
- Query string 을 통한 상품 리스트 구현
- 상품 구매하기 구현
- Query string 을 통한 주문 리스트 구현
- 배송 처리 버튼으로 배송 상태 변경 구현
- 주문 상세페이지 구현

**< frontend - javascript / vue.js >**
- 상품 구매하기 모달창 구현
