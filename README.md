# FitWise 👕

> **개인·상품·리뷰 데이터 기반 AI 구매적합도 Agent & Resource Monitoring System**

FitWise는 의류 쇼핑몰에서 사용자의 **구매·반품 이력, 상품 정보, 사이즈 정보, 리뷰 데이터**를 활용하여 구매 전에 상품과 사용자의 적합도를 분석하는 웹 서비스입니다.

핵심 기능은 **Purchase Suitability Agent**이며 다음 정보를 종합하여 구매적합도를 계산합니다.

* 개인 구매·반품 이력
* 상품별 반품 데이터
* 사이즈별 반품 데이터
* 상품 실측 사이즈
* Review Analysis Agent 분석 결과

Review Analysis Agent는 동일한 상품에 대해 불필요하게 반복 실행하지 않습니다.

> **Review Agent는 필요할 때 한 번 실행하고 분석 결과를 저장하여 재사용합니다.**

또한 Agent 실행 과정에서 발생하는 **CPU, Memory, Response Time**을 기록하여 관리자 Dashboard에서 AI Agent의 시스템 자원 사용량을 확인합니다.

---

# 📌 프로젝트 목표

온라인 의류 쇼핑에서는 상품을 직접 입어보기 어렵기 때문에 사이즈나 핏이 예상과 달라 반품하는 경우가 발생합니다.

FitWise는 단순히 반품 여부를 예측하는 것이 아니라,

> **"이 상품의 이 사이즈가 나에게 얼마나 잘 맞을까?"**

를 분석하는 것을 목표로 합니다.

이를 위해 개인 데이터, 상품 데이터, 반품 데이터와 리뷰 분석 결과를 결합하여 **구매적합도 점수와 판단 근거**를 제공합니다.

---

# 🧩 핵심 시스템 구조

```text
                 사용자
                   │
                   ▼
             상품 / 사이즈 선택
                   │
                   ▼
          Purchase Suitability
                 Agent
                   │
        ┌──────────┼───────────┐
        │          │           │
        ▼          ▼           ▼
    개인 이력    반품 데이터   상품/사이즈
        │          │           │
        └──────────┼───────────┘
                   │
                   ▼
            리뷰 분석 결과 확인
                   │
             ┌─────┴─────┐
             │           │
          결과 있음     결과 없음
             │           │
             │           ▼
             │      Review Agent
             │           │
             │           ▼
             │      분석 결과 저장
             │           │
             └─────┬─────┘
                   ▼
             리뷰 결과 재사용
                   │
                   ▼
              구매적합도
```

---

# ✨ 주요 기능

## 1. Review Analysis Agent

상품 리뷰에서 사이즈와 핏에 관련된 정보를 분석합니다.

### 분석 항목

* 긍정 / 부정 리뷰 비율
* 사이즈 관련 의견
* 핏 관련 의견
* 주요 긍정 키워드
* 주요 부정 키워드
* 리뷰 적합도
* 리뷰 종합 요약

### 사용 데이터

```text
products
reviews
```

### 분석 예시

```text
긍정 리뷰: 76%
부정 리뷰: 24%

사이즈 관련 긍정: 82%
핏 관련 긍정: 70%

주요 긍정 키워드
- 착용감
- 디자인
- 가벼움

주요 부정 키워드
- 사이즈 큼
- 소매 길음
- 소재 얇음

리뷰 적합도: 76점

AI 요약:
전체적인 만족도는 높은 편이지만
일부 구매자에게 소매가 길다는 의견이 있습니다.
```

---

# ♻️ Review Agent 결과 재사용

FitWise에서는 동일한 리뷰를 반복해서 AI가 분석하지 않도록 합니다.

Review Agent가 실행되면 분석 결과를 DB에 저장합니다.

```text
reviews
   │
   ▼
Review Agent
   │
   ▼
review_analysis
   │
   ├── 리뷰 적합도
   ├── 긍정/부정 비율
   ├── 사이즈 분석
   ├── 핏 분석
   └── AI 요약
```

이후 Purchase Suitability Agent가 실행될 때 저장된 분석 결과가 있다면 **Review Agent를 다시 실행하지 않습니다.**

---

