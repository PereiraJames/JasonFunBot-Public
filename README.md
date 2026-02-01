# 🤖 JasonFunBot

JasonFunBot is a modular Telegram bot built in Python.

It acts as a central controller that routes commands and triggers to
independent feature modules. The architecture is designed for
scalability, maintainability, and controlled admin access.

---

# 🧠 Architecture Overview

jasonfunbot/ → Core bot controller\
flights/ → Flight schedule tracking module\
bully/ → Humour & group interaction module\
stories/ → AI-driven interaction module (future expansion)

The main bot listens for commands and routes them to the relevant
module.

---

# ✈️ Flights Module

## Purpose

The Flights module helps track my girlfriend's flight schedule.

## How It Works

1.  Upload flight roster in PDF format\
2.  Jason extracts duty and flight data\
3.  Data is stored in a database\
4.  Flights can be retrieved on demand

## Commands

- /currentflight → Displays current active flight\
- /nextflight → Displays next two upcoming flights

## Requirements

- Database configuration (DB_HOST, DB_USER, DB_PASSWORD, DB_NAME)

---

# 😈 Bully Module

## Purpose

Allows Jason to replace me in groups and generate humorous jokes toward
friends.

## Features

- Adjustable bullying tolerance\
- Separate master compliment tolerance\
- Enable/disable control

## Commands

- /bullystatus\
- /bullyenable (Master only)\
- /bullydisable (Master only)\
- /bullytolerance → 0 = no bullying\
- /masterbullytolerance → 0 = no compliments

## Tolerance Settings

- BULLYTOLERANCE → Controls teasing intensity\
- MASTER_BULLYTOLERANCE → Controls compliment level for Master

---

# 🗂 Message Logging & AI Training

JasonFunBot stores messages for: - Record keeping\

- Conversation analysis\
- AI training experiments

Data supports contextual response improvements and future AI projects.

---

# 🔐 Access Control

Certain commands are restricted to the Master account using Telegram
filters.

Master-only commands include: - Bully configuration\

- Flight tracking commands

---

# ⚙️ Environment Setup

Copy `.env.example` to `.env` and configure required values:

Core required: - BOT_TOKEN\

- BOT_USERNAME\
- TELE_MASTERNAME\
- TELE_MASTERID

Optional modules require additional configuration.

---

# 🚀 Running the Bot

Install dependencies: pip install -r requirements.txt

Run: python jasonfunbot.py

Production deployment via Docker or systemd is recommended.

---

# 📌 Design Philosophy

- Modular design\
- Environment-driven feature toggling\
- Clean separation of concerns\
- Built for scalability
