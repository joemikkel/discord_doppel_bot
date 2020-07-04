import configparser
import json
import pprint
import os
import random
import asyncio

import discord
import requests

class Bot(object):
	def __init__(self, username, config_path=None):
		"""
		username: name of user to be immitated (e.g. joemikkel)
		config_path: specify path to config file if not default
					 default is <username>.conf, e.g. joemikkel.conf
		"""
		# ingest config
		self.username = username
		if config_path:
			self.config_path = config_path
		else:
			self.config_path = "./" + self.username + ".conf"
		self._import_config()

		#set up discord stuff
		self.client = discord.Client()
		self.discord_id = None

	def __str__(self):
		"""
		make string repr for debugging
		"""
		values = {
			"username" : self.username,
			"token" : self.token,
			"config path" : self.config_path,
			"regular interjection chance" : self.regular_chance,
			"robot prison interjection chance" : self.prison_chance
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
		self.token = config['auth']['token']
		self.regular_chance = float(config['behavior']['interjection_chance'])
		self.prison_chance = float(config['behavior']['prison_interjection_chance'])
		self.history_length = int(config['behavior']['history_length'])
		self.inferkit_token = config['inferkit']['access_token']
		self.inferkit_url = config['inferkit']['url']
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
			print(f"saw message from {message.author}")
			# don't reply to myself
			if message.author == self.client.user:
				print("\t this is a message from me, ignoring...")
				return
			# check if I've been mentioned
			if f"<@!{self.discord_id}>" in message.content:
				await self.reply(message)
			# otherwise reply depending on channel
			if str(message.channel) == 'robot-prison':
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
		reply = await self.make_reply(message)
		message_sent = False #keep track of whether we've replied at all
		for a_message in reply:
			print(f"sending a message: {a_message}")
			if a_message.isspace() or a_message == "":
				continue
			else:
				await message.channel.send(a_message)
				message_sent = True
		if not message_sent:
			message.channel.send("_I don't want to reply to that._")

	async def get_message_history(self, message):
		# gets last X messages from channel history where message was posted
		messages = []
		async for message in message.channel.history(limit=self.history_length):
			messages.append(message)
		return messages

	def format_message_history(self, messages):
		# extract usernames and messages into a string digestible by NN
		formatted_messages = []
		for message in messages:
			author = message.author.name
			content = message.content
			formatted_messages.append(f'>{author}\n{content}\n')
		return '\n'.join(formatted_messages)

	def sample_model(self, context, header):
		# talks to the NN to get a reply

	    #these are the config options to sample the model
	    access_token = self.inferkit_token
	    stop_sequence = ">"
	    json = {
	      "prompt": {
	        "text": context + header
	      },
	      "length": 500
	    }
	    #make the actual request
	    headers = {"Authorization" : "Bearer " + access_token}
	    response = requests.post(self.inferkit_url, json=json, headers=headers)
	    textOutput= response.json()['data']['text']
	    lines = textOutput.split("\n")
	    output_lines =[]
	    currentmessage=""
	    stop = False
	    for line in lines:
	        if not stop:
	            if not stop_sequence in line:
	               currentmessage = currentmessage+line+"\n"
	            else:
	                if header.rstrip("\n") in line:
	                    output_lines.append(currentmessage)
	                    currentmessage=""
	                else:
	                    stop=True
	    output_lines.append(currentmessage)
	    #output line now contains a list of things to post as discord messages
	    return output_lines

	async def make_reply(self, message):
		"""
		generates a reply to the message from the NN
		"""
		# get properly formatted message history
		print("I've decided to reply")
		messages = await self.get_message_history(message)
		messages.reverse()
		formatted_messages = self.format_message_history(messages)
		# get user who made request
		author = f"> {message.author.name}"
		# talk to inferkit
		print(" >>> Sampling model <<< ")
		print(f"Header: {author}")
		print(f"Context:\n---\n {formatted_messages}\n---\n")
		results = self.sample_model(formatted_messages, author)
		print(" >>> Results from nnet <<< ")
		print(results)
		return results

		
		