## Case 1. 리뷰 화면에서 먼저 분석한 경우

```text
[리뷰 AI 분석] 클릭
        │
        ▼
Review Agent 실행
        │
        ▼
review_analysis 저장
        │
        ▼
리뷰 분석 결과 표시


이후


[구매적합도 분석] 클릭
        │
        ▼
review_analysis 확인
        │
        ▼
기존 결과 발견
        │
        ▼
Review Agent 재실행 X
        │
        ▼
기존 리뷰 분석 결과 사용
        │
        ▼
Purchase Suitability Agent
```

따라서 Review Agent는 **한 번만 실행됩니다.**

---

## Case 2. 리뷰 분석 없이 구매적합도를 실행한 경우

```text
[구매적합도 분석] 클릭
        │
        ▼
review_analysis 확인
        │
        ▼
분석 결과 없음
        │
        ▼
Review Agent 자동 실행
        │
        ▼
review_analysis 저장
        │
        ▼
Purchase Suitability Agent
        │
        ▼
구매적합도
```

이 경우에도 Review Agent는 한 번 실행되고 이후 결과가 재사용됩니다.

---

# 🧠 Review Agent 실행 판단

프로그램에서는 다음과 같은 흐름으로 처리합니다.

```text
리뷰 분석 결과 있음?
        │
   ┌────┴────┐
   │         │
  YES        NO
   │         │
   │    Review Agent 실행
   │         │
   │    결과 DB 저장
   │         │
   └────┬────┘
        ▼
   저장 결과 사용
        │
        ▼
Purchase Suitability Agent
```

핵심 원칙:

> **Analyze Once, Reuse Many Times**

---

# ⭐ 2. Purchase Suitability Agent

FitWise의 핵심 Agent입니다.

사용자가 선택한 상품과 사이즈에 대해 여러 데이터를 종합하여 **구매적합도 점수**를 제공합니다.

사용자는 이번 분석에 적용할 **선호 핏·키·몸무게**를 직접 선택합니다. 키와 몸무게는 선택 사이즈 구매 이력과 리뷰 작성자의 체형 유사도를 계산하는 데 사용되며, 사용자의 기본 프로필을 변경하지 않습니다.

### 분석 데이터

* 개인 선택 사이즈 구매 성공률
* 상품 전체 반품 안정성
* 체형 유사 선택 사이즈 구매 성공률
* 체형 유사 리뷰 적합도
* 상품 실측 사이즈 및 Review Agent 분석 결과

### 사용 데이터

```text
users (키·몸무게 포함)
orders / returns
products
reviews / review_analysis
```

---

# 🧮 구매적합도 계산

예를 들어 다음과 같은 내부 지표를 사용할 수 있습니다.

| 분석 지표 | 가중치 |
| --- | ---: |
| 개인 선택 사이즈 성공률 | 25% |
| 상품 반품 안정성 | 20% |
| 체형 유사 선택 사이즈 성공률 | 30% |
| 체형 유사 리뷰 적합도 | 25% |
| **합계** | **100%** |

계산 예시:

```text
개인 선택 사이즈 성공률       90점
상품 반품 안정성             85점
체형 유사 선택 사이즈 성공률  88점
체형 유사 리뷰 적합도        76점
```

```text
구매적합도
=
90 × 0.25
+ 85 × 0.20
+ 88 × 0.30
+ 76 × 0.25

= 84점
```

체형 유사 선택 사이즈 성공률과 체형 유사 리뷰 적합도는 입력한 사용자 키·몸무게와 구매자/리뷰 작성자의 차이가 작을수록 높은 가중치를 적용합니다.

```text
체형 유사도
= max(0.1, 1 - 0.5 × min(키 차이, 20) / 20
              - 0.5 × min(몸무게 차이, 20) / 20)
```

키·몸무게 차이는 각각 최대 20cm·20kg까지만 반영하며, 크게 다른 체형의 데이터도 완전히 배제하지 않도록 최소 가중치 0.1을 둡니다.

> 구매적합도 점수는 실제 반품 확률을 의미하지 않으며 프로젝트에서 정의한 내부 적합도 지표입니다.

---

# 📋 구매적합도 결과 예시

