# Peewee library
from peewee import *

database = SqliteDatabase('cache_v1.db')

class BaseModel(Model):
    class Meta:
        database = database

class User(BaseModel):
    name = CharField(unique=True, null=False)
    tag = CharField()
    type = CharField()
    experience = DecimalField(max_digits=4, decimal_places=2, auto_round=True)
    total_change_number = IntegerField(null=True)
    review_number = IntegerField()
    changes_per_week = FloatField(null=True)
    global_merge_ratio = DecimalField(max_digits=3, decimal_places=2, auto_round=True, null=True)
    project_merge_ratio = DecimalField(max_digits=3, decimal_places=2, auto_round=True, null=True)

class Project(BaseModel):
    name = CharField(unique=True, null=False)
    changes_per_week = FloatField()
    changes_per_author = FloatField()
    merge_ratio = DecimalField(max_digits=3, decimal_places=2, auto_round=True)

def create_tables():
    if not database.table_exists(User):
        with database:
            database.create_tables([User, Project])
            print('Tables created')

