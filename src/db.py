from sqlalchemy import MetaData, Table, Column, Numeric, String, DateTime, create_engine


class DataAccessLayer:
    connection = None
    engine = None
    conn_string = None
    metadata = MetaData()
    temperature = Table(
        "temperature",
        metadata,
        Column("heure", DateTime(), nullable=False),
        Column("valeur", Numeric()),
    )
    evenements = Table(
        "evenements",
        metadata,
        Column("heure", DateTime(), nullable=False),
        Column("description", String(), nullable=False),
    )

    def db_init(self, conn_string):
        self.engine = create_engine(conn_string or self.conn_string)
        self.connection = self.engine.connect()


dal = DataAccessLayer()
