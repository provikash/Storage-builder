# Adapted from: https://github.com/zawsq/Teleshare/blob/main/bot/utilities/schedule_manager.py
# Modified & extended by: @Mak0912 (TG)

import datetime
import tzlocal
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pyrogram import Client
from info import Config
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

class ScheduleManager:
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler(
            timezone=tzlocal.get_localzone(),
            misfire_grace_time=5,
        )

    async def start(self) -> None:
        """
        Starts the scheduler and recovers pending tasks.
        """
        self.scheduler.start()
        print("DEBUG: Scheduler started successfully")
        await self.recover_pending_tasks()

    async def recover_pending_tasks(self) -> None:
        """
        Recover pending delete tasks from database on bot restart.
        """
        try:
            from bot.database.auto_delete_db import get_all_delete_tasks
            pending_tasks = await get_all_delete_tasks()

            if not pending_tasks:
                print("DEBUG: No pending delete tasks found")
                return

            current_time = datetime.datetime.now(tz=tzlocal.get_localzone())
            recovered_count = 0

            for task in pending_tasks:
                try:
                    # Parse run_time
                    if isinstance(task['run_time'], str):
                        run_time = datetime.datetime.fromisoformat(task['run_time'])
                        if run_time.tzinfo is None:
                            run_time = run_time.replace(tzinfo=tzlocal.get_localzone())
                    else:
                        run_time = task['run_time']

                    # If task time has passed, skip it
                    if run_time <= current_time:
                        from bot.database.auto_delete_db import delete_saved_task
                        await delete_saved_task(task['_id'])
                        continue

                    # Re-schedule the task
                    self.scheduler.add_job(
                        func=self.delete_messages,
                        trigger="date",
                        run_date=run_time,
                        args=[None, task['chat_id'], task['message_ids'], task['base64_file_link'], task['_id']],
                        id=task['_id'],
                        misfire_grace_time=60,
                        replace_existing=True
                    )
                    recovered_count += 1

                except Exception as e:
                    print(f"ERROR recovering task {task.get('_id', 'unknown')}: {e}")
                    continue

            print(f"DEBUG: Recovered {recovered_count} pending delete tasks")

        except Exception as e:
            print(f"ERROR in recover_pending_tasks: {e}")

    async def delete_messages(self, client: Client, chat_id: int, message_ids: list[int], base64_file_link: str, task_id: str = None) -> None:
        try:
            # Get client instance if not provided (for recovered tasks)
            if client is None:
                # Import here to avoid circular imports
                import pyrogram
                # Get the running client instance
                for instance in pyrogram.Client.instances:
                    if hasattr(instance, 'db_channel'):
                        client = instance
                        break

                if client is None:
                    print("ERROR: No active bot client found for scheduler")
                    return

            chunk_size = 100
            chunked_ids = [message_ids[i:i+chunk_size] for i in range(0, len(message_ids), chunk_size)]
            deleted_count = 0

            for chunk in chunked_ids:
                try:
                    await client.delete_messages(chat_id=chat_id, message_ids=chunk)
                    deleted_count += len(chunk)
                    print(f"DEBUG: Deleted {len(chunk)} messages from chat {chat_id}")
                    await asyncio.sleep(1)  # Avoid rate limits
                except Exception as e:
                    print(f"ERROR: Failed to delete chunk: {e}")
                    continue

            # Send retrieve button only if messages were actually deleted
            if deleted_count > 0:
                retrieve_button = InlineKeyboardMarkup([
                    [InlineKeyboardButton("🗂 Retrieve Deleted File(s)", url=f"https://t.me/{client.me.username}?start={base64_file_link}")]
                ])

                success_msg = getattr(Config, 'AUTO_DEL_SUCCESS_MSG', f"✅ Successfully deleted {deleted_count} files. Click below to retrieve them again.")

                await client.send_message(
                    chat_id=chat_id,
                    text=success_msg,
                    reply_markup=retrieve_button,
                )
                print(f"DEBUG: Auto-delete completed for {deleted_count} messages")

            if task_id:
                from bot.database.auto_delete_db import delete_saved_task
                await delete_saved_task(task_id)

        except Exception as e:
            print(f"ERROR in delete_messages: {e}")
            import traceback
            traceback.print_exc()

    async def schedule_delete(self, client: Client, chat_id: int, message_ids: list[int], delete_n_seconds: int, base64_file_link: str) -> None:
        try:
            run_time = datetime.datetime.now(tz=tzlocal.get_localzone()) + datetime.timedelta(seconds=delete_n_seconds)
            task_id = f"{chat_id}_{message_ids[0]}_{datetime.datetime.utcnow().timestamp()}"

            # Save task to database
            from bot.database.auto_delete_db import save_delete_task
            await save_delete_task(
                chat_id=chat_id,
                message_ids=message_ids,
                base64_file_link=base64_file_link,
                run_time=run_time,
                task_id=task_id
            )

            # Schedule the deletion job
            self.scheduler.add_job(
                func=self.delete_messages,
                trigger="date",
                run_date=run_time,
                args=[client, chat_id, message_ids, base64_file_link, task_id],
                id=task_id,
                misfire_grace_time=60,
                replace_existing=True
            )

            print(f"DEBUG: Scheduled auto-delete for {len(message_ids)} messages in {delete_n_seconds} seconds")

        except Exception as e:
            print(f"ERROR in schedule_delete: {e}")
            import traceback
            traceback.print_exc()

# Global instance
schedule_manager = ScheduleManager()