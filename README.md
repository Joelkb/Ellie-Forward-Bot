<div align="center">

# 🚀 Ellie Forward Bot

*⚡ High-performance Telegram forwarding automation with distributed workers and smart workflow control.*

</div>

<br />

**Ellie Forward Bot** is built using Python, Pyrogram, and MongoDB to automate large-scale message forwarding. It eliminates manual effort, handles real-world forwarding challenges, and enables highly efficient batch operations.

---

>[!WARNING]
> **🚧 Under Active Development**
> * ✅ Core features are working.
> * ⚡ Performance and stability improvements are ongoing.
> * 🧪 Some features and UI flows are still being refined.

---

## 📌 About

This bot is specifically designed to handle real-world Telegram forwarding bottlenecks, including:
* Massive message volumes.
* Deleted or empty messages in a sequence.
* Rate limits and `FloodWait` restrictions.
* Long-running background jobs.

It utilizes a powerful distributed worker system and supports multiple forwarding strategies to balance flexibility and performance.

---

## ✨ Core Features

### 🔁 Automated Forwarding
* **Zero Manual Selection:** Fully automates forwarding between channels.
* **Smart Detection:** Simply forward the last message from the source chat to the bot, and it detects the source automatically.
* **Batch Processing:** Handles large batches efficiently while skipping deleted or empty messages.

### ⚡ Distributed Worker System
* **Parallel Execution:** Uses multiple bot tokens as concurrent workers.
* **Load Balancing:** The parent bot splits message ranges evenly across all available workers.
* *🔬 Successfully tested with ~10 workers (no hard limit implemented yet).*

### 🔄 Channel & Limit System
Supports dynamic routing with two target channels:
1.  **Main Target:** The primary forwarding destination.
2.  **Switch Channel:** The fallback destination used when the primary limit is reached.

> [!NOTE]
> *If only one target is set, limits are ignored.*

**Commands:**
* `/limit` — Set the forwarding limit.
* `/skip` — Skip a specific number of messages.

> [!TIP]
> Use `/skip` to jump directly to valid message ranges and avoid wasting time scanning deleted messages.

### 📊 Progress & Data Tracking
* Provides live progress updates during operations.
* Tracks total forwarded data globally.
* Auto-converts and formats data sizes cleanly (Bytes → KB → MB → GB → TB → PB).

### 🛠️ Customization
* **Custom Captions (HTML and Telegram Markdown Supported):** Use variables like `{file_name}`, `{file_size}`, and `{caption}`.
* **Custom Buttons:** Create inline button templates for forwarded messages.
* **Toggle Options:** Choose between keeping the original caption/buttons or applying your custom configurations.

### 🔁 Reliability & Error Handling
* **Auto-Resume:** Picks up right where it left off after a restart.
* **Resilience:** Gracefully handles `FloodWait`, API errors, and invalid/deleted messages.
* **Logging:** Built-in logging system accessible via the `/logs` command.

---

## 🚦 Forwarding Modes

Choose the strategy that best fits your immediate needs:

| Feature | 🧠 Smart Indexing System | ⚡ Direct Forward Mode |
| :--- | :--- | :--- |
| **Start Time** | Slower (waits for database indexing) | Starts instantly |
| **Duplicate Handling**| Prevents duplicate messages entirely | May include duplicate messages |
| **Execution Speed** | Slower (due to MongoDB operations)| Extremely fast execution |
| **Best Used For** | Clean, exact forwarding without repeats | Quick, immediate bulk operations |
*(Note: Both modes can be canceled at any time during execution).*

---

## ⚙️ Workflow (How to Use)

1.  **Configure Targets:** Set your target channel(s) in the bot.
2.  **Adjust Settings:** Configure `/limit` and `/skip` parameters if necessary.
3.  **Trigger Detection:** Forward the *last message* from your source chat directly to the bot.
4.  **Select Strategy:** Choose either **Direct Forward** or **Index + Forward** to begin the operation.

> [!IMPORTANT]
> **Channel Requirements**<br>
> All worker bots and the parent bot **must** be administrators/members of both the **Source channel** and the **Target channel(s)**. This is strictly required for accessing messages and forwarding from private channels.

---

## 💻 Tech Stack

* **Language:** Python 
* **API Framework:** Pyrogram (MTProto API)
* **Database:** MongoDB
* **Concurrency:** Async Programming (`asyncio`)

---

## 🚀 Installation & Setup

**1. Clone the repository and install dependencies:**
```bash
git clone https://github.com/Joelkb/Ellie-Forward-Bot
cd Ellie-Forward-Bot
pip install -r requirements.txt
```

**2. Configure Environment Variables:**
You will need to set the following variables in your environment or `.env` file:
```ini
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_parent_bot_token
DATABASE_URI=your_mongodb_connection_string
```

**3. Run the Bot:**
```bash
python3 main.py
```

> [!NOTE]
> *Worker bot tokens, admins, and target chats are added dynamically at runtime via the bot's settings menu.*

---

## 🚧 Limitations & Planned Improvements

**Current Limitations:**
- [ ] No media-type filtering yet.
- [ ] Worker limit control is not yet implemented.
- [ ] Duplicate messages are possible in Direct Mode.
- [ ] UI for runtime configuration is still being refined.

**Roadmap:**
- [ ] Add media filtering (isolate video, document, or audio).
- [ ] Implement per-job data tracking.
- [ ] Build a robust Worker Management UI.
- [ ] Streamline the admin and channel setup flow.
- [ ] Develop a better retry and queue system for failed messages.

---

## 🙏 Acknowledgement

>**_This project was developed based on an idea and requirements provided by a <a href="https://github.com/caproger">client</a>.  
Special thanks for the concept._**

---

<div align="center">
  <b>👨‍💻 Author</b><br>
  <a href="[https://github.com/Joelkb](https://github.com/Joelkb)">Joel Kurian Biju</a><br>
  <i>Python developer focused on automation, backend systems, and distributed workflows.</i>
</div>
