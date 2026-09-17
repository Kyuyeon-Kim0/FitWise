# FitWise 👕

> **개인·상품 반품 데이터 기반 AI 구매적합도 Agent 및 자원 모니터링 시스템**

FitWise는 의류 쇼핑몰에서 발생하는 **사이즈 및 핏 불일치로 인한 반품을 예방**하기 위한 웹 서비스입니다.

사용자의 과거 구매·반품 이력과 상품별 반품 데이터, 상품 리뷰를 분석하여 **AI 구매적합도**를 제공하고, AI Agent 실행에 따른 **시스템 자원 사용량**을 관리자 Dashboard에서 모니터링합니다.

---

## 📌 프로젝트 개요

온라인 의류 쇼핑에서는 실제로 옷을 입어보기 어렵기 때문에 사이즈나 핏이 예상과 달라 반품하는 경우가 발생합니다.

FitWise는 다음 데이터를 활용하여 구매 전에 사용자와 상품의 적합도를 분석합니다.

* 개인별 구매 및 반품 이력
* 상품별 / 사이즈별 반품 이력
* 상품 리뷰 및 평점
* 리뷰의 사이즈·핏 관련 의견

이를 기반으로 사용자에게 **구매적합도 점수와 판단 근거**를 제공합니다.

또한 AI Agent 사용 전후의 CPU, Memory, 처리시간 등을 측정하여 AI 기능이 시스템 자원에 미치는 영향을 확인할 수 있습니다.

---

## ✨ 주요 기능

### 1. Review Analysis Agent

상품 리뷰를 분석하여 구매 판단에 필요한 정보를 제공합니다.

**분석 항목**

* 긍정 / 부정 리뷰 비율
* 사이즈 관련 의견
* 핏 관련 의견
* 주요 긍정 / 부정 키워드
* 리뷰 종합 요약

**예시**

```text
긍정 리뷰: 76%
사이즈 관련 불만: 18%

주요 긍정 키워드
- 착용감
- 디자인
- 가벼움

주요 부정 키워드
- 사이즈 큼
- 소매 길음
- 소재가 얇음
```

---

### 2. Purchase Suitability Agent

사용자의 과거 구매·반품 이력과 상품 데이터를 분석하여 **구매적합도 점수**를 제공합니다.

주요 분석 데이터:

* 개인 구매 성공률
* 개인 사이즈별 반품 이력
* 상품별 반품률
* 사이즈별 반품률
* Review Analysis Agent 분석 결과

**결과 예시**

```text
구매적합도: 84점

개인 사이즈 성공률: 90%
상품 선택 사이즈 반품률: 12%
리뷰 적합도: 76%

AI 분석:
과거 구매 기록을 기준으로 M 사이즈의 적합도가 높습니다.
다만 일부 리뷰에서 소매가 길다는 의견이 있으므로
상품의 실측 사이즈를 확인하는 것을 권장합니다.
```

> 구매적합도 점수는 실제 반품 확률을 의미하는 것이 아니라 프로젝트에서 정의한 내부 적합도 지표입니다.

---

### 3. Resource Monitoring Dashboard

AI Agent 사용이 시스템 자원에 미치는 영향을 확인할 수 있는 관리자 Dashboard입니다.

**모니터링 항목**

* CPU 사용률
* Memory 사용량
* Agent 처리시간
* 응답시간
* Agent 실행 횟수
* 실행 로그

일반 상품 조회와 AI Agent 실행 상황을 비교하여 자원 사용량의 변화를 확인합니다.

```text
                일반 조회    Review Agent    Fit Agent

CPU                18%          32%            47%
Memory            620MB        750MB          890MB
Processing Time   0.18s        0.72s          1.24s
```

※ 위 수치는 예시이며 실제 서비스에서는 실행 과정에서 측정된 값을 사용합니다.

---

## 👥 역할 분담

| 담당     | 핵심 역할                        | 세부 작업                                                 |
| ------ | ---------------------------- | ----------------------------------------------------- |
| **1번** | **DB 설계 + 구매적합도**            | DB 테이블/관계 설계, 샘플 데이터, 개인·상품 반품률 분석, 구매적합도 계산 로직       |
| **2번** | **쇼핑몰 메인 화면 + 리뷰**           | 상품 목록, 카테고리, 상품 카드, 리뷰 데이터/표시, 리뷰 분석 Agent            |
| **3번** | **상품 상세 화면 + 관리자 Dashboard** | 상품 상세/사이즈 선택, 구매적합도 결과 표시, CPU·Memory·처리시간 측정, 관리자 화면 |

---

## 🖥️ 화면 구성

### 1. 상품 목록

```text
상품 카테고리

상의 | 아우터 | 하의

Jacket A
Shirt B
Pants C
```

상품을 선택하면 상품 상세 화면으로 이동합니다.

### 2. 상품 상세 / 리뷰

상품의 다음 정보를 확인할 수 있습니다.

* 상품 정보
* 가격
* 사이즈
* 리뷰
* 평점

또한 **Review Analysis Agent**를 실행하여 리뷰 분석 결과를 확인할 수 있습니다.

### 3. 구매적합도

사용자가 사이즈를 선택하고 구매적합도 분석을 실행하면 다음 정보를 제공합니다.

* 개인 구매 성공률
* 상품 반품률
* 사이즈별 반품률
* 리뷰 적합도
* 최종 구매적합도
* AI 분석 근거

