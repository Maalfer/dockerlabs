import sqlalchemy as sa
from sqlalchemy.orm import relationship, backref
from sqlalchemy import LargeBinary
from dockerlabs.database import Base, db_session

class DBFacade:
    def __init__(self):
        self.Model = Base
        self.session = db_session
        self.Column = sa.Column
        self.Integer = sa.Integer
        self.String = sa.String
        self.DateTime = sa.DateTime
        self.Boolean = sa.Boolean
        self.Text = sa.Text
        self.LargeBinary = LargeBinary
        self.ForeignKey = sa.ForeignKey
        self.relationship = relationship
        self.backref = backref
        self.UniqueConstraint = sa.UniqueConstraint
        self.Index = sa.Index
        self.Float = sa.Float
        self.Date = sa.Date
        self.func = sa.func
        self.or_ = sa.or_
        self.and_ = sa.and_
        self.desc = sa.desc
        self.asc = sa.asc

db = DBFacade()
