import core
import asyncio
import time
import lang.vn as lang
import re

posts = []
members = []
channels = {}
posts_lock = asyncio.Lock()

def generate_send(channel_name):
  async def send(text):
    posts.append('[{}] {}'.format(channel_name, text))
  return send

def low_create_channel(name, *players):
  channel = channels[name] = Channel(name)
  channel.members.extend(players)
  return channel

class Channel:
  def __init__(self, name):
    self.id = self.name = name
    self.send = generate_send(name)
    self.members = []
    channels[name] = self

  async def delete(self):
    del channels[self.name]
    self.id = self.name = self.send = None

class Message:
  def __init__(self, author, content, channel):
    self.content = content
    self.author = author
    self.channel = channel
  async def reply(self, msg):
    await self.channel.send(msg)

class Member:
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.mention = '@' + name
    self.dm_channel = low_create_channel(self.mention, self)
    self.bot = False
  async def send(self, msg):
    await self.dm_channel.send(msg)

core.DEBUG = True
core.BOT_PREFIX = '!'
core.VOTE_COUNTDOWN = 0.5
core.LANDSLIDE_VOTE_COUNTDOWN = 0.3

anne = Member(0, 'anne')
bob = Member(1, 'bob')
carl = Member(2, 'carl')
david = Member(3, 'david')
elsa = Member(4, 'elsa')
frank = Member(5, 'frank')
george = Member(6, 'george')
harry = Member(7, 'harry')
ignacio = Member(8, 'ignacio')
not_player = Member(100, 'not_player')

game = low_create_channel('game')
bot_dm = low_create_channel('@bot')

members = [ anne, bob, carl, david, elsa, frank, george, harry, ignacio ]
admins = [ anne ]

@core.action
def main_channel():
  return game

@core.action
def is_dm_channel(channel):
  return channel.name.startswith('@')

@core.action
def is_public_channel(channel):
  return channel.name == 'game'

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

  def add_formats(key, sample):
    arg_count = 0
    tokens = []
    while True:
      batch = re.findall('{?{' + str(arg_count) + '.*?}}?', sample)
      if not batch: break
      for token in batch:
        if not token in tokens:
          tokens.append(token)
      arg_count += 1

    if tokens:
      tokens.sort()
      return key + '({})'.format(', '.join(tokens))
    else:
      arg_count = sample.count('{') - sample.count('{{') * 2
      return (key if arg_count == 0 else '{}({})'.format(key, ', '.join(['{}'] * arg_count)))

  if key == '_and':
    return ''
  if key == 'reveal_item':
    return '{}:{}'
  if strip_prefix('cmd_'):
    sample = getattr(lang, 'cmd_' + key)
    return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), key + '_alias' ]
  if strip_prefix('role_'):
    sample = getattr(lang, 'role_' + key)
    return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), add_formats(key + '_greeting', sample[2]), key + ' alias' ]
  sample_result = getattr(lang, key)
  if isinstance(sample_result, list):
    sample_result = sample_result[0]
  return add_formats(key, sample_result) + ' '

@core.action
async def get_available_members():
  return members

@core.action
def shuffle_copy(arr):
  return arr[::-1]

core.initialize(admins)
loop = asyncio.get_event_loop()

async def low_expect_response(coroutine, response):
  async with posts_lock:
    await coroutine
    try:
      if isinstance(response, str):
        response = [ response ]
      assert len(posts) == len(response), r"""
  Expected: {},
       Got: {}""".format(response, posts)
      for idx, r in enumerate(response):
        assert r == posts[idx], r"""At index {},
  Expected: {}.
       Got: {}.""".format(idx, r, posts[idx])
    finally:
      del posts[:]
  await core.await_vote_countdown()

async def expect_response(author, message, channel, response):
  await low_expect_response(core.process_message(Message(author, message, channel)), response)

