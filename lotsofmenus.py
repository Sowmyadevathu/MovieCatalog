from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Category, Base, MenuItem, User

engine = create_engine('sqlite:///catalogitemwithusers.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()
session.query(Category).delete()
session.query(MenuItem).delete()
session.query(User).delete()


# Create dummy user
User1 = User(name="sowmya devathu",
             email="soumya.devathu@gmail.com",
             picture='''https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png''')
session.add(User1)
session.commit()

# menu for Family movies
category1 = Category(user_id=1, name="Family")

session.add(category1)
session.commit()

menuItem1 = MenuItem(user_id=1, name="Kalisundam Ra",
                     description="Family entertainer with village backdrop Indian movie",
                     price="$2.00", category=category1)
session.add(menuItem1)
session.commit()
menuItem2 = MenuItem(user_id=1, name="Kabhi kushi kabhi gam", description=" Blockbuster family movie directed by Karanjohar",
                     price="$2.99", category=category1)

session.add(menuItem2)
session.commit()

# Menu for Romantic movies
category2 = Category(user_id=1, name="Romance")

session.add(category2)
session.commit()


menuItem1 = MenuItem(user_id=1, name="Sakhi", description="A clean Romantic love story.",
                     price="$3.00", category=category2)

session.add(menuItem1)
session.commit()

menuItem2 = MenuItem(user_id=1, name="Sillun oru Kadal",
                     description="heartbreaking triangle love story", price="$3.00", category=category2)

session.add(menuItem2)
session.commit()


# Menu for Comedy movies
category3 = Category(user_id=1, name=" Comedy")

session.add(category3)
session.commit()


menuItem1 = MenuItem(user_id=1, name="Julai", description="full to full comedy",
                     price="$2.50", category=category3)

session.add(menuItem1)
session.commit()

menuItem2 = MenuItem(user_id=1, name="Nuvvu naku nachav", description="trivikrams entertainer",
                     price="$1.50", category=category3)

session.add(menuItem2)
session.commit()

# Menu for Animation
category4 = Category(user_id=1, name="Animation")

session.add(category4)
session.commit()


menuItem1 = MenuItem(user_id=1, name="Inside out", description="a must watch animation movie which revolves around the inside emoticans",
                     price="$4.99", category=category4)

session.add(menuItem1)
session.commit()

menuItem2 = MenuItem(user_id=1, name="Ratatoulli", description="When Rat is a master-chef.",
                     price="$4.99", category=category4)

session.add(menuItem2)
session.commit()


# Menu for Action
category5 = Category(user_id=1, name="Action")

session.add(category5)
session.commit()


menuItem1 = MenuItem(user_id=1, name="Psv-garudavega", description="Praveen sattaru's action film",
                     price="$2.00", category=category5)

session.add(menuItem1)
session.commit()

menuItem2 = MenuItem(user_id=1, name="Sahoo", description="Prabas upcoming action film",
                     price="$4.95", category=category5)

session.add(menuItem2)
session.commit()

print "added menu items!"
