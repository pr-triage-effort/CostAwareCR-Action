import os

from db_alchemy import User, Session
from db_alchemy import get_user, init_db

def main() -> None:
    # Connect
    cache_reset = True
    init_db(cache_reset)

    # Create User
    user1 = User(
        username='bill', tag='full', type='pub', experience=3.2, total_change_number=78, 
        review_number=23, changes_per_week=5.0, global_merge_ratio=0.67, project_merge_ratio=0.8
    )
    user2 = User(username='Doe', tag='part', type='pub', experience=1.2, review_number=15)


    with Session() as session:
        # Create users
        session.add(user1)
        session.add(user2)
        session.commit()
        print(session.query(User).where(User.username == 'bill').first().__status__())
        print(session.query(User).where(User.username == 'Doe').first().__status__())

        # Select
        # sel_user = session.query(User).where(User.username == 'bill').first()
        sel_user = get_user('bill', session)
        print(sel_user.__status__())

        # Update
        sel_user.experience = 5
        session.commit()

        # Delete
        del_user = session.query(User).where(User.username == 'Doe').first()

        print(del_user)
        session.delete(del_user)
        session.commit()

        # Close connection


main()
