import random
import time
import os
from collections import defaultdict
from telegram import Update, Poll
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    PollAnswerHandler,
    ContextTypes,
)

# Path to your questions file (relative or absolute if needed)
QUESTION_FILE = "questions.txt"

# Global quiz state
quiz_data = {
    "is_running": False,
    "questions": [],
    "current_index": 0,
    "poll_to_question": {},
    "start_time": 0,
    "timer": 30,
    "scores": {},
    "answer_times": {},
    "usernames": {},
    "job": None,
}

def safe_remove_job():
    if quiz_data["job"]:
        try:
            from apscheduler.jobstores.base import JobLookupError
            try:
                quiz_data["job"].schedule_removal()
            except JobLookupError:
                pass
        except ImportError:
            try:
                quiz_data["job"].schedule_removal()
            except Exception:
                pass
        quiz_data["job"] = None

def load_questions(file_path):
    with open(r"E:\python_coding\projects\questions.txt", "r", encoding="utf-8") as f:
        content = f.read().strip().split("\n\n")
    questions = []
    for block in content:
        lines = block.strip().split("\n")
        if len(lines) == 6:
            q_text = lines[0]
            options = [opt[3:].strip() if len(opt) > 3 and opt[1] == ')' else opt for opt in lines[1:5]]
            correct = lines[5].strip().upper()
            if correct in ['A', 'B', 'C', 'D']:
                correct_index = ['A', 'B', 'C', 'D'].index(correct)
                # Shuffle options and update correct index
                combined = list(zip(['A', 'B', 'C', 'D'], options))
                random.shuffle(combined)
                shuffled_labels, shuffled_options = zip(*combined)
                new_correct_index = shuffled_labels.index(correct)
                questions.append({
                    "question": q_text,
                    "options": list(shuffled_options),
                    "correct": new_correct_index
                })
    random.shuffle(questions)
    return questions

async def quiz_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if quiz_data["is_running"]:
        await update.message.reply_text("A quiz is already running. Use /stop to end it.")
        return

    args = context.args
    quiz_data["timer"] = int(args[0]) if args and args[0].isdigit() else 30
    quiz_data["questions"] = load_questions(QUESTION_FILE)
    quiz_data["is_running"] = True
    quiz_data["current_index"] = 0
    quiz_data["poll_to_question"].clear()
    quiz_data["start_time"] = time.time()

    # Send welcome message
    await update.message.reply_text(f"Welcome to the quiz! Each question will have {quiz_data['timer']} seconds.")

    # Pass context to send_question to enable job queue scheduling
    await send_question(context.bot, update.effective_chat.id, context)

import logging

async def send_question(bot, chat_id, context=None):
    logging.info(f"send_question called: current_index={quiz_data['current_index']}, total_questions={len(quiz_data['questions'])}")
    if quiz_data["current_index"] >= len(quiz_data["questions"]):
        leaderboard_text = "🎉 Quiz finished!\n\n🏆 Leaderboard:\n"
        # Include all users who participated
        all_users = set(quiz_data["usernames"].keys())
        # Prepare list of (user_id, score, time) with default 0 for missing scores/times
        leaderboard_data = []
        for user_id in all_users:
            score = quiz_data["scores"].get(user_id, 0)
            time_score = quiz_data["answer_times"].get(user_id, float('inf'))
            leaderboard_data.append((user_id, score, time_score))
        # Sort by score descending, then time ascending
        leaderboard_data.sort(key=lambda x: (-x[1], x[2]))
        leaderboard_text = "🎉 Quiz finished!\n\n🏆 Leaderboard:\n"
        for user_id, score, time_score in leaderboard_data:
            username = quiz_data["usernames"].get(user_id, str(user_id))
            time_display = f"{time_score:.2f}" if time_score != float('inf') else "N/A"
            leaderboard_text += f"{username}: {score} points, Time Score: {time_display}\n"
        await bot.send_message(chat_id=chat_id, text=leaderboard_text)
        # Set is_running to False only after sending leaderboard
        quiz_data["is_running"] = False
    if quiz_data["job"]:
        logging.info("Removing existing job before scheduling new one")
        safe_remove_job()

    q = quiz_data["questions"][quiz_data["current_index"]]
    message = await bot.send_poll(
        chat_id=chat_id,
        question=q["question"],
        options=q["options"],
        type=Poll.QUIZ,
        correct_option_id=q["correct"],
        is_anonymous=False,
        open_period=quiz_data["timer"],
    )
    quiz_data["poll_to_question"][message.poll.id] = {"question": q, "chat_id": chat_id}
    quiz_data["current_index"] += 1

    # Schedule next question after timer seconds
    if context:
        logging.info(f"Scheduling next question in {quiz_data['timer']} seconds")
        if quiz_data["job"]:
            quiz_data["job"].schedule_removal()
        quiz_data["job"] = context.job_queue.run_once(send_next_question_wrapper, quiz_data["timer"], data={"bot": bot, "chat_id": chat_id, "context": context})

