"""
Tistory 자동 포스팅 스크립트 (Playwright 기반)

사용법:
  python post_tistory.py

필수 환경변수:
  KAKAO_EMAIL    - 카카오 로그인 이메일
  KAKAO_PASSWORD - 카카오 로그인 비밀번호
  BLOG_NAME      - 티스토리 블로그 이름 (예: myblog → myblog.tistory.com)

선택 환경변수:
  POST_TITLE     - 포스팅 제목 (기본값: 스크립트 내 DEFAULT_TITLE)
  POST_CONTENT   - 포스팅 내용 HTML (기본값: 스크립트 내 DEFAULT_CONTENT)
  POST_TAGS      - 태그 (쉼표 구분, 예: "Python,자동화,블로그")
"""

import asyncio
import os
import sys
from datetime import datetime
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# ── 기본 포스팅 내용 (환경변수로 덮어쓸 수 있음) ──────────────────────────────
DEFAULT_TITLE = f"자동 포스팅 - {datetime.now().strftime('%Y-%m-%d')}"
DEFAULT_CONTENT = """
<h2>자동으로 작성된 포스팅입니다</h2>
<p>이 글은 Playwright와 GitHub Actions를 이용해 자동으로 작성되었습니다.</p>
<ul>
  <li>작성 시각: {timestamp}</li>
  <li>작성 도구: Python + Playwright</li>
</ul>
""".format(timestamp=datetime.now().strftime('%Y-%m-%d %H:%M:%S'))


async def login_kakao(page, email: str, password: str):
    """카카오 계정으로 티스토리 로그인"""
    print("로그인 페이지로 이동 중...")
    await page.goto("https://www.tistory.com/auth/login", wait_until="networkidle")

    # 카카오로 로그인 버튼 클릭
    await page.click(".btn_login.link_kakao_id")
    await page.wait_for_load_state("networkidle")

    # 이메일/비밀번호 입력
    print("카카오 계정 입력 중...")
    await page.fill("#loginId--1", email)
    await page.fill("#password--2", password)
    await page.click(".btn_g.highlight.submit")
    await page.wait_for_load_state("networkidle")

    # 로그인 성공 확인
    if "tistory.com" in page.url:
        print("로그인 성공")
    else:
        raise RuntimeError(f"로그인 실패: 현재 URL = {page.url}")


async def post_to_tistory(title: str, content: str, tags: str = ""):
    """티스토리에 글 포스팅"""
    email = os.environ.get("KAKAO_EMAIL")
    password = os.environ.get("KAKAO_PASSWORD")
    blog_name = os.environ.get("BLOG_NAME")

    if not all([email, password, blog_name]):
        print("오류: 다음 환경변수를 설정해주세요:")
        print("  KAKAO_EMAIL, KAKAO_PASSWORD, BLOG_NAME")
        sys.exit(1)

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            )
        )
        page = await context.new_page()

        try:
            await login_kakao(page, email, password)

            # 새 글쓰기 페이지 이동
            write_url = f"https://{blog_name}.tistory.com/manage/newpost"
            print(f"글쓰기 페이지 이동 중: {write_url}")
            await page.goto(write_url, wait_until="networkidle")

            # 제목 입력
            await page.wait_for_selector("#post-title-inp", timeout=10000)
            await page.fill("#post-title-inp", title)
            print(f"제목 입력 완료: {title}")

            # HTML 모드로 전환하여 내용 입력
            await page.click(".toolbar_item.tistory-btn-bold ~ .toolbar_item, button:has-text('HTML')", timeout=5000)
            await page.wait_for_timeout(500)
            editor = page.frame_locator("#editor-content-iframe")
            body = editor.locator("body")
            await body.click()
            await page.keyboard.press("Control+a")
            await page.keyboard.type(content)
            print("내용 입력 완료")

            # 태그 입력
            if tags:
                await page.fill("#tagText", tags)
                await page.keyboard.press("Enter")
                print(f"태그 입력 완료: {tags}")

            # 발행 버튼 클릭
            await page.click(".btn_publish")
            await page.wait_for_selector(".layer-post-publish", timeout=10000)

            # 공개 발행 확인
            await page.click(".btn_pop_sub.btn_publish")
            await page.wait_for_load_state("networkidle")

            print(f"포스팅 완료! URL: {page.url}")
            return page.url

        except PlaywrightTimeoutError as e:
            print(f"타임아웃 오류: {e}")
            await page.screenshot(path="error_screenshot.png")
            print("오류 스크린샷 저장: error_screenshot.png")
            raise
        finally:
            await browser.close()


async def main():
    title = os.environ.get("POST_TITLE", DEFAULT_TITLE)
    content = os.environ.get("POST_CONTENT", DEFAULT_CONTENT)
    tags = os.environ.get("POST_TAGS", "자동화,Python,Playwright")

    print(f"포스팅 시작: {title}")
    url = await post_to_tistory(title, content, tags)
    print(f"완료: {url}")


if __name__ == "__main__":
    asyncio.run(main())
