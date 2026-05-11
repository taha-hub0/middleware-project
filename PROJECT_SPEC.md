# Middleware Data Processing System

## Project Goal
This project is a backend middleware system that processes generated log/data records.

The system has two main parts:

1. Producer Service
- Generates fake log/data records
- Sends data to middleware service

2. Middleware Service
- Receives data
- Filters unnecessary logs
- Applies KVKK masking to sensitive data
- Enriches/classifies data
- Converts data into multiple formats
- Routes data into channels
- Stores logs

Frontend and LLM are NOT included.

---

# Technologies
- Python
- FastAPI
- Docker
- Faker
- Logging module

---

# Design Patterns
The project must include these patterns:

1. Chain of Responsibility
Used for:
- filtering
- KVKK masking
- enrichment
- formatting pipeline

2. Factory Pattern
Used for:
- JSON formatter
- CSV formatter
- HTML formatter creation

3. Observer Pattern
Used for:
- logging system
- critical event notifications

---

# System Flow

Producer
↓
Middleware API
↓
Log Filter
↓
KVKK Filter
↓
Enrichment
↓
Formatting
↓
Channel Routing
↓
Output Files

---

# Project Structure

project/
│
├── producer/
│
├── middleware/
│   ├── filters/
│   ├── enrichers/
│   ├── formatters/
│   ├── observers/
│   ├── routers/
│   └── main.py
│
├── logs/
├── outputs/
│
├── Dockerfile
├── docker-compose.yml
└── requirements.txt

---

# Notes
- Keep the architecture simple and understandable.
- Avoid unnecessary enterprise complexity.
- The project is for a university final assignment.