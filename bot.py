import discord
from discord.ext import commands
from config import BOT_TOKEN
from utils.file_handler import load_data, save_data
import datetime
from matplotlib import pyplot as plt
import io
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

class StudyBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="/", intents=intents)
        self.study_records = {}
        self.voice_join_times = {}

    async def setup_hook(self):
        await self.tree.sync()

    async def on_ready(self):
        print(f'Logged in as {self.user}!')
        self.study_records = load_data()

    async def on_voice_state_update(self, member, before, after):
        now = datetime.datetime.now()
        if before.channel is None and after.channel is not None:
            self.voice_join_times[member.id] = now
        elif before.channel is not None and after.channel is None:
            start_time = self.voice_join_times.pop(member.id, None)
            if start_time:
                duration = (now - start_time).total_seconds()
                date_str = now.strftime('%Y-%m-%d')
                user_record = self.study_records.get(str(member.id), {})
                user_record[date_str] = user_record.get(date_str, 0) + duration
                self.study_records[str(member.id)] = user_record
                save_data(self.study_records)

bot = StudyBot()

@bot.tree.command(name="일간기록", description="오늘 공부한 시간을 보여줍니다.")
async def daily_record(interaction: discord.Interaction):
    now = datetime.datetime.now()
    user_record = bot.study_records.get(str(interaction.user.id), {})
    seconds = user_record.get(now.strftime('%Y-%m-%d'), 0)
    await interaction.response.send_message(f"오늘 공부한 시간: {seconds//3600}시간 {(seconds%3600)//60}분")

@bot.tree.command(name="주간기록", description="이번 주 공부한 시간을 보여줍니다.")
async def weekly_record(interaction: discord.Interaction):
    now = datetime.datetime.now()
    user_record = bot.study_records.get(str(interaction.user.id), {})
    total = 0
    for i in range(7):
        day = (now - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        total += user_record.get(day, 0)
    await interaction.response.send_message(f"이번 주 공부한 시간: {total//3600}시간 {(total%3600)//60}분")

@bot.tree.command(name="월간기록", description="이번 달 공부한 시간을 보여줍니다.")
async def monthly_record(interaction: discord.Interaction):
    now = datetime.datetime.now()
    user_record = bot.study_records.get(str(interaction.user.id), {})
    total = 0
    for date_str, seconds in user_record.items():
        if date_str.startswith(now.strftime('%Y-%m')):
            total += seconds
    await interaction.response.send_message(f"이번 달 공부한 시간: {total//3600}시간 {(total%3600)//60}분")

@bot.tree.command(name="도움말", description="사용 가능한 명령어 목록을 보여줍니다.")
async def help_command(interaction: discord.Interaction):
    help_text = (
        "사용할 수 있는 명령어 목록:\n"
        "/일간기록 - 오늘 공부한 시간 보기\n"
        "/주간기록 - 이번 주 공부한 시간 보기\n"
        "/월간기록 - 이번 달 공부한 시간 보기\n"
        "/히스토리 [7/30] - 최근 공부 기록 그래프로 보기\n"
        "/뽀모도로 [집중시간] [쉬는시간] - 뽀모도로 타이머 시작하기\n"
        "/집중종료 - 현재 진행 중인 타이머 종료\n"
        "/도움말 - 명령어 목록 보여주기"
    )
    await interaction.response.send_message(help_text, ephemeral=True)

@bot.tree.command(name="히스토리", description="최근 공부 기록을 그래프로 보여줍니다.")
@app_commands.describe(days="며칠 동안의 공부 기록을 보고 싶나요? (7 또는 30)")
async def study_history(interaction: discord.Interaction, days: int = 7):
    if days not in (7, 30):
        await interaction.response.send_message("7 또는 30만 입력할 수 있어요!", ephemeral=True)
        return

    now = datetime.datetime.now()
    user_record = bot.study_records.get(str(interaction.user.id), {})

    dates = []
    times = []

    for i in range(days-1, -1, -1):
        day = (now - datetime.timedelta(days=i)).strftime('%Y-%m-%d')
        dates.append(day[5:])  # MM-DD만 표시
        times.append(user_record.get(day, 0) / 3600)  # 초를 시간으로 변환

    # 그래프 그리기
    plt.figure(figsize=(10, 5))
    plt.bar(dates, times)
    plt.title(f'Recent {days} Days of Study Time')
    plt.xlabel('Day')
    plt.ylabel('Study Time (Hour)')
    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = io.BytesIO()
    plt.savefig(buffer, format='png')
    buffer.seek(0)
    plt.close()

    file = discord.File(fp=buffer, filename='history.png')
    await interaction.response.send_message(file=file)

    import asyncio

@bot.tree.command(name="뽀모도로", description="자유롭게 집중 시간과 휴식 시간을 설정합니다.")
@app_commands.describe(focus_minutes="집중 시간 (분)", rest_minutes="휴식 시간 (분)")
async def pomodoro(interaction: discord.Interaction, focus_minutes: int, rest_minutes: int):
    if focus_minutes <= 0 or rest_minutes <= 0:
        await interaction.response.send_message(
            "집중 시간과 휴식 시간은 1분 이상이어야 해요!", ephemeral=True
        )
        return

    await interaction.response.send_message(
        f"🎯 {focus_minutes}분 집중 시작합니다! 끝나면 {rest_minutes}분 쉬세요!", ephemeral=True
    )

    # 공부시간 타이머
    await asyncio.sleep(focus_minutes * 60)

    await interaction.followup.send(
        f"⏰ {focus_minutes}분 집중 끝! 🛌 {rest_minutes}분 쉬는 시간 시작!", ephemeral=True
    )

    # 쉬는시간 타이머
    await asyncio.sleep(rest_minutes * 60)

    await interaction.followup.send(
        f"✅ {rest_minutes}분 쉬는 시간 끝났어요! 다시 집중할 준비 완료! 🔥", ephemeral=True
    )


bot.run(BOT_TOKEN)
