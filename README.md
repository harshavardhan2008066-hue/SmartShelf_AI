# 🍳 SmartShelf AI & Automated Gym Tracker
An Intelligent Kitchen Inventory Optimization Engine & Relational Health Monitoring Ecosystem built with Streamlit, PostgreSQL, and Gemini AI.

---

## 🚀 Project Overview
**SmartShelf AI** resolves the dual challenge of household food waste and fragmented fitness monitoring by bridging a relational database backend with advanced generative AI. 

The system allows users to seamlessly manage kitchen inventories through manual input or dynamic vision simulation vectors. It tracks ingredient shelf lives dynamically via background database queries, automatically respects individual dietary constraints (Vegan, Vegetarian, etc.), and includes a fully integrated health tracking metric bar that triggers real-time audio-visual alarms when daily calorie limits are breached.

---

## 🛠️ System Architecture & Tech Stack
* **Frontend Dashboard:** Python 3.13 + Streamlit Framework
* **Cognitive AI Core:** Google GenAI SDK (`gemini-2.5-flash`)
* **Relational Database Tier:** PostgreSQL 18 + pgAdmin 4
* **System Automation Components:** HTML5 Web Audio Synthesis Core

---

## 🗄️ Database Schema Design
The relational storage layer consists of three tables connected via strict primary/foreign key validation boundaries:

* **`users`**: Manages unique profiles, login credentials, and core dietary constraint strings.
* **`inventory`**: Manages active stock data items mapped to their owning user account via an `ON DELETE CASCADE` relation constraint.
* **`expirations`**: Tracks estimated expiration timestamps mapped down to specific relational inventory rows.

---

## 🏃‍♂️ Quick Start Setup & Execution Guide

### 1. Database Configuration
Execute the structural table schemas inside your pgAdmin query tool to initialize the storage nodes:
```sql
-- Run your smartshelf_setup.sql file inside pgAdmin to create the required tables