### 4. 관리자 Dashboard

AI Agent 실행에 따른 시스템 자원 사용량을 확인합니다.

```text
Agent 미사용
      ↓
CPU / Memory / Response Time

Review Agent
      ↓
CPU / Memory / Processing Time

Purchase Suitability Agent
      ↓
CPU / Memory / Processing Time
```

---

## 🗂️ 상품 카테고리

| Category | Sub Category    | 주요 Fit 요소      |
| -------- | --------------- | -------------- |
| 상의       | 티셔츠 / 셔츠 / 니트   | 어깨, 가슴, 총장, 소매 |
| 아우터      | 자켓 / 코트 / 점퍼    | 어깨, 가슴, 소매, 핏  |
| 하의       | 청바지 / 슬랙스 / 반바지 | 허리, 허벅지, 총장    |

---

## 🗄️ Database

FitWise는 하나의 SQLite Database를 사용합니다.

```text
fashion_shop.db
```

### 주요 테이블

| Table           | Description            |
| --------------- | ---------------------- |
| `users`         | 사용자 정보                 |
| `products`      | 상품 정보                  |
| `orders`        | 구매 내역                  |
| `returns`       | 반품 내역 및 반품 사유          |
| `reviews`       | 상품 리뷰                  |
| `agent_logs`    | Agent 실행 기록            |
| `resource_logs` | CPU / Memory / 처리시간 기록 |

### 데이터 관계

```text
users
  │
  ├──── orders ──── products
  │        │
  │        └──── returns
  │
  └──── reviews ─── products

Review Agent
      │
      ▼
Purchase Suitability Agent
      │
      ▼
agent_logs / resource_logs
      │
      ▼
Admin Dashboard
```

---

## 👥 역할 분담

### 👤 Review Agent

* 상품 목록 / 상세 화면
* 상품 카테고리
* 리뷰 화면
* Review Analysis Agent
* 리뷰 키워드 분석
* 리뷰 요약

담당 데이터:

```text
products
reviews
```

### 👤 Purchase Suitability Agent

* 사용자 구매 데이터
* 개인 반품 데이터 분석
* 상품별 반품률 분석
* 사이즈별 반품률 분석
* 구매적합도 계산
* 구매적합도 결과 화면

담당 데이터:

```text
users
orders
returns
```

### 👤 Resource Monitoring / Admin

* CPU 사용량 측정
* Memory 사용량 측정
* Agent 처리시간 측정
* Agent 실행 로그
* Agent 사용 / 미사용 비교
* 관리자 Dashboard

담당 데이터:

```text
agent_logs
resource_logs
```

---

## 🌿 Git Branch

```text
main
│
├── feature/review-agent
│
├── feature/fit-agent
│
└── feature/admin-dashboard
```

각 기능은 별도의 Feature Branch에서 개발한 후 Pull Request를 통해 `main`에 병합합니다.

---

## 🔄 서비스 흐름

```text
상품 목록
   │
   ▼
상품 상세
   │
   ├── 상품 정보
   ├── 사이즈 선택
   └── 리뷰
          │
          ▼
   Review Analysis Agent
          │
          ▼
      리뷰 분석 결과
          │
          ▼
Purchase Suitability Agent
          │
          ▼
      구매적합도
          │
          ▼
     사용자 결과 제공


Agent 실행
   │
   ▼
Resource Monitoring
   │
   ├── CPU
   ├── Memory
   └── Processing Time
          │
          ▼
    Admin Dashboard
```

---

## 🛠️ Tech Stack

**Frontend**

* HTML
* CSS
* JavaScript

**Backend / Data**

* Python
* SQLite
* Pandas

**Resource Monitoring**

* psutil
* Python `time`

**Version Control**

* Git
* GitHub

---

## 📁 프로젝트 구조

```text
FitWise/
│
├── app/
│   ├── review_agent/
│   ├── fit_agent/
│   └── monitoring/
│
├── static/
│   ├── css/
│   └── js/
│
├── templates/
│   ├── products.html
│   ├── product_detail.html
│   ├── fit_result.html
│   └── admin_dashboard.html
│
├── data/
│   └── fashion_shop.db
│
├── README.md
└── requirements.txt
```

※ 실제 구현 방식에 따라 디렉터리 구조는 변경될 수 있습니다.

---

## 🎯 프로젝트 목표

FitWise의 핵심 목표는 단순히 AI Agent를 구현하는 것이 아닙니다.

**사용자 관점**

> 개인의 구매·반품 이력과 상품 데이터를 활용하여 구매 전에 의류의 적합성을 판단할 수 있도록 지원합니다.

**서비스 관점**

> 리뷰와 반품 데이터를 활용하여 사이즈 및 핏 문제로 발생하는 불필요한 반품을 줄이는 것을 목표로 합니다.

**시스템 관점**

> AI Agent 도입에 따른 CPU, Memory, 처리시간 변화를 측정하여 AI 기능과 시스템 자원 사용량의 관계를 분석합니다.

---

## 💡 FitWise

**Better Fit. Smarter Purchase. Fewer Returns.**

데이터를 활용하여 사용자에게 더 적합한 의류 구매를 지원하고, AI Agent의 시스템 자원 사용량까지 함께 관리하는 것을 목표로 합니다.
