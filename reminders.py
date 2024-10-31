import asyncio
import json
from typing import List

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from discord.ext import commands

REMINDER_FILE_PATH = 'reminders.json'

KOREAN_DAYS_OF_WEEK = {
    "월요일": "0",
    "화요일": "1",
    "수요일": "2",
    "목요일": "3",
    "금요일": "4",
    "토요일": "5",
    "일요일": "6"
}


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


def save_reminders_to_file(reminders: List[Reminder]):
    with open(REMINDER_FILE_PATH, 'w', encoding='utf-8') as file:
        json.dump([reminder.to_dict() for reminder in reminders], file, ensure_ascii=False, indent=4)


def load_reminders_from_file(scheduler: AsyncIOScheduler, bot: commands.Bot) -> List[Reminder]:
    reminders = []
    try:
        with open(REMINDER_FILE_PATH, 'r', encoding='utf-8') as file:
            data = json.load(file)
            for reminder_data in data:
                reminder = Reminder.from_dict(reminder_data)
                reminders.append(reminder)
                schedule_reminder(reminder, scheduler, bot)
    except FileNotFoundError:
        pass
    except json.JSONDecodeError:
        pass
    return reminders


def schedule_reminder(reminder: Reminder, scheduler: AsyncIOScheduler, bot: commands.Bot):
    cron_trigger = CronTrigger(
        hour=int(reminder.time.split(':')[0]),
        minute=int(reminder.time.split(':')[1]),
        day_of_week=','.join([KOREAN_DAYS_OF_WEEK[day] for day in reminder.day.split(',')])
    )

    async def reminder_action(_reminder: Reminder) -> None:
        await _reminder.send_reminder(bot)
        if _reminder.decrement_interval() == 0:
            scheduler.remove_job(_reminder.job_id)

    scheduler.add_job(
        lambda: asyncio.run_coroutine_threadsafe(
            reminder_action(reminder),
            bot.loop
        ),
        cron_trigger,
        id=reminder.job_id
    )