```text
━━━━━━━━━━━━━━━━━━━━━━
       구매적합도
          85점
━━━━━━━━━━━━━━━━━━━━━━

개인 사이즈 성공률       90%
상품 반품 안정성         85%
체형 유사 M 사이즈 성공률 88%
체형 유사 리뷰 적합도     76%

AI Fit Advisor

과거 구매 기록을 기준으로
M 사이즈의 구매 성공률이 높은 편입니다.

해당 상품의 M 사이즈 역시
반품률이 비교적 낮습니다.

리뷰에서는 전체적인 핏 만족도가 높지만
일부 사용자에게 소매가 길다는 의견이 있습니다.

따라서 구매 전 소매 실측 사이즈를
함께 확인하는 것이 좋습니다.
```

---

# 📊 3. Resource Monitoring

AI Agent 실행 과정에서 발생하는 시스템 자원 사용량을 측정합니다.

### 측정 항목

* CPU 사용률
* Memory 사용량
* Response Time
* Agent 실행 횟수
* Agent 실행 로그
* 버튼 클릭 시점(requested)과 작업 완료 시점(completed) 기록

### 사용 데이터

```text
agent_logs
resource_logs
```

`agent_logs`에는 각 Review/Fit Agent의 `started`, `success`, `error` 상태를 남기고, `resource_logs`에는 동일한 `request_id`로 `requested`와 `completed` 이벤트를 남깁니다. Dashboard의 집계는 완료 이벤트만 사용합니다. DB 시간은 UTC로 보존하고 Dashboard에서는 KST로 변환해 표시합니다.

---

# 🔬 Agent 실행 비교

FitWise에서는 Review Agent 결과를 재사용하기 때문에 다음 상황을 비교할 수 있습니다.

### 최초 실행

```text
Purchase Suitability
        │
        ▼
Review 결과 없음
        │
        ▼
Review Agent 실행
        +
Purchase Agent 실행
        │
        ▼
CPU / Memory / Time 측정
```

### 재실행

```text
Purchase Suitability
        │
        ▼
Review 결과 있음
        │
        ▼
저장 결과 재사용
        +
Purchase Agent 실행
        │
        ▼
CPU / Memory / Time 측정
```

이를 통해 **AI 재실행과 기존 분석 결과 재사용의 자원 차이**를 비교할 수 있습니다.

예시:

| 실행 방식                    | CPU | Memory | Response Time |
| ------------------------ | --: | -----: | ------------: |
| 일반 상품 조회                 | 18% |  620MB |         0.18s |
| Review Agent 신규 분석       | 32% |  750MB |         0.72s |
| Purchase + Review 신규 분석  | 47% |  890MB |         1.24s |
| Purchase + Review 결과 재사용 | 35% |  780MB |         0.68s |

> 위 수치는 설명용 예시이며 실제 실행 시 측정된 데이터를 사용합니다.

---

# 🖥️ 화면 구성

FitWise는 총 4개의 주요 화면으로 구성합니다.

## 1. 상품 목록

```text
FitWise

[상의] [아우터] [하의]

┌─────────────┐
│ 상품 이미지  │
│ Jacket A    │
│ 119,000원   │
└─────────────┘

┌─────────────┐
│ 상품 이미지  │
│ Shirt B     │
│ 49,000원    │
└─────────────┘
```

주요 기능:

* 상품 목록
* 카테고리 조회
* 상품 카드
* 상품 상세 이동

---

## 2. 상품 상세 / 리뷰

상품 정보와 사이즈, 리뷰를 확인합니다.

### 상품 정보

* 상품명
* 브랜드
* 가격
* 카테고리
* 소재
* 색상
* Fit Type
* 상품 설명
* 상품 이미지

### 사이즈 정보

```text
[S] [M] [L]

선택: M

어깨    44cm
가슴    52.5cm
소매    60cm
총장    68cm
```

### 실행 기능

```text
[ 리뷰 AI 분석 ]

[ 구매적합도 분석 ]
```

리뷰 분석을 먼저 실행했다면 해당 결과가 저장되어 구매적합도 분석에서 다시 사용됩니다.

---

## 3. 구매적합도 결과

