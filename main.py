import asyncio
import datetime
import json
import uuid
from typing import List
from dotenv import load_dotenv
import os

import discord
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord import app_commands
from discord.ext import commands

load_dotenv()
REMINDER_FILE_PATH = 'reminders.json'

TOKEN = os.getenv('DISCORD_BOT_TOKEN')

# Initialize the scheduler
scheduler = AsyncIOScheduler()


class Reminder:
    def __init__(self, user_id: int, channel_id: int, day: str, time: str, interval: int, content: str, job_id: str):
        self.user_id = user_id
        self.channel_id = channel_id
        self.day = day
        self.time = time
        self.interval = interval
        self.content = content
        self.job_id = job_id

    def to_dict(self):
        return {
            'user_id': self.user_id,
            'channel_id': self.channel_id,
            'day': self.day,
            'time': self.time,
            'interval': self.interval,
            'content': self.content,
            'job_id': self.job_id
        }

    @staticmethod
    def from_dict(data):
        return Reminder(
            user_id=data['user_id'],
            channel_id=data['channel_id'],
            day=data['day'],
            time=data['time'],
            interval=data['interval'],
            content=data['content'],
            job_id=data['job_id']
        )

    async def send_reminder(self, bot: commands.Bot) -> None:
        channel = bot.get_channel(self.channel_id)
        if channel:
            await channel.send(f"{self.content}")

    def decrement_interval(self) -> int:
        if self.interval > 0:
            self.interval -= 1
        return self.interval


class SetupClient(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix='!', intents=intents)
        self.synced = False

    async def setup_hook(self) -> None:
        if not self.synced:
            await self.tree.sync()
            self.synced = True

    async def on_ready(self) -> None:
        await self.change_presence(activity=discord.CustomActivity(name="촐랑거리는중"))
        scheduler.start()
        load_reminders_from_file()


bot = SetupClient()

# Map Korean day names to cron day of week values
KOREAN_DAYS_OF_WEEK = {
    "월요일": "0",
    "화요일": "1",
    "수요일": "2",
    "목요일": "3",
    "금요일": "4",
    "토요일": "5",
    "일요일": "6"
}

reminders: List[Reminder] = []


def save_reminders_to_file():
    with open(REMINDER_FILE_PATH, 'w', encoding='utf-8') as file:
        json.dump([reminder.to_dict() for reminder in reminders], file, ensure_ascii=False, indent=4)


def load_reminders_from_file():
    try:
        with open(REMINDER_FILE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for reminder_data in data:
                reminder = Reminder.from_dict(reminder_data)
                reminders.append(reminder)
                schedule_reminder(reminder)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass


def schedule_reminder(reminder: Reminder):
    cron_trigger = CronTrigger(
        hour=int(reminder.time.split(':')[0]),
        minute=int(reminder.time.split(':')[1]),
        day_of_week=','.join([KOREAN_DAYS_OF_WEEK[day] for day in reminder.day.split(',')])
    )

    async def reminder_action(_reminder: Reminder) -> None:
        await _reminder.send_reminder(bot)
        if _reminder.decrement_interval() == 0:
            scheduler.remove_job(_reminder.job_id)
            reminders.remove(_reminder)
            save_reminders_to_file()

    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(
            reminder_action(reminder),
            bot.loop
        ),
        cron_trigger,
        id=reminder.job_id
    )


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

    reminders.append(reminder)
    schedule_reminder(reminder)
    save_reminders_to_file()

    await interaction.response.send_message(
        f"{','.join(days)} {time}에 '{content}' 내용으로 리마인더가 설정되었습니다. 반복 횟수: {'무한정' if interval == -1 else interval}",
        ephemeral=True)


class ReminderButton(discord.ui.Button):
    def __init__(self, reminder: Reminder):
        super().__init__(label="삭제하기", style=discord.ButtonStyle.danger)
        self.reminder = reminder

    async def callback(self, interaction: discord.Interaction):
        scheduler.remove_job(self.reminder.job_id)
        reminders.remove(self.reminder)
        save_reminders_to_file()
        await interaction.response.send_message("리마인더가 삭제되었습니다.", ephemeral=True)


class ReminderView(discord.ui.View):
    def __init__(self, reminder: Reminder):
        super().__init__()
        self.add_item(ReminderButton(reminder))


async def update_reminder_list(interaction: discord.Interaction) -> None:
    channel_reminders = [r for r in reminders if r.channel_id == interaction.channel_id]
    if not channel_reminders:
        await interaction.edit_original_response(content="설정된 리마인더가 없습니다.", view=None)
        return

    reminder_messages = []
    views = []
    for r in channel_reminders:
        repeat_info = "무한정" if r.interval == -1 else f"{r.interval}"
        reminder_messages.append(f"{r.day} {r.time} - {r.content} (반복횟수: {repeat_info})")
        views.append(ReminderView(r))

    await interaction.edit_original_response(content="설정된 리마인더 목록:\n" + "\n".join(reminder_messages),
                                             view=views[0] if views else None)


@bot.tree.command(name="remind-list", description="설정된 모든 리마인더 목록을 확인합니다.")
async def remind_list_command(interaction: discord.Interaction) -> None:
    await interaction.response.send_message("리마인더 목록을 불러오는 중...", ephemeral=True)
    await update_reminder_list(interaction)


if TOKEN:
    bot.run(TOKEN)
else:
    print("Token not found. Please set the DISCORD_BOT_TOKEN environment variable.")
