# twitch.py


import re
import time
import asyncio


#==============================================================
# a twitch chat monitor you can send to any channel
#==============================================================

class Chat():
    def __init__(
            self, 
            token, #-- (str) account token
            nick, #-- (str) account name
            channel, #-- (int) twitch channel to join
            server='irc.chat.twitch.tv', #-- (str) url of twitch irc server
            port=6667 #-- (int) port to connect to
            ):
        self.channel = channel
        self.connected = False
        self.message_class = Message
        self.nick = nick
        self.port = port
        self.chat_receivers = set()
        self.server = server
        self.streaming = False
        self.token = token
    
    def add_chat_receiver(self, awaitable): 
    #== adds awaitable to chat receivers
        self.chat_receivers.add(awaitable)
    
    def remove_chat_receiver(self, awaitable): 
    #== removes awaitable from chat receivers
        self.chat_receivers.discard(awaitable)
    
    async def connect(self): 
    #== connects to the twitch channel of choice and returns reader/writer
        reader, writer = await asyncio.open_connection(self.server, self.port)
        writer.write(f"PASS {self.token}\n".encode('utf-8'))
        writer.write(f"NICK {self.nick}\n".encode('utf-8'))
        writer.write(f"JOIN {self.channel}\n".encode('utf-8'))
        self.connected = True
        print(f'{self.nick} connected to {self.channel}')
        return (reader, writer)
    
    async def disconnect(self, writer): 
    #== disconnects from twitch
        writer.close()
        await writer.wait_closed()
        self.connected = False
        print(f'{self.nick} disconnected from {self.channel}')
    
    async def reconnect(self): 
    #== continuously attempts to reconnect once per second and returns reader/writer on success
        while not self.connected:
            try:
                reader, writer = await self.connect()
            except:
                await asyncio.sleep(1)
        return (reader, writer)
    
    async def start_stream(self): 
    #== continuously monitors twitch chat
        try:
            reader, writer = await self.connect()
        except:
            reader, writer = await self.reconnect()
        self.streaming = True
        while self.streaming:
            try:
                chat_line = await reader.readline()
            except ConnectionError:
                print('lost connection: attempting reconnect')
                reader, writer = await self.reconnect()
                continue
            message = self.message_class(chat_line)
            if message.is_ping():
                writer.write("PONG\n".encode('utf-8'))
            elif message.is_privmsg():
                await self.send_message(message)
        await self.disconnect()
    
    def stop_stream(self): 
    #== stops the chat monitor
        self.streaming = False
    
    async def send_message(self, message): 
    #== sends Message object to awaitable receiver(s)
        for receiver in self.chat_receivers:
            await receiver(message)


#==============================================================
# a twitch chat message
#==============================================================

class Message():
    def __init__(
            self, 
            chat_line #-- (bytes) encoded line read from twitch irc server
            ):
        self.line = chat_line.decode('utf-8')
    
    def is_ping(self): 
    #== returns true if line is a PING
        if self.line.startswith('PING'):
            return True
        return False
    
    def is_privmsg(self): 
    #== returns true if line is a PRIVMSG
        match = re.match(r":.*PRIVMSG.*:", self.line)
        if match is not None:
            return True
        return False
    
    def get_privmsg(self): 
    #== returns user and message from a PRIVMSG
        if not self.is_privmsg(): return (None, None)
        match = re.match(r":(.*)!.*:(.*)", self.line)
        user = match.group(1)
        message = match.group(2)
        return (user, message)