def check_private_single_arg_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use = True):
  result = [
    expect_response(author, cmd, game, [ '[game] question({0}) wrong_role({1}) '.format(author.mention, cmd), '[{0}] question({0}) dm_only({1}) '.format(author.mention, cmd) ]),
    expect_response(author, cmd, bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
    expect_response(author, cmd + ' foo bar', bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
    expect_response(author, cmd + ' ' + target, bot_dm, '[@bot] confirm({}) {}'.format(author.mention, success_msg)),
    *([ expect_response(author, cmd + ' ' + target, bot_dm, '[@bot] question({}) ability_used({}) '.format(author.mention, cmd)) ] if single_use else [])
  ]
  return result

def check_private_single_player_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use = True):
  return [
    expect_response(author, cmd + ' foobar', bot_dm, '[@bot] question({}) player_notfound(foobar) '.format(author.mention)),
    expect_response(author, cmd + ' ' + author.name, bot_dm, '[@bot] question({}) {} '.format(author.mention, no_self_msg)),
    *check_private_single_arg_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use)
  ]

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!save _test_empty', game, '[game] confirm(@anne) save_success(_test_empty) '),
  expect_response(anne, '!listroles', game, "[game] confirm(@anne) no_roles default_roles(['Wolf', 'Thief', 'Troublemaker', 'Drunk', 'Wolf', 'Villager', 'Seer', 'Clone', 'Minion', 'Insomniac', 'Tanner']) "),
  #expect_response(anne, '!startimmediate', game, '[game] question(@anne) start_needless(9, 0) '),
  expect_response(anne, '!help', game, '[game] confirm(@anne) help_list(!help`, `!addrole`, `!removerole`, `!listroles`, `!startimmediate`, `!votecount`, `!closevote`, `!save`, `!load`, `!endgame`, `!wakeup`, `!revealall) '),
  expect_response(carl, '!help', game, '[game] confirm(@carl) help_list(!help`, `!listroles`, `!votecount`, `!revealall) '),

  expect_response(anne, '!help help', game, '[game] confirm(@anne) help_desc(!help)aliases_list(help_alias) '),
  expect_response(anne, '!help tanner', game, '[game] confirm(@anne) tanner_desc'),
  expect_response(anne, '!help seer', game, '[game] confirm(@anne) seer_desc(2)'),
  expect_response(carl, '!help startimmediate', game, '[game] confirm(@carl) startimmediate_desc(!startimmediate)aliases_list(startimmediate_alias) '),
  expect_response(carl, '!help blabla', game, '[game] confused(`blabla`) '),
  expect_response(anne, '!help_alias help', game, '[game] confirm(@anne) help_desc(!help)aliases_list(help_alias) '),
  expect_response(anne, '!help help_alias', game, '[game] confirm(@anne) alias(help_alias, help) help_desc(!help)'),

  expect_response(anne, '!addrole', game, '[game] question(@anne) add_wronguse(!addrole) '),
  expect_response(anne, '!vote carl', game, '[game] question(@anne) not_playing '),
  expect_response(carl, '!addrole', game, '[game] question(@carl) require_admin '),

  expect_response(anne, '!addrole villager', bot_dm, '[@bot] question(@anne) public_only(!addrole) '),
  expect_response(anne, '!addrole villager, villager, villager', game, '[game] add_success(villager, villager, villager) '),
  expect_response(anne, '!addrole insomniac', game, '[game] add_success(insomniac) '),
  expect_response(anne, '!addrole clone', game, '[game] add_success(clone) '),
  expect_response(anne, '!addrole drunk', game, '[game] add_success(drunk) '),
  expect_response(anne, '!addrole troublemaker', game, '[game] add_success(troublemaker) '),
  expect_response(anne, '!addrole thief', game, '[game] add_success(thief) '),
  expect_response(anne, '!addrole villager alias', game, '[game] add_success(villager) '),
  expect_response(anne, '!addrole seer', game, '[game] add_success(seer) '),
  expect_response(anne, '!startimmediate', game, '[game] question(@anne) start_needless(9, 7) '),
  expect_response(anne, '!addrole wolf', game, '[game] add_success(wolf) '),

  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!load _test ', game, '[game] confirm(@anne) load_success(_test) '),

  expect_response(anne, '!addrole wolf', game, '[game] add_success(wolf) '),
  expect_response(anne, '!listroles', game, '[game] confirm(@anne) list_roles(villager, villager, villager, insomniac, clone, drunk, troublemaker, thief, villager, seer, wolf, wolf, 9) '),
  expect_response(anne, '!startimmediate', game, [
    '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) ',
    '[@anne] role(wolf) wolf_greeting',
    '[@bob] role(wolf) wolf_greeting',
    '[wolf ] channel_greeting(@bob, wolf ) ',
    '[@carl] role(seer) seer_greeting(!reveal, !see)',
    '[@david] role(villager) villager_greeting',
    '[@elsa] role(thief) thief_greeting(!steal)',
    '[@frank] role(troublemaker) troublemaker_greeting(!swap)',
    '[@george] role(drunk) drunk_greeting(!take)',
    '[@harry] role(clone) clone_greeting(!clone)',
    '[@ignacio] role(insomniac) insomniac_greeting',
    '[wolf ] wolf_channel(@anne, @bob) end_discussion_info(!enddiscussion) '
  ])
))

