import configparser
import json
import pprint
import os
import random
import asyncio
import time
import subprocess
import re

import discord
import requests


class Bot(object):
    def __init__(self, username, config_path=None):
        """
        username: name of user to be immitated (e.g. joemikkel)
        config_path: specify path to config file if not default
                     default is <username>.conf, e.g. joemikkel.conf
        """
        print("Starting...")
        # ingest config
        self.username = username
        if config_path:
            self.config_path = config_path
        else:
            self.config_path = "./bot.conf"
        self._import_config()

        # set up discord stuff
        self.client = discord.Client()
        self.discord_id = None

    def __str__(self):
        """
        make string repr for debugging
        """
        values = {
            "username": self.username,
            "token": self.token,
            "config path": self.config_path,
            "regular interjection chance": self.regular_chance,
            "robot prison interjection chance": self.prison_chance,
        }
        return pprint.pformat(values)

    def _import_config(self):
        """
        loads values from config file into class
        """
        if not os.path.exists(self.config_path):
            raise Exception(f"The config file was not found: {self.config_path}")
        config = configparser.ConfigParser()
        config.read(self.config_path)
        self.token = config["auth"][self.username]
        self.regular_chance = float(config["behavior"]["interjection_chance"])
        self.prison_chance = float(config["behavior"]["prison_interjection_chance"])
        self.history_length = int(config["behavior"]["history_length"])
        self.inferkit_token = config["inferkit"]["access_token"]
        self.inferkit_url = config["inferkit"]["url"]
        return

    def run(self):
        """
        starts bot service
        """
        # do this when the bot comes online
        @self.client.event
        async def on_ready():
            self.discord_id = self.client.user.id
            print(f"Running as user {self.client.user}, ID: {self.discord_id}")

        # do this when the bot sees a message posted somewhere
        @self.client.event
        async def on_message(message):
            print(f"saw message from {message.author}:\n {message.content}")
            # don't reply to myself
            if message.author == self.client.user:
                print("\t this is a message from me, ignoring...")
                return
            # check if I've been mentioned
            if f"{self.discord_id}" in message.content:
                print("\tI've been mentioned!")
                await self.reply(message)
            # otherwise reply depending on channel
            if str(message.channel) == "robot-prison":
                if random.random() < self.prison_chance:
                    await self.reply(message)
            else:
                if random.random() < self.regular_chance:
                    await self.reply(message)

        self.client.run(self.token)

    async def reply(self, message):
        """
        creates and posts a reply to a given message 
        """
        message_sent = False  # keep track of whether we've replied at all
        debugCtr = 0
        while message_sent is False and debugCtr < 3:
            reply = await self.make_reply(message)
            for a_message in reply:
                print(f"sending a message: {a_message}")
                if a_message.isspace() or a_message == "":
                    continue
                else:
                    await message.channel.send(a_message)
                    message_sent = True
            if not message_sent:
                debugCtr = debugCtr + 1
        if message_sent is False:
            await message.channel.send("_I don't want to reply to that._")

    async def get_message_history(self, message):
        # gets last X messages from channel history where message was posted
        messages = []
        async for message in message.channel.history(limit=self.history_length):
            messages.append(message)
        return messages

    def clean_message_history(self, messages, username):
        # create list of bad statements
        badstatements = [
            "Can't reach inferkit. Got back a 400",
            "I don't want to reply to that.",
            "---IMAGE---",
            "---URL---",
            "---TWEET---",
            "---VIDEO---",
        ]
        badsubstrings = [
            "reach inferkit",
            "IMAGE",
            "URL",
            "TWEET",
        ]
        # extract usernames and messages into a string digestible by NN
        formatted_messages = []
        for message in messages:
            # get the author
            author = message.author.name
            # make the bot think its own messages were sent by its persona
            # and that any messages sent by the actual user it's doppeling
            # were sent by a stranger
            author = author.replace("robot_" + username, "robot_placeholder")
            author = author.replace(username, "TheStranger")
            author = author.replace("robot_placeholder", username)
            content = message.content
            if "--IMAGE--" in content:
                content = "https://picsum.photos/200/200"
            # remove empty statements likely to cause repetitive behavior
            for badstatement in badstatements:
                content = content.replace(badstatement, "")
            for badsubstring in badsubstrings:
                if badsubstring in content:
                    content = ""
            # format the message so it can be digested by NN
            if len(content) > 2:
                formatted_messages.append(f"> {author}\n{content}\n")
        # put all messages into one big string for NN
        return "\n".join(formatted_messages)

    def execute_inference(self, context):
        """
        runs local executable to perform inference
        """
        exe = '/root/minimal_generator/gpt2tc'
        command = [exe, '-m', '345M', 'g', str(context)]
        r = subprocess.run(command, stdout=subprocess.PIPE, cwd=os.path.split(exe)[0])
        out = r.stdout.decode('utf8')
        print("Got this from the exe:\n---")
        print(out)
        print("---")
        split_text = bytes(context[-20:], "utf8").decode('utf8')
        print("Split : " + split_text)
        out = out.split(split_text)[-1]
        print("---")
        print(out)
        print("---")
        out = out.replace("\\n", "\n")
        out = out.replace("\\'", "'")
        out = out.split("time=")[0]
        if "<|endoftext|>" in out:
            out = out.split("<|endoftext|>")[0]
        # if out.startswith('b"') or out.startswith("b'"):
        #     out = out[2:]
        return out

    def sample_model(self, context, header):
        # talks to the NN to get a reply

        # these are the config options to sample the model
        access_token = self.inferkit_token
        stop_sequence = ">"
        # create some fake context to bias the net towards more reasonable responses
        fake_0 = "> Zack\nHow would you describe yourself?\nUTOKEN\nI'm kind of a nerd.\n"
        fake_1 = "> Ezra\nWhat color are apples?\nUTOKEN\nRed usually, sometimes green.\n"
        fake_2 = "> Rita\nhow many hands do you have?\nUTOKEN\nI have two hands.\n"
        fake_3 = "> Kira\nWhat's 23+19?\nUTOKEN\n42!\n"
        fake_4 = "> Dante\nWhat's your name?\nUTOKEN\n"+header.replace("> ", "")+"\n"
        fake_5 = "> Andre\nHow old are you?\nUTOKEN\nI'm in my mid twenties.\n"
        fake_6 = "> Ben\nWhat's a good name for a dog?\nUTOKEN\nSpot, or Killer.\n"
        fake_7 = "> Kira\nWhat's the ocean made of?\nUTOKEN\nSalt water!\n"
        fake_8 = "> Shannon\nWhat's your favorite color?\nUTOKEN\nRed!\n"
        fake_9 = "> Ethan\nWhat do you do for fun?\nUTOKEN\nI spend a lot of time on the internet.\n"
        fake_10 = "> Zack\nAre you a machine?\nUTOKEN\nI honestly don't know. I feel human, but that's what a robot *would* say.\n"
        fake_11 = "> Ezra\nWhat country are you from?\nUTOKEN\nI'm from the US.\n"
        fact_list = [fake_0,fake_1,fake_2, fake_3, fake_4, fake_5, fake_6, fake_7, fake_8, fake_9, fake_10, fake_11]
        random.shuffle(fact_list)
        fake_context = ''.join(fact_list)
        fake_context = fake_context.replace("UTOKEN", header)

        full_init_vector= fake_context + context + header
        if len(full_init_vector) > 998:
           full_init_vector = full_init_vector[-998:]
        
        textOutput = self.execute_inference(full_init_vector)
        print("This is the output from the inference function call:")
        print("---")
        print(textOutput)
        print("---")
        lines = textOutput.split("\n")
        #always remove the last line, because it may be only partially formed
        if len(lines) > 2:
            lines.pop()
        output_lines = []
        currentmessage = ""
        stop = False
        for line in lines:
            if not stop:
                if not stop_sequence in line:
                    currentmessage = currentmessage + line + "\n"
                else:
                    if header.rstrip("\n") in line:
                        output_lines.append(currentmessage)
                        currentmessage = ""
                    else:
                        stop = True
        output_lines.append(currentmessage)
        # output line now contains a list of things to post as discord messages
        return output_lines

    async def make_reply(self, message):
        """
        generates a reply to the message from the NN
        """
        # get properly formatted message history
        print("I've decided to reply")
        messages = await self.get_message_history(message)
        messages.reverse()
        formatted_messages = self.clean_message_history(messages, self.username)
        # get user who made request
        author = f"> {self.username}"
        # talk to inferkit
        print(" >>> Sampling model <<< ")
        print(f"Header: {author}")
        print(f"Context:\n---\n {formatted_messages}\n---\n")
        results = self.sample_model(formatted_messages, author)
        print(" >>> Results from nnet <<< ")
        print(results)
        return results
