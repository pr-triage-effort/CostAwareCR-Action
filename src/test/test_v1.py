from test.db_peewee import database, create_tables, User, Project
from peewee import *

def main():
    # Connect to DB
    if database.connect():
        create_tables()
        print("Connection established to database")

    # Do stuff
    # user = create_user('bill', 'full', 'pub', 3.2, 78, 23, 5.0, 0.67, 0.8)
    # print(f"User {user.name} was created")
    # user = User.create(name='Doe', tag='part', type='pub', experience=1.2, review_num=15)
    # print(f"User {user.name} was created")

    # Select
    query = User.get(User.name == 'Doe')
    for res in query:
        user = res
        break
    print(user.experience)

    # Update
    user.experience = 5
    user.save()

    # Delete
    query = User.get(User.name == 'bill')
    for res in query:
        user = res
        break

    print(user.experience)
    user.delete_instance()

    # Close Connection
    database.close()


def create_user(name, tag, type, experience=None, total_changes=None, review_num=None, changes_per_week=None, global_merge_ratio=None, project_merge_ratio=None) -> User:
    try:
        with database.atomic():
            user = User.create(
                name = name,
                tag = tag,
                type = type,
                experience = experience,
                total_change_number = total_changes,
                review_number = review_num,
                changes_per_week = changes_per_week,
                global_merge_ratio = global_merge_ratio,
                project_merge_ratio = project_merge_ratio
            )

        return user

    except IntegrityError:
        print('Error')


main()
