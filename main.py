from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import ListView, ListItem, Static, Input
from rich.text import Text
from telethon import TelegramClient
import re, os, json

def login(id, hash):
    client = TelegramClient('session_name', id, hash)
    client.start()
    return client

api_id = input("Please enter your API id: ")
api_hash = input("Please enter your API hash: ")

if os.path.isfile("session_name.session"):
    with open("credentials.json","r") as f:
        c = json.load(f)

    id = c.get("api_id")
    hash = c.get("api_hash")
    client = login(id, hash)
else:
    client = login(api_id, api_hash)

if api_id and api_hash:    
    data = {"api_id": api_id, "api_hash": api_hash}
    with open("credentials.json", "w") as f:
        json.dump(data, f)

async def getChats():
    await client.start()
    chats = []
    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        cleaned = re.sub(r"[^a-zA-Z0-9\s'\-\u2600-\u26FF\u2700-\u27BF]", '', dialog.name or '')
        chats.append([cleaned, dialog.entity.id])
    return chats

async def getMessages(user, chat_view):
    me = await client.get_me()
    texts = []
    messages = client.iter_messages(user, limit=100)
    async for message in messages:
        if message.text is None:
            continue
        if message.out:
            texts.append(f"{me.username}: {message.text}")
        else:
            sender = message.sender
            if not sender:
                name = "User"
            elif hasattr(sender, "first_name") and sender.first_name:
                name = sender.first_name
            elif hasattr(sender, "title") and sender.title:
                name = sender.title
            else:
                name = "User"
            texts.append(f"{name}: {message.text}")

    chat_view.display_messages(texts)

class UserList(ListView):
    def __init__(self, users, **kwargs):
        super().__init__(**kwargs)
        self.users = users
        self.border_title = "Chats"

    async def on_mount(self):
        for user in self.users:
            await self.append(ListItem(Static(Text(user))))

class ChatView(Static):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.messages = []

    def display_messages(self, messages):
        self.messages = messages
        text = Text("\n").join(Text(msg) for msg in self.messages)
        self.update(text)

class TelegramTUI(App):
    CSS = "style.tcss"

    users = []
    uids = []

    def compose(self) -> ComposeResult:
        yield UserList(self.users, id="user_list")
        with Container(id="chat_container"):
            yield ChatView(id="chat_display")
            yield Input(placeholder="Message: ", id="chat_input")

    async def on_mount(self):
        getchat = await getChats()
        self.users = [i[0] for i in getchat]
        self.uids = [i[1] for i in getchat]

        if self.users:
            self.selected_user = self.users[0]
            self.selected_uid = self.uids[0]

        user_list = self.query_one(UserList)
        await user_list.clear()
        for user in self.users:
            await user_list.append(ListItem(Static(Text(user))))

        user_list.focus()
        await self.load_messages_for_selected_user()

    async def load_messages_for_selected_user(self):
        chat_view = self.query_one("#chat_display", ChatView)
        await getMessages(self.selected_uid, chat_view)
        input_box = self.query_one("#chat_input", Input)
        input_box.value = ""

    async def on_list_view_selected(self, event: ListView.Selected):
        selected = event.item.query_one(Static).renderable
        self.selected_user = str(selected)

        idx = self.users.index(self.selected_user)
        self.selected_uid = self.uids[idx]

        await self.load_messages_for_selected_user()

    async def on_input_submitted(self, event: Input.Submitted):
        message = event.value.strip()
        if not message:
            return
            
        await client.send_message(self.selected_uid, message)
        
        chat_view = self.query_one("#chat_display", ChatView)
        chat_view.messages.append(f"You: {message}")
        chat_view.display_messages(chat_view.messages)

        event.input.value = ""

TelegramTUI().run()