members.append(not_player)

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!addrole villager ', game, '[game] question(@anne) forbid_game_started(!addrole) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:wolf\ncarl:seer\nbob:wolf\ndavid:villager\nelsa:thief\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_roles(villager, villager, villager) '),

  expect_response(anne, '!swap', game, '[game] question(@anne) wrong_role(!swap) '),
  expect_response(anne, '!swap carl', bot_dm, '[@bot] question(@anne) wrong_role(!swap) '),

  *check_private_single_player_cmd(elsa, '!steal', 'anne', 'thief_wronguse(!steal)', 'no_swap_self', 'thief_success(anne, wolf) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:thief\ncarl:seer\nbob:wolf\ndavid:villager\nelsa:wolf\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_roles(villager, villager, villager) '),

  *check_private_single_player_cmd(carl, '!see', 'anne', 'see_wronguse(!see)', 'seer_self', 'see_success(anne, thief) '),
  expect_response(carl, '!reveal', bot_dm, '[@bot] question(@carl) reveal_wronguse(!reveal, 3) '),
  expect_response(carl, '!reveal 2', bot_dm, '[@bot] question(@carl) seer_see_already '),

  expect_response(frank, '!swap frank elsa', bot_dm, '[@bot] question(@frank) no_swap_self '),
  expect_response(frank, '!swap elsa', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!swap) '),
  expect_response(frank, '!swap ', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!swap) '),
  expect_response(frank, '!swap anne david', bot_dm, '[@bot] confirm(@frank) troublemaker_success(anne, david) '),

  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!load _test ', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(frank, '!swap anne david', bot_dm, '[@bot] question(@frank) ability_used(!swap) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_roles(villager, villager, villager) '),

  expect_response(george, '!take 4', bot_dm, '[@bot] question(@george) choice_outofrange(3) '),
  *check_private_single_arg_cmd(george, '!take', '1', 'drunk_wronguse(!take, 3)', 'no_swap_self', 'drunk_success(1) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:villager\nharry:clone\nignacio:insomniac) \nexcess_roles(drunk, villager, villager) '),

  *check_private_single_player_cmd(harry, '!clone', 'david', 'clone_wronguse(!clone)', 'clone_self', 'clone_success(david, thief) thief_greeting(!steal)', False),
  expect_response(harry, '!steal ignacio', bot_dm, '[@bot] confirm(@harry) thief_success(ignacio, insomniac) '),
  expect_response(anne, '!enddiscussion', channels['wolf '], '[wolf ] confirm(@anne) discussion_ended discussion_wait_other '),
  expect_response(bob, '!enddiscussion', channels['wolf '], [ '[wolf ] confirm(@bob) discussion_ended discussion_all_ended ', '[@ignacio] insomniac_reveal(thief) ', '[game] wake_up vote(!vote) ' ]),

  expect_response(harry, '!swap frank', bot_dm, '[@bot] question(@harry) wrong_role(!swap) '),
  expect_response(not_player, '!vote frank', bot_dm, '[@bot] question(@not_player) not_playing '),
  expect_response(harry, '!vote frank', bot_dm, '[@bot] question(@harry) public_only(!vote) '),
  expect_response(harry, '!vote frank', game, '[game] vote_success(@harry, @frank) '),
  expect_response(harry, '!vote anne', game, '[game] vote_success(@harry, @anne) '),
  expect_response(anne, '!vote harry', game, '[game] vote_success(@anne, @harry) '),
  expect_response(frank, '!vote harry', game, '[game] vote_success(@frank, @harry) '),

  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!load _test ', game, '[game] confirm(@anne) load_success(_test) '),

  expect_response(elsa, '!vote harry', game, '[game] vote_success(@elsa, @harry) '),
  expect_response(david, '!vote harry', game, '[game] vote_success(@david, @harry) '),
  expect_response(ignacio, '!vote elsa', game, [ '[game] vote_success(@ignacio, @elsa) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ]),
  expect_response(not_player, '!votecount', game, [ '[game] vote_result(vote_item(@anne, 1) \nvote_item(@harry, 4) \nvote_item(@elsa, 1) ) ', '[game] most_vote(@harry) ' ]),
  expect_response(bob, '!vote harry', game, [ '[game] vote_success(@bob, @harry) ', '[game] landslide_vote_countdown(@harry, {}) '.format(core.LANDSLIDE_VOTE_COUNTDOWN) ]),
  expect_response(carl, '!vote elsa', game, '[game] vote_success(@carl, @elsa) ')
))

