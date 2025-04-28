import discord
from config import BOT_TOKEN
from utils.file_handler import load_data, save_data
import datetime

intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

class StudyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=intents)
        self.tree = discord.app_commands.CommandTree(self)
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
        "/일간기록 - 오늘 공부한 시간\n"
        "/주간기록 - 이번 주 공부한 시간\n"
        "/월간기록 - 이번 달 공부한 시간\n"
        "/도움말 - 명령어 목록 보여주기"
    )
    await interaction.response.send_message(help_text)

bot.run(BOT_TOKEN)