import asyncio

async def send_next_question(context):
    bot = context.job.data["bot"]
    chat_id = context.job.data["chat_id"]
    ctx = context.job.data["context"]
    if quiz_data["is_running"]:
        await send_question(bot, chat_id, ctx)

async def send_next_question_wrapper(context):
    await send_next_question(context)

import time as time_module

async def handle_poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not quiz_data["is_running"]:
        return
    poll_id = update.poll_answer.poll_id
    user_id = update.poll_answer.user.id
    username = update.poll_answer.user.username or str(user_id)
    quiz_data["usernames"][user_id] = username
    selected_option = update.poll_answer.option_ids[0] if update.poll_answer.option_ids else None
    answer_time = time_module.time()
    if poll_id in quiz_data["poll_to_question"]:
        question_data = quiz_data["poll_to_question"][poll_id]["question"]
        chat_id = quiz_data["poll_to_question"][poll_id]["chat_id"]
        if selected_option == question_data["correct"]:
            quiz_data["scores"][user_id] = quiz_data["scores"].get(user_id, 0) + 1
            # Record answer time (lower is better)
            start_time = quiz_data["start_time"]
            time_taken = answer_time - start_time
            prev_time = quiz_data["answer_times"].get(user_id, float('inf'))
            if time_taken < prev_time:
                quiz_data["answer_times"][user_id] = time_taken
        # Removed immediate send_question call to wait for timer expiration

async def stop_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not quiz_data["is_running"]:
        await update.message.reply_text("No active quiz to stop.")
        return
    quiz_data["is_running"] = False
    if quiz_data["job"]:
        try:
            from apscheduler.jobstores.base import JobLookupError
            try:
                quiz_data["job"].schedule_removal()
            except JobLookupError:
                pass
        except ImportError:
            try:
                quiz_data["job"].schedule_removal()
            except Exception:
                pass
        quiz_data["job"] = None
    # Send leaderboard on stop
    # Include all users who participated
    all_users = set(quiz_data["usernames"].keys())
    leaderboard_data = []
    for user_id in all_users:
        score = quiz_data["scores"].get(user_id, 0)
        time_score = quiz_data["answer_times"].get(user_id, float('inf'))
        leaderboard_data.append((user_id, score, time_score))
    leaderboard_data.sort(key=lambda x: (-x[1], x[2]))
    leaderboard_text = "🏆 Quiz stopped by admin.\n\nCurrent Leaderboard:\n"
    for user_id, score, time_score in leaderboard_data:
        username = quiz_data["usernames"].get(user_id, str(user_id))
        time_display = f"{time_score:.2f}" if time_score != float('inf') else "N/A"
        leaderboard_text += f"{username}: {score} points, Time Score: {time_display}\n"
    await update.message.reply_text(leaderboard_text)

if __name__ == "__main__":
    app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_TOKEN")).build()

    app.add_handler(CommandHandler("quiz", quiz_command))
    app.add_handler(CommandHandler("stop", stop_command))

    async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not quiz_data["scores"]:
            await update.message.reply_text("No scores yet.")
            return
        leaderboard_text = "🏆 Current Leaderboard:\n"
        sorted_scores = sorted(quiz_data["scores"].items(), key=lambda x: x[1], reverse=True)
        for user_id, score in sorted_scores:
            leaderboard_text += f"User {user_id}: {score} points\n"
        await update.message.reply_text(leaderboard_text)

    app.add_handler(CommandHandler("leaderboard", leaderboard_command))
    app.add_handler(PollAnswerHandler(handle_poll_answer))

    app.run_polling()