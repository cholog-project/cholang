import datetime
import os
import uuid

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

from reminders import Reminder, save_reminders_to_file, load_reminders_from_file, schedule_reminder, KOREAN_DAYS_OF_WEEK

load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
scheduler = AsyncIOScheduler()


class TemplateModal(discord.ui.Modal, title="질문 양식 입력"):
    def __init__(self, template_text):
        super().__init__()
        self.template_text = template_text
        self.text_input = discord.ui.TextInput(
            label="질문 내용",
            style=discord.TextStyle.long,
            placeholder="질문을 작성하세요",
            default=template_text
        )
        self.add_item(self.text_input)

    async def on_submit(self, interaction: discord.Interaction):
        user_id = interaction.user.id
        channel = interaction.channel
        try:
            if channel:
                await channel.send(f"<@{user_id}>님의 질문이 제출되었습니다!\n{self.text_input.value}")
                await interaction.response.send_message("질문이 작성되었어요!", ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


class TemplateSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        select = TemplateSelect()
        self.add_item(select)
        self.add_item(UseTemplateButton(select))


def log_template_selection(channel, template_name):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = (f"{timestamp} - Guild [ ID: {channel.guild.id} | Name: {channel.guild.name} ] - "
                 f"Channel [ ID: {channel.id} | Name: {channel.name} ] - "
                 f"Template: {template_name}\n")

    with open("question_log.txt", "a", encoding="utf-8") as log_file:
        log_file.write(log_entry)


class TemplateSelect(discord.ui.Select):
    def __init__(self):
        self.selected_template = ""
        options = [
            discord.SelectOption(label="구체적인 질문 템플릿", description="첫 번째 양식"),
            discord.SelectOption(label="간단한 질문 템플릿", description="두 번째 양식"),
            discord.SelectOption(label="이론 질문 템플릿", description="세 번째 양식"),
            discord.SelectOption(label="자유 양식", description="네 번째 양식")
        ]
        super().__init__(placeholder="질문 양식을 선택하세요", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        log_template_selection(interaction.channel, self.values[0])

        templateEmbed = discord.Embed(title="선택한 질문 템플릿", color=discord.Color.blue())
        if self.values[0] == "구체적인 질문 템플릿":
            self.selected_template = (
                "1. **초록스터디 강의 제목** : ex) 학습 테스트로 배우는 스프링 기초\n"
                "2. **진행 중인 단계** : ex) Spring MVC(인증) - 2단계\n"
                "3. **해결하려는 문제가 무엇인가요?** : ex) 예약 생성 시, NPE가 발생하고 있습니다.\n"
                "4. **이를 해결하기 위해 본인이 한 시도** : ex) 예약을 생성할 때, 객체를 참조하고 있는 부분을 확인해보았습니다.\n"
                "5. **코드로 첨부하기 어려운 내용은 스크린샷을 통해 첨부해주세요.**\n"
                "   - 답변자가 참고할 만한 코드 첨부(선택)\n"
                "   - 답변자가 참고할 만한 에러 메시지(선택)\n"
                "6. **원하는 답변을 선택해주세요.**\n"
                "   - [ ] 해결할 수 있는 구체적인 방안을 원합니다\n"
                "   - [ ] 해결을 위한 힌트를 주세요\n"
                "7. **질문에 대한 제목 작성** : **1 ~ 5번에서 작성한 내용을 토대로 질문의 제목을 작성**"
            )
        elif self.values[0] == "간단한 질문 템플릿":
            self.selected_template = (
                "**1. 문제 요약**\n"
                "- **문제:** (예: API 호출 시 401 오류 발생)\n"
                "**2. 상황 설명**\n"
                "- **작업:** (예: 로그인 기능 구현 중)\n"
                "- **파일:** (예: `login.js`)\n"
                "**3. 시도한 방법**\n"
                "- (예: 요청 형식 변경, CORS 설정 수정)\n"
                "**4. 최종 질문**\n"
                "- **질문:** (예: '왜 401 오류가 발생하나요?')"
            )
        elif self.values[0] == "이론 질문 템플릿":
            self.selected_template = (
                "1. **궁금증이 생긴 상황을 알려주세요!**\n"
                "   - ex) 예외처리를 하고, 해당 예외상황이 되었을 때 스프링이 어떻게 동작하는지 궁금합니다\n"
                "2. **질문자님이 생각하시는 질문의 키워드를 알려주세요!**\n"
                "   - ex) 예외처리"
            )
        elif self.values[0] == "자유 양식":
            self.selected_template = "자유롭게 질문을 작성하세요."

        templateEmbed.description = self.selected_template

        try:
            await interaction.response.edit_message(view=self.view, embed=templateEmbed)
        except discord.errors.NotFound:
            await interaction.response.send_message(embed=templateEmbed, ephemeral=True)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")


class UseTemplateButton(discord.ui.Button):
    def __init__(self, select: TemplateSelect):
        super().__init__(label="양식 사용하기", style=discord.ButtonStyle.primary)
        self.select = select

    async def callback(self, interaction: discord.Interaction):
        if self.select.selected_template:
            await interaction.response.send_modal(TemplateModal(self.select.selected_template))
        else:
            await interaction.response.send_message("먼저 양식을 선택해주세요.", ephemeral=True)


class SetupClient(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.synced = False
        self.reminders = []

    async def setup_hook(self) -> None:
        if not self.synced:
            await self.tree.sync()
            self.synced = True

    async def on_ready(self) -> None:
        await self.change_presence(activity=discord.Game(name="촐랑거리기"))
        scheduler.start()
        self.reminders = load_reminders_from_file(scheduler, self)


bot = SetupClient()


@bot.tree.command(name="질문", description="질문 양식을 띄웁니다.")
async def question_command(interaction: discord.Interaction):
    view = TemplateSelectView()
    await interaction.response.send_message("질문 양식을 선택하세요.", view=view, ephemeral=True)


@bot.tree.command(name="remind", description="지정된 요일과 시간에 리마인더를 생성합니다.")
@app_commands.describe(
    day="리마인더를 설정할 요일 (예: 월요일, 화요일)",
    time="리마인더 시간을 HH:MM 형식으로 설정 (24시간 형식)",
    interval="리마인더 반복 횟수 (설정하지 않으면 무한 반복)",
    content="리마인더 내용"
)
async def remind_command(interaction: discord.Interaction, day: str, time: str, content: str,
                         interval: int = -1) -> None:
    days = [d.strip() for d in day.split(',')]
    cron_days = []
    for d in days:
        if d not in KOREAN_DAYS_OF_WEEK:
            await interaction.response.send_message(f"유효하지 않은 요일 '{d}'입니다. 올바른 요일을 지정하세요.", ephemeral=True)
            return
        cron_days.append(KOREAN_DAYS_OF_WEEK[d])

    try:
        reminder_time = datetime.datetime.strptime(time, "%H:%M")
    except ValueError:
        await interaction.response.send_message("시간 형식이 잘못되었습니다. HH:MM (24시간 형식)으로 입력하세요.", ephemeral=True)
        return

    job_id = f"{uuid.uuid1().hex}"

    reminder = Reminder(
        user_id=interaction.user.id,
        channel_id=interaction.channel_id,
        day=','.join(days),
        time=time,
        interval=interval,
        content=content,
        job_id=job_id
    )

    bot.reminders.append(reminder)
    schedule_reminder(reminder, scheduler, bot)
    save_reminders_to_file(bot.reminders)

    await interaction.response.send_message(
        f"{','.join(days)} {time}에 '{content}' 내용으로 리마인더가 설정되었습니다. 반복 횟수: {'무한정' if interval == -1 else interval}",
        ephemeral=True)


@bot.tree.command(name="remind-list", description="설정된 모든 리마인더 목록을 확인합니다.")
async def remind_list_command(interaction: discord.Interaction) -> None:
    channel_reminders = [r for r in bot.reminders if r.channel_id == interaction.channel_id]
    if not channel_reminders:
        await interaction.response.send_message("설정된 리마인더가 없습니다.", ephemeral=True)
        return

    reminder_messages = []
    for r in channel_reminders:
        repeat_info = "무한정" if r.interval == -1 else f"{r.interval}"
        reminder_messages.append(f"{r.day} {r.time} - {r.content} (반복횟수: {repeat_info})")

    await interaction.response.send_message("설정된 리마인더 목록:\n" + "\n".join(reminder_messages), ephemeral=True)


if TOKEN:
    bot.run(TOKEN)
else:
    print("Token not found. Please set the DISCORD_BOT_TOKEN environment variable.")
