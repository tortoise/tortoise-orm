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


class IntFields(Model):
    id = fields.IntField(pk=True)
    intnum = fields.IntField()
    intnum_null = fields.IntField(null=True)


class SmallIntFields(Model):
    id = fields.IntField(pk=True)
    smallintnum = fields.SmallIntField()
    smallintnum_null = fields.SmallIntField(null=True)


class CharFields(Model):
    id = fields.IntField(pk=True)
    char = fields.CharField(max_length=255)
    char_null = fields.CharField(max_length=255, null=True)


class TextFields(Model):
    id = fields.IntField(pk=True)
    text = fields.TextField()
    text_null = fields.TextField(null=True)


class BooleanFields(Model):
    id = fields.IntField(pk=True)
    boolean = fields.BooleanField()
    boolean_null = fields.BooleanField(null=True)


class DecimalFields(Model):
    id = fields.IntField(pk=True)
    decimal = fields.DecimalField(max_digits=18, decimal_places=4)
    decimal_nodec = fields.DecimalField(max_digits=18, decimal_places=0)
    decimal_null = fields.DecimalField(max_digits=18, decimal_places=4, null=True)


class DatetimeFields(Model):
    id = fields.IntField(pk=True)
    datetime = fields.DatetimeField()
    datetime_null = fields.DatetimeField(null=True)
    datetime_auto = fields.DatetimeField(auto_now=True)
    datetime_add = fields.DatetimeField(auto_now_add=True)


class DateFields(Model):
    id = fields.IntField(pk=True)
    date = fields.DateField()
    date_null = fields.DateField(null=True)


class FloatFields(Model):
    id = fields.IntField(pk=True)
    floatnum = fields.FloatField()
    floatnum_null = fields.FloatField(null=True)


class JSONFields(Model):
    id = fields.IntField(pk=True)
    data = fields.JSONField()
    data_null = fields.JSONField(null=True)


# TODO: Test that minimaly specified relations work as expected
class MinRelation(Model):
    id = fields.IntField(pk=True)
    tournament = fields.ForeignKeyField('models.Tournament')
    participants = fields.ManyToManyField(
        'models.Team'
    )


class NoID(Model):
    name = fields.CharField(max_length=255, null=True)
