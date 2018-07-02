"""
This is the testing Models
"""
import binascii
import os

from tortoise import fields
from tortoise.models import Model


def generate_token():
    return binascii.hexlify(os.urandom(16)).decode('ascii')


class Tournament(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    created = fields.DatetimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class Event(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField(
        'models.Team', related_name='events', through='event_team'
    )
    modified = fields.DatetimeField(auto_now=True)
    token = fields.TextField(default=generate_token)

    def __str__(self):
        return self.name


class Team(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    def __str__(self):
        return self.name


class EventTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()
    tournament_id = fields.IntField()
    # Here we make link to events.Team, not models.Team
    participants = fields.ManyToManyField(
        'events.TeamTwo', related_name='events', through='eventtwo_teamtwo'
    )

    class Meta:
        app = 'events'

    def __str__(self):
        return self.name


class TeamTwo(Model):
    id = fields.IntField(pk=True)
    name = fields.TextField()

    class Meta:
        app = 'events'

    def __str__(self):
        return self.name