```text
상품
Classic Jacket

선택 사이즈
M

━━━━━━━━━━━━━━━━
 구매적합도 85점
━━━━━━━━━━━━━━━━

개인 사이즈 성공률    90%
상품 반품 안정성      85%
사이즈 안정성         88%
리뷰 적합도           76%

AI 분석
...
```

---

## 4. 관리자 Dashboard

Agent 실행 및 자원 사용량을 확인합니다.

### 주요 지표

```text
Agent 실행 횟수

Review Agent 실행 횟수

Purchase Agent 실행 횟수

Review 결과 재사용 횟수

평균 CPU

평균 Memory

평균 Response Time
```

이를 통해 **Review Agent의 중복 실행을 줄였을 때 발생하는 자원 절감 효과**도 확인할 수 있습니다.

---

# 🗄️ Database

SQLite를 사용합니다.

```text
data/fashion_shop.db
```

## 주요 테이블

| Table             | Description        |
| ----------------- | ------------------ |
| `users`           | 사용자 정보             |
| `products`        | 상품 정보              |
| `product_sizes`   | 상품 실측 사이즈          |
| `orders`          | 구매 내역              |
| `returns`         | 반품 내역              |
| `reviews`         | 원본 상품 리뷰           |
| `review_analysis` | Review Agent 분석 결과 |
| `agent_logs`      | Agent 실행 기록        |
| `resource_logs`   | 시스템 자원 사용 기록       |

---

# 🆕 review_analysis

Review Agent의 분석 결과를 저장하는 테이블입니다.

```text
review_analysis
─────────────────────────
PK analysis_id
FK product_id

positive_ratio
negative_ratio

size_positive_ratio
fit_positive_ratio

review_score
positive_keywords
negative_keywords

summary
created_at
```

역할:

```text
원본 리뷰
reviews
   │
   ▼
Review Agent
   │
   ▼
review_analysis
   │
   └── 결과 저장
          │
          ▼
Purchase Suitability Agent
```

---

# 🔗 Database 관계

```text
users
 │
 ├──────────────┐
 │              │
 ▼              ▼
orders        reviews
 │              │
 ▼              ▼
returns      products
                │
        ┌───────┴────────┐
        ▼                ▼
 product_sizes     review_analysis


users ────────────┐
                  │
products ─────────┤
                  ▼
              agent_logs
                  │
                  ▼
            resource_logs
```

---

# 🗃️ 주요 Table 구조

## users

```text
user_id       PK
name
password
```

## products

```text
product_id    PK
name
category
sub_category
price
brand
fit_type
material
color
season
description
image_url
```

## product_sizes

```text
size_id       PK
product_id    FK
size
shoulder
chest
sleeve
length
waist
thigh
```

## orders

```text
order_id      PK
user_id       FK
product_id    FK
size
quantity
ordered_at
```

## returns

```text
return_id     PK
order_id      FK
reason
detail_reason
returned_at
```

## reviews

```text
review_id     PK
user_id       FK
product_id    FK
size
rating
content
created_at
```

## review_analysis

```text
analysis_id
product_id

positive_ratio
negative_ratio

size_positive_ratio
fit_positive_ratio

review_score

positive_keywords
negative_keywords

summary
created_at
```

## agent_logs

```text
agent_log_id
user_id
product_id

agent_type
input_size
result_score
response_time
created_at
```

Agent Type:

```text
general
review
fit
```

## resource_logs

```text
resource_id
agent_log_id

action
agent_used

cpu_percent
memory_mb
response_time
created_at
```

---

# 👥 역할 분담

| 담당     | 핵심 역할                           | 주요 담당 데이터                                       |
| ------ | ------------------------------- | ----------------------------------------------- |
| **김규연** | DB + Purchase Suitability Agent | users, orders, returns, products, product_sizes |
| **최재우** | 상품 목록 + Review Analysis Agent   | products, reviews, review_analysis              |
| **이동원** | 상품 상세 + Resource Monitoring     | agent_logs, resource_logs                       |

### 👤 김규연 — DB / 구매적합도

* DB 구조 관리
* 샘플 데이터
* 개인 구매 성공률
* 개인 반품 분석
* 상품 반품률
* 사이즈별 반품률
* 리뷰 적합도 결합
* 최종 구매적합도 계산

