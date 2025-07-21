# Telegram Quiz Bot

This project is a Telegram quiz bot implemented in Python using the `python-telegram-bot` library. The bot runs quizzes by sending multiple-choice questions as Telegram polls, tracks user scores, and displays a leaderboard.

## Features

- Loads quiz questions from a text file (`questions.txt`).
- Sends quiz questions as Telegram quiz polls.
- Tracks user scores and answer times.
- Displays a leaderboard with usernames and scores.
- Supports commands:
  - `/quiz [timer]` - Starts the quiz with an optional timer per question (default 30 seconds).
  - `/stop` - Stops the quiz and shows the leaderboard.
  - `/leaderboard` - Shows the current leaderboard.
- Automatically sends the next question after the timer expires.

## Setup

1. Create a Telegram bot and get the bot token from [BotFather](https://t.me/BotFather).
2. Update the bot token in `projects/p2.py` in the `ApplicationBuilder().token("YOUR_TOKEN")` line.
3. Ensure the `questions.txt` file is present in the `projects/` directory with the correct format:
   - Each question block consists of 6 lines:
     - Question text
     - Option A
     - Option B
     - Option C
     - Option D
     - Correct answer letter (A, B, C, or D)
   - Question blocks are separated by a blank line.

## Running the Bot

Run the bot script:

```bash
python projects/p2.py
```

The bot will start polling Telegram for updates.

## Usage

- Use `/quiz` command in your Telegram chat to start the quiz.
- Use `/stop` to stop the quiz and see the final leaderboard.
- Use `/leaderboard` to view the current leaderboard anytime.

## Dependencies

- Python 3.7+
- `python-telegram-bot` library
- `apscheduler` library (for scheduling question timers)

Install dependencies using pip:

```bash
pip install python-telegram-bot apscheduler
```

## Notes

- The bot shuffles answer options for each question to avoid predictability.
- Make sure the bot has permission to send polls and messages in the chat.

## License

This project is provided as-is without warranty.
