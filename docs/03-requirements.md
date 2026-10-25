# 요구사항 명세

## 목표

가족의 네이버 블로그 글이 특정 키워드에서 네이버 검색 기준별로 몇 위에 노출되는지 확인한다.

## 사용자 시나리오

### Discord에서 순위 확인

사용자는 Discord에서 키워드를 입력한다.

```text
!rank 예시 키워드
```

봇은 아래 검색 표면을 확인한다.

1. PC 통합검색
2. 모바일 통합검색
3. PC 블로그탭
4. 모바일 블로그탭
5. 네이버 블로그 섹션

봇은 각 표면별 순위와 글 URL을 응답한다.

### 검색 표면별 단독 확인

PC 통합검색만 확인한다.

```text
!rank-pc 예시 키워드
```

모바일 통합검색만 확인한다.

```text
!rank-mobile 예시 키워드
```

PC 블로그탭만 확인한다.

```text
!rank-blog 예시 키워드
```

모바일 블로그탭만 확인한다.

```text
!rank-mblog 예시 키워드
```

네이버 블로그 섹션만 확인한다.

```text
!rank-section 예시 키워드
```

## 환경변수

필수:

```env
DISCORD_TOKEN=...
TARGET_BLOG_ID=your_blog_id
```

`TARGET_BLOG_ID` 대신 URL 전체를 쓸 수 있다.

```env
TARGET_BLOG_URL=https://blog.naver.com/your_blog_id
```

선택:

```env
BROWSER_HEADLESS=true
BROWSER_LOCALE=ko-KR
BROWSER_TIMEZONE=Asia/Seoul
```

## 순위 판정 기준

현재 MVP는 검색 결과에서 발견되는 개별 블로그 글 링크를 순서대로 세어 순위를 계산한다.

### 공통 기준

순위는 네이버 검색 결과 DOM에서 발견되는 개별 블로그 글 링크의 등장 순서를 기준으로 한다.

예를 들어 검색 결과에서 블로그 글 링크가 아래 순서로 발견되면:

```text
1. 다른 블로그 글
2. 다른 블로그 글
3. your_blog_id 글
```

`your_blog_id`의 순위는 3위로 판정한다.

프로필 링크, 블로그 홈 링크, 네이버 블로그 섹션 링크는 순위에서 제외한다.

실제 글 URL로 인정하는 형식:

```text
https://blog.naver.com/{blogId}/{postNo}
https://m.blog.naver.com/{blogId}/{postNo}
```

내부 저장 및 비교 시 모바일 URL은 PC URL로 정규화한다.

```text
https://m.blog.naver.com/your_blog_id/000000000000
-> https://blog.naver.com/your_blog_id/000000000000
```

### PC 통합검색 기준

PC 통합검색은 아래 URL 형식의 결과 페이지를 본다.

```text
https://search.naver.com/search.naver?where=nexearch&query={keyword}
```

검색 결과 페이지에 노출된 개별 블로그 글 링크를 위에서부터 순서대로 센다.

현재 Discord 명령에서는 최대 30개의 블로그 글 링크를 확인한다.

### 모바일 통합검색 기준

모바일 통합검색은 아래 URL 형식의 결과 페이지를 본다.

```text
https://m.search.naver.com/search.naver?where=m&query={keyword}
```

모바일 결과에서는 `m.blog.naver.com` 링크가 나올 수 있으며, 내부 비교 시 `blog.naver.com`으로 정규화한다.

현재 Discord 명령에서는 최대 30개의 블로그 글 링크를 확인한다.

### 찾지 못한 경우

최대 확인 개수 안에서 대상 블로그 글이 발견되지 않으면 순위권 밖으로 처리한다.

봇 응답 예시:

```text
[PC 통합검색] `예시 키워드` 검색 결과 30개 안에서 `your_blog_id` 블로그 글을 찾지 못했습니다.
```

주의: 이 메시지는 네이버 전체 검색 결과에 글이 없다는 뜻이 아니라, 현재 파서가 확인한 최대 30개의 블로그 글 링크 안에서 찾지 못했다는 뜻이다.

## 현재 제외 범위

1. 로그인 기반 개인화 순위
2. 위치 기반 검색 결과 차이 보정
3. 전일 대비 순위 변동 저장
4. Google Sheets 연동
5. Streamlit 대시보드
6. 키워드 자동 추천

위 항목은 다음 단계에서 구현한다.
