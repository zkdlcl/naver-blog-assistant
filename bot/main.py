import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import discord
from core.config import load_config
from core.naver_blog_monitor import DEFAULT_RANK_SURFACES, NaverBlogMonitor, format_posts_for_discord
from core.naver_blog_monitor import format_rank_for_discord, format_rank_results_for_discord

config = load_config()
TOKEN = config.discord_token

# 디스코드 인텐트 설정
intents = discord.Intents.default()
intents.message_content = True  # 메시지 내용을 읽기 위한 권한

# 봇 클라이언트 생성
client = discord.Client(intents=intents)
blog_monitor = NaverBlogMonitor()


HELP_TEXT = """사용 가능한 명령어
`!ping` - 봇 응답 확인
`!blog 검색어` - 네이버 블로그 최신 글 3개 확인
`!rank 검색어` - 통합검색, 블로그탭, 블로그 섹션 기준 순위 확인
`!rank-pc 검색어` - PC 통합검색 순위 확인
`!rank-mobile 검색어` - 모바일 통합검색 순위 확인
`!rank-blog 검색어` - PC 블로그탭 순위 확인
`!rank-mblog 검색어` - 모바일 블로그탭 순위 확인
`!rank-section 검색어` - 네이버 블로그 섹션 순위 확인
"""


@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    print('Vibe Coding Harness Bot is now actively listening for prompts...')
    print(f'Target blog: {config.target_blog_id or "not configured"}')

@client.event
async def on_message(message):
    # 봇 자신이 보낸 메시지는 무시
    if message.author == client.user:
        return

    # 메시지를 터미널에 프린트
    channel = message.channel.name if hasattr(message.channel, 'name') else "DM"
    content = message.content.strip()
    print(f"[{channel}] {message.author.name}: {content}")

    if content in {'!help', '!도움말'}:
        print("Handling command: help")
        await message.channel.send(HELP_TEXT)
        return

    # 간단한 핑퐁 테스트
    if content.startswith('!ping'):
        print("Handling command: ping")
        await message.channel.send('Pong! Harness bot is active.')
        return

    if content.startswith('!blog'):
        print("Handling command: blog")
        keyword = content.removeprefix('!blog').strip()
        if not keyword:
            await message.channel.send('사용법: `!blog 검색어`')
            return

        await message.channel.send(f'`{keyword}` 블로그 검색을 시작합니다.')
        try:
            posts = await blog_monitor.search(keyword, limit=3)
        except Exception as exc:
            await message.channel.send(f'블로그 검색 실패: `{exc.__class__.__name__}`')
            print(f"Blog monitor error: {exc}")
            return

        await message.channel.send(format_posts_for_discord(keyword, posts))
        return

    rank_commands = {
        '!rank-pc': ('rank-pc', ('desktop',)),
        '!rank-mobile': ('rank-mobile', ('mobile',)),
        '!rank-mblog': ('rank-mblog', ('mobile_blog',)),
        '!rank-blog': ('rank-blog', ('desktop_blog',)),
        '!rank-section': ('rank-section', ('blog_section',)),
        '!rank': ('rank', DEFAULT_RANK_SURFACES),
    }

    for command, (command_name, surfaces) in rank_commands.items():
        if not content.startswith(command):
            continue

        print(f"Handling command: {command_name}")
        keyword = content.removeprefix(command).strip()
        if not keyword:
            await message.channel.send(f'사용법: `{command} 검색어`')
            return

        if not config.has_target_blog:
            await message.channel.send('`.env`에 `TARGET_BLOG_ID` 또는 `TARGET_BLOG_URL`을 먼저 설정해야 합니다.')
            return

        await message.channel.send(f'`{keyword}`에서 `{config.target_blog_id}` 블로그 순위를 확인합니다.')
        try:
            if len(surfaces) == 1:
                result = await blog_monitor.rank_keyword(
                    keyword,
                    config.target_blog_id,
                    limit=30,
                    surface=surfaces[0],
                )
                response = format_rank_for_discord(result)
            else:
                results = await blog_monitor.rank_keyword_all(
                    keyword,
                    config.target_blog_id,
                    limit=30,
                    surfaces=surfaces,
                )
                response = format_rank_results_for_discord(results)
        except Exception as exc:
            await message.channel.send(f'순위 확인 실패: `{exc.__class__.__name__}`')
            print(f"Rank tracker error: {exc}")
            return

        await message.channel.send(response)
        return

    if content.startswith('!'):
        print("Handling command: unknown")
        await message.channel.send('알 수 없는 명령어입니다. `!help`를 입력해 사용법을 확인하세요.')

if __name__ == "__main__":
    if TOKEN:
        client.run(TOKEN)
    else:
        print("ERROR: DISCORD_TOKEN is not set in .env file.")
