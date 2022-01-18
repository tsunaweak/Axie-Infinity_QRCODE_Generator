import requests
import json
import qrcode
from web3.auto import w3
from eth_account.messages import encode_defunct
import time
import discord
from discord.ext import commands
import os
import asyncio


class discordBot(commands.Bot):
    roninWallet = None
    privateKey = None
    raw_message = None
    signed_message = None
    signature = None
    config = None
    async def on_ready(self):
        await self.wait_until_ready()
        self.add_commands()
        print(f'We have logged in as {self.user.name}')
    async def on_command_error(self, ctx, error):
        if isinstance(error, commands.CommandNotFound):
            await ctx.send(error)
    def add_commands(self):
        @self.group(name="getqr", pass_context=True, invoke_without_command = True)
        async def getqr(ctx, arg=None):
            if ctx.message.author.guild_permissions.administrator:
                if arg is not None:
                    if arg in self.config['users']:
                        self.roninWallet = self.config["users"][arg]["roninWallet"]
                        self.privateKey = self.config["users"][arg]["privateKey"]
                        self.submit_signature()
                        if self.signature is None:
                            await ctx.send('Oops Something went wrong, Please try again.')
                        else:
                            qrCodePath = f"QRCode_{arg}_{time.strftime('%m%d%Y%H%M%S')}.png"
                            qrcode.make(self.signature).save(qrCodePath)
                            embed = discord.Embed(title=f"Axie Infinity QR Code by {arg}", description="**Note: ** Dont share with anyone")
                            embed.set_image(url="attachment://" + qrCodePath)
                            await ctx.send(file=discord.File(qrCodePath), embed=embed)
                            os.remove(qrCodePath)
                    else:
                        await ctx.send('User not found, please input a valid user')
        @self.group(name="removeUser", pass_context=True, invoke_without_command = True)
        async def removeUser(ctx, arg=None):
            if ctx.message.author.guild_permissions.administrator:
                if arg is not None:
                    if arg in self.config['users']:
                        self.removeUser(arg)
                        await ctx.send(f'{arg} has been remove.')
                    else:
                        await ctx.send('User not found, please input a valid user')
        @self.group(name="addUser", pass_context=True, invoke_without_command = True)
        async def addUser(ctx, username=None, roninWallet=None, privateKey=None):
            if ctx.message.author.guild_permissions.administrator:
                errorMsg = ""
                if username is None:
                    errorMsg += "Username not found.\n"
                if roninWallet is None:
                    errorMsg += "Ronin Wallet not found.\n"
                if privateKey is None:
                    errorMsg += "Private Key not found.\n"
                if errorMsg != "":
                    await ctx.send(errorMsg)
                else:
                    if username in self.config["users"]:
                        await ctx.send(f'{username} is already exists')
                    else:
                        self.addUser(username, roninWallet, privateKey)
                        await ctx.send(f'{username} has been added')
        @self.group(name="listUser", pass_context=True, invoke_without_command = True)
        async def listUser(ctx):
            self.parseJSON()
            if ctx.message.author.guild_permissions.administrator:
                embed = discord.Embed(title=f"Username List", description="")
                if self.config["users"] == {}:
                    await ctx.send("No user found, please add user.")
                else:
                    for index, user in enumerate(self.config["users"], 1):
                        embed.add_field(name=f"User No. {index}", value=user, inline=False)
                    await ctx.send(embed=embed)
        @self.group(name="help", pass_context=True, invoke_without_command = True)
        async def help(ctx):
            if ctx.message.author.guild_permissions.administrator:
                msg = """
```
Discord Bot Command Helper

Available Commands:
!getqr - Display the QR Code of the user
!addUser - Add a user that can be used on getqr
!removeUser - Remove a user that can be used on getqr
!listUser - List all user that can be used on getqr

!help - Show this message

Type !help command for more info on a command.
```"""
                await ctx.send(msg)
        @help.command()
        async def getqr(ctx):
             if ctx.message.author.guild_permissions.administrator:
                msg = """
```
How to use !getqr command

Display the QR Code of the user

Usage:
!getqr [Username]

Example:
!getqr user1
```"""
                await ctx.send(msg)
        @help.command()
        async def removeUser(ctx):
            if ctx.message.author.guild_permissions.administrator:
                msg = """
```
How to use !removeUser command

Remove a user that can be used on getqr

Usage:
!removeUser [Username]

Example:
!removeUser user1
```"""
                await ctx.send(msg)
        @help.command()
        async def addUser(ctx):
            if ctx.message.author.guild_permissions.administrator:
                msg = """
```
How to use !addUser command

Add a user that can be used on getqr

Usage:
!addUser [Username] [Ronin Wallet Address] [Private Key]

Example:
!addUser user1 ronin:xxxxxxxxxxxxxxxxxxxxxxx 0x000000000000000000000000000000
```"""
                await ctx.send(msg)
        @help.command()
        async def listUser(ctx):
            if ctx.message.author.guild_permissions.administrator:
                msg = """
```
How to use !listUser command

List all user that can be used on getqr

Usage:
!listUser

Example:
!listUser
```"""
                await ctx.send(msg)
    def get_raw_memssage(self):
        request_body = {"operationName": "CreateRandomMessage", "variables": {}, "query": "mutation CreateRandomMessage {\n  createRandomMessage\n}\n"}
        r = requests.post('https://axieinfinity.com/graphql-server-v2/graphql', headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',}, data=request_body)
        json_data = json.loads(r.text)
        self.raw_message = json_data['data']['createRandomMessage']
    def get_sign_message(self):
        self.get_raw_memssage()
        if self.raw_message is not None:
            try:
                private_key = bytearray.fromhex(self.privateKey.replace('0x', ''))
                message = encode_defunct(text=self.raw_message)
                self.signed_message =  w3.eth.account.sign_message(message, private_key=private_key)
            except Exception as e:
                return False
    def submit_signature(self):
        msg = self.get_sign_message()
        if msg == False:
            return False
        request_body =  {"operationName": "CreateAccessTokenWithSignature", "variables": {"input": {"mainnet": "ronin", "owner": "User's Eth Wallet Address", "message": "User's Raw Message", "signature": "User's Signed Message"}}, "query": "mutation CreateAccessTokenWithSignature($input: SignatureInput!) {  createAccessTokenWithSignature(input: $input) {    newAccount    result    accessToken    __typename  }}"}
        if self.signed_message is not None:
            request_body['variables']['input']['signature'] = self.signed_message['signature'].hex()
            request_body['variables']['input']['message'] = self.raw_message
            request_body['variables']['input']['owner'] = self.roninWallet.replace('ronin:', '0x')
            r = requests.post('https://axieinfinity.com/graphql-server-v2/graphql', headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/41.0.2228.0 Safari/537.36',}, json=request_body)
            try:
                json_data = json.loads(r.text)
            except ValueError as e:
                return False
            self.signature = json_data['data']['createAccessTokenWithSignature']['accessToken']
    def parseJSON(self):
        with open('storage.json', 'r') as file:
            self.config =  json.load(file)
    def updateConfig(self):
        with open('storage.json', 'w') as file:
            file.write(json.dumps(self.config,indent=4, sort_keys=True))
        self.parseJSON()
    def addUser(self, username, roninWallet, privateKey):
        userData = {
            "roninWallet": roninWallet,
            "privateKey": privateKey
        }
        self.config["users"][username] = userData;
        self.updateConfig()
    def removeUser(self, username):
        del self.config["users"][username]
        self.updateConfig()
    def listUsers(self):
        for user in self.config["users"]:
            print(user)
    def startBot(self):
        self.parseJSON()
        loop = asyncio.get_event_loop()
        loop.create_task(self.start(self.config["discordToken"]))
        try:
            loop.run_forever()
        except  KeyboardInterrupt as e:
            loop.close()
        except Exception as e:
            loop.close()      
if __name__ == "__main__":
    bot = discordBot(command_prefix='!', help_command=None)
    bot.startBot()
