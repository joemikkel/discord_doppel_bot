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
		values = {
			"username" : self.username,
			"token" : self.token,
			"config path" : self.config_path,
			"regular interjection chance" : self.regular_chance,
			"robot prison interjection chance" : self.prison_chance
		}
		return pprint.pformat(values)


	def _import_config(self):

		if not os.path.exists(self.config_path):
			raise Exception(f"The config file was not found: {self.config_path}")
		config = configparser.ConfigParser()
		config.read(self.config_path)
		self.token = config['auth']['token']
		self.regular_chance = float(config['behavior']['interjection_chance'])
		self.prison_chance = float(config['behavior']['prison_interjection_chance'])
		self.history_length = int(config['behavior']['history_length'])
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
				reply = await self.make_reply(message)
				await message.channel.send(reply)
			# otherwise reply depending on channel
			if str(message.channel) == 'robot-prison':
				if random.random() < self.prison_chance:
					reply = await self.make_reply(message)
					await message.channel.send(reply)
			else:
				if random.random() < self.regular_chance:
					reply = await self.make_reply(message)
					await message.channel.send(reply)

		self.client.run(self.token)

	async def get_message_history(self, message):
		messages = []
		async for message in message.channel.history(limit=self.history_length):
			messages.append(message)
		return messages

	def format_message_history(self, messages):
		#extract usernames and messages
		formatted_messages = []
		for message in messages:
			author = message.author.name
			content = message.content

			formatted_messages.append(f'>{author}\n{content}\n')
		return '\n'.join(formatted_messages)


	async def make_reply(self, message):
		"""
		generates a reply
		"""
		#get message history
		messages = await self.get_message_history(message)
		messages.reverse()
		formatted_messages = self.format_message_history(messages)
		print("Making a reply")
		return f"Thanks for mentioning me! here's a history:\n{formatted_messages}"