### 👤 최재우 — 상품 / Review Agent

* 상품 목록
* 상품 카테고리
* 리뷰 표시
* Review Analysis Agent
* 리뷰 키워드 분석
* 리뷰 적합도 계산
* `review_analysis` 저장
* 기존 분석 결과 조회

### 👤 이동원 — 상품 상세 / Monitoring

* 상품 상세 화면
* 사이즈 선택
* 구매적합도 결과
* CPU 측정
* Memory 측정
* Response Time 측정
* Agent 실행 로그
* 관리자 Dashboard

---

# 🌿 Git Branch

```text
main
│
├── feature/review-agent
│
├── feature/fit-agent
│
└── feature/admin-dashboard
```

각 기능은 Feature Branch에서 개발한 후 Pull Request를 통해 `main`에 병합합니다.

---

# 📁 프로젝트 구조

```text
FitWise/
│
├── app/
│   ├── review_agent/
│   ├── fit_agent/
│   └── monitoring/
│
├── data/
│   └── fashion_shop.db
│
├── static/
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/
│   ├── products.html
│   ├── product_detail.html
│   ├── fit_result.html
│   └── admin_dashboard.html
│
├── README.md
├── requirements.txt
└── .gitignore
```

---

# 🛠️ Tech Stack

**Frontend**

```text
HTML
CSS
JavaScript
```

**Backend / Data**

```text
Python
SQLite
Pandas
```

**AI Agent**

```text
Python
LLM API
```

**Resource Monitoring**

```text
psutil
Python time
```

**Version Control**

```text
Git
GitHub
```

---

# 🔄 전체 서비스 흐름

```text
                    사용자
                      │
                      ▼
                   상품 목록
                      │
                      ▼
                   상품 상세
                      │
                상품 / 사이즈 선택
                      │
          ┌───────────┴───────────┐
          │                       │
          ▼                       ▼
   리뷰 AI 분석             구매적합도 분석
          │                       │
          ▼                       ▼
   Review 결과 있음?        Review 결과 있음?
          │                       │
     ┌────┴────┐             ┌────┴────┐
    YES       NO            YES       NO
     │         │             │         │
     │    Review Agent       │    Review Agent
     │         │             │         │
     │         ▼             │         ▼
     │      결과 저장         │      결과 저장
     │         │             │         │
     └────┬────┘             └────┬────┘
          │                       │
          ▼                       ▼
     리뷰 결과 표시         Purchase Suitability
                                  Agent
                                    │
                       ┌────────────┼────────────┐
                       ▼            ▼            ▼
                    개인 이력    반품 데이터    리뷰 분석
                       │            │            │
                       └────────────┼────────────┘
                                    ▼
                               구매적합도
                                    │
                                    ▼
                               사용자 결과


                    Agent 실행
                        │
                        ▼
                    agent_logs
                        │
                        ▼
                  resource_logs
                        │
                ┌───────┼─────────┐
                ▼       ▼         ▼
               CPU    Memory   Response Time
                        │
                        ▼
                  Admin Dashboard
```

---

# 🎯 프로젝트 핵심

### 사용자 관점

> 개인의 구매 경험, 상품 반품 데이터, 리뷰를 종합하여 구매 전에 선택한 상품과 사이즈가 자신에게 얼마나 적합한지 확인할 수 있도록 지원합니다.

### AI 관점

> Review Agent가 리뷰를 분석하고, Purchase Suitability Agent가 개인·상품·반품 데이터와 리뷰 분석 결과를 종합하여 최종 구매적합도를 제공합니다.

### 데이터 관점

> Review Agent의 분석 결과를 DB에 저장하여 동일한 분석을 반복하지 않고 여러 기능에서 재사용합니다.

### 시스템 관점

> AI Agent의 중복 실행을 줄이고 CPU, Memory, Response Time을 측정하여 **Agent 결과 재사용에 따른 시스템 자원 차이**를 확인합니다.

---

# 💡 FitWise

**Better Fit. Smarter Purchase. Fewer Returns.**

> **Analyze Once, Reuse Many Times.**

리뷰를 한 번 분석하고 결과를 재사용하여 사용자에게 더 효율적인 AI 구매적합도 서비스를 제공합니다.
