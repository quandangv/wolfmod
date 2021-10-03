import core
import asyncio
import lang.vn as lang

posts = []
members = []
channels = {}

def generate_send(channel_name):
  async def send(text):
    posts.append('[{}] {}'.format(channel_name, text))
  return send

def low_create_channel(name, *players):
  channel = channels[name] = Channel(name)
  channel.members.extend(players)
  return channel

@core.action
async def create_channel(name, *players):
  return low_create_channel(name, *players)

@core.action
async def add_member(channel, member):
  channel.members.append(member)

@core.action
def tr(key):
  def strip_prefix(prefix):
    nonlocal key
    if key.startswith(prefix):
      key = key[len(prefix):]
      return True
  if key == '_and':
    return ''
  if strip_prefix('cmd_'):
    return [ key, key + '_desc ', key + '_alias' ]
  if strip_prefix('role_'):
    return [ key, key + '_desc ', key + '_alias' ]
  sample_result = getattr(lang, key)
  if isinstance(sample_result, tuple):
    sample_result = sample_result[0]
  arg_count = sample_result.count('{') - sample_result.count('{{') * 2
  return (key if arg_count == 0 else '{}({})'.format(key, ', '.join(['{}'] * arg_count))) + ' '

@core.action
async def get_available_members():
  for member in members:
    yield member

@core.action
def shuffle_copy(arr):
  return arr[::-1]

class Channel:
  def __init__(self, name):
    self.name = name
    self.send = generate_send(name)
    self.members = []
    channels[name] = self

  def delete():
    del channels[name]
    del self.name
    del self.send

class Message:
  def __init__(self, author, content, channel):
    self.content = content
    self.author = author
    self.channel = channel

class Member:
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.mention = '@' + name
    self.dm_channel = low_create_channel(self.mention, self)

anne = Member(0, 'anne')
bob = Member(1, 'bob')
carl = Member(2, 'carl')
david = Member(3, 'david')
elsa = Member(4, 'elsa')

game = low_create_channel('game')

members = [ anne, bob, carl, david, elsa ]
admins = [ anne ]

core.BOT_PREFIX = '!'
core.initialize(admins)

loop = asyncio.get_event_loop()

def low_expect_response(coroutine, response):
  loop.run_until_complete(coroutine)

  if isinstance(response, str):
    assert len(posts) == 1, "Expected a single response. Actual: " + str(posts)
    assert posts[0] == response, r"""
Unexpected response: {}.
           Expected: {}.""".format(posts[0], response)
  else:
    assert len(posts) == len(response), "Expected {} responses, got {} responses: {}".format(len(response), len(posts), posts)
    for idx, r in enumerate(response):
      assert r == posts[idx], r"""At index {},
Expected: {}.
     Got: {}.""".format(idx, r, posts[idx])
    
  del posts[:]

def expect_response(author, message, channel, response):
  low_expect_response(core.process_message(Message(author, message, channel)), response)

expect_response(anne, '!help', game, '[game] confirm(@anne) help_list(!help`, `!add_role`, `!list_roles`, `!start_immediate) ')
expect_response(carl, '!help', game, '[game] confirm(@carl) help_list(!help`, `!list_roles) ')

expect_response(anne, '!help help', game, '[game] confirm(@anne) help_desc ')
expect_response(carl, '!help start_immediate', game, '[game] confirm(@carl) start_immediate_desc ')
expect_response(carl, '!help blabla', game, '[game] confused(`blabla`) ')
expect_response(anne, '!help_alias help', game, '[game] confirm(@anne) help_desc ')
expect_response(anne, '!help help_alias', game, '[game] confirm(@anne) alias(help_alias, help) help_desc ')

expect_response(anne, '!add_role', game, '[game] question(@anne) add_nothing(!) ')
expect_response(carl, '!add_role', game, '[game] question(@carl) require_admin ')

expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role villager_alias', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role guard', game, '[game] confirm(@anne) add_success(guard) ')
expect_response(anne, '!start_immediate', game, '[game] question(@anne) start_needless(5, 3) ')
expect_response(anne, '!add_role wolf', game, '[game] confirm(@anne) add_success(wolf) ')
expect_response(anne, '!add_role wolf', game, '[game] confirm(@anne) add_success(wolf) ')
expect_response(anne, '!list_roles', game, '[game] confirm(@anne) list_roles(villager, villager, guard, wolf, wolf, 5) ')
expect_response(anne, '!start_immediate', game, ['[game] confirm(@anne) start(@anne, @bob, @carl, @david, @elsa) ', '[@anne] role(wolf) ', '[@bob] role(wolf) ', '[@carl] role(guard) ', '[@david] role(villager) ', '[@elsa] role(villager) ', '[wolf ] channel_greeting(wolf , @anne, @bob) '])