members.pop()

loop.run_until_complete(asyncio.gather(
  expect_response(carl, '', game, [ '[game] vote_result(vote_item(@anne, 1) \nvote_item(@harry, 5) \nvote_item(@elsa, 2) ) ', '[game] lynch(@harry) ', '[game] reveal_player(@harry, insomniac) ', '[game] winners(@bob, @elsa) ', '[game] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:villager\nharry:insomniac\nignacio:thief) \nexcess_roles(drunk, villager, villager) ' ]),
  expect_response(carl, '!vote elsa', game, '[game] question(@carl) not_playing ')
))

@core.action
def shuffle_copy(arr):
  return arr[:]

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!removerole', game, '[game] question(@anne) remove_wronguse(!removerole) '),
  expect_response(anne, '!removerole villager, villager', game, '[game] remove_success(villager, villager) '),
  expect_response(anne, '!removerole villager', game, '[game] remove_success(villager) '),
  expect_response(anne, '!removerole wolf', game, '[game] remove_success(wolf) '),
  expect_response(anne, '!removerole minion', game, '[game] question(@anne) remove_notfound(minion) '),
  expect_response(anne, '!addrole minion', game, '[game] add_success(minion) '),
  expect_response(anne, '!addrole villager', game, '[game] add_success(villager) '),
  expect_response(anne, '!addrole villager', game, '[game] add_success(villager) '),
  expect_response(anne, '!addrole wolf', game, '[game] add_success(wolf) '),
  expect_response(anne, '!startimmediate', game, [
    '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) ',
    '[@anne] role(insomniac) insomniac_greeting',
    '[@bob] role(clone) clone_greeting(!clone)',
    '[@carl] role(drunk) drunk_greeting(!take)',
    '[@david] role(troublemaker) troublemaker_greeting(!swap)',
    '[@elsa] role(thief) thief_greeting(!steal)',
    '[@frank] role(villager) villager_greeting',
    '[@george] role(seer) seer_greeting(!reveal, !see)',
    '[@harry] role(wolf) wolf_greeting',
    '[@ignacio] role(minion) minion_greeting',
    '[@ignacio] wolves_reveal(harry) ',
    '[wolf ] wolf_channel(@harry) end_discussion_info(!enddiscussion) ',
    '[wolf ] wolf_get_reveal(!reveal, 3) '
  ])
))

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:insomniac\ncarl:drunk\nbob:clone\ndavid:troublemaker\nelsa:thief\nfrank:villager\ngeorge:seer\nharry:wolf\nignacio:minion) \nexcess_roles(wolf, villager, villager) '),
  expect_response(harry, '!reveal 1', game, [ '[game] question(@harry) wrong_role(!reveal) ', '[@harry] question(@harry) wolf_only(!reveal) ' ]),
  expect_response(harry, '!reveal 1', channels['wolf '], '[wolf ] confirm(@harry) reveal_success(1, wolf) '),
  expect_response(harry, '!reveal 1', channels['wolf '], '[wolf ] question(@harry) ability_used(!reveal) '),
  expect_response(george, '!reveal 2', bot_dm, '[@bot] confirm(@george) reveal_success(2, villager) reveal_remaining(1) '),
  expect_response(george, '!see harry', bot_dm, '[@bot] question(@george) seer_reveal_already '),
  expect_response(george, '!reveal 1', bot_dm, '[@bot] confirm(@george) reveal_success(1, wolf) no_reveal_remaining '),
  expect_response(bob, '!clone harry', bot_dm, [ '[wolf ] channel_greeting(@bob, wolf ) ', '[@bot] confirm(@bob) clone_success(harry, wolf) wolf_greeting' ]),
  expect_response(carl, '!take 1', bot_dm, '[@bot] confirm(@carl) drunk_success(1) '),
  expect_response(david, '!swap elsa george', bot_dm, '[@bot] confirm(@david) troublemaker_success(elsa, george) '),
  expect_response(harry, '!enddiscussion', channels['wolf '], '[wolf ] confirm(@harry) discussion_ended discussion_wait_other '),
  expect_response(bob, '!enddiscussion', channels['wolf '], '[wolf ] confirm(@bob) discussion_ended discussion_all_ended '),
  expect_response(elsa, '!steal ignacio', bot_dm, [ '[@anne] insomniac_reveal(insomniac) ', '[game] wake_up vote(!vote) ', '[@bot] confirm(@elsa) thief_success(ignacio, minion) ' ]),
  expect_response(not_player, '!vote frank', bot_dm, '[@bot] question(@not_player) not_playing '),
  expect_response(harry, '!vote frank', bot_dm, '[@bot] question(@harry) public_only(!vote) '),
  expect_response(harry, '!vote frank', game, '[game] vote_success(@harry, @frank) '),
  expect_response(harry, '!vote anne', game, '[game] vote_success(@harry, @anne) '),
  expect_response(anne, '!vote harry', game, '[game] vote_success(@anne, @harry) '),
  expect_response(frank, '!vote harry', game, '[game] vote_success(@frank, @harry) '),
  expect_response(elsa, '!vote harry', game, '[game] vote_success(@elsa, @harry) '),
  expect_response(david, '!vote frank', game, '[game] vote_success(@david, @frank) '),
  expect_response(ignacio, '!vote david', game, [ '[game] vote_success(@ignacio, @david) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ]),
  expect_response(ignacio, '!unvote', game, [ '[game] unvote_success(@ignacio) ', '[game] vote_countdown_cancelled ' ]),
  expect_response(ignacio, '!vote elsa', game, [ '[game] vote_success(@ignacio, @elsa) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ]),
  expect_response(bob, '!vote elsa', game, '[game] vote_success(@bob, @elsa) '),
  expect_response(carl, '!vote elsa', game, '[game] vote_success(@carl, @elsa) '),
  expect_response(not_player, '!votecount', game, [ '[game] vote_result(vote_item(@frank, 1) \nvote_item(@anne, 1) \nvote_item(@harry, 3) \nvote_item(@elsa, 3) ) ', '[game] vote_tie ' ]),
  expect_response(george, '!vote david', game, [ '[game] vote_success(@george, @david) ', '[game] vote_result(vote_item(@frank, 1) \nvote_item(@anne, 1) \nvote_item(@harry, 3) \nvote_item(@david, 1) \nvote_item(@elsa, 3) ) ', '[game] no_lynch ', '[game] winners(@carl, @bob, @elsa, @harry) ', '[game] reveal_all(anne:insomniac\ncarl:wolf\nbob:wolf\ndavid:troublemaker\nelsa:minion\nfrank:villager\ngeorge:thief\nharry:wolf\nignacio:seer) \nexcess_roles(drunk, villager, villager) ' ]),
))
