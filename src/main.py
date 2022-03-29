from signalrcore.hub_connection_builder import HubConnectionBuilder
import logging
import sys
import requests
import json
import time
import os
from dotenv import load_dotenv
import sqlalchemy as db


# Add .env variable in system variables, making them accessible from os.getenv()
load_dotenv()

# metadata.create_all(engine)


class Main:
    def __init__(self):
        self._hub_connection = None
        self.HOST = os.getenv("HOST", "http://178.128.234.252:32775")

        token = os.getenv("TOKEN")
        if token is None:
            sys.exit("Error: Missing environment variable 'TOKEN'")

        self.HVAC_TOKEN = token
        self.MIN_TEMP = float(os.getenv("MIN_TEMP", "20"))
        self.MAX_TEMP = float(os.getenv("MAX_TEMP", "80"))
        self.NB_TICK = int(os.getenv("NB_TICK", "6"))

    def __del__(self):
        if self._hub_connection != None:
            self._hub_connection.stop()

    def db_init(self):
        self.engine = db.create_engine(
            f"mysql+mysqlconnector://"
            f"{os.getenv('DB_USERNAME')}:"
            f"{os.getenv('DB_PASSWORD')}@"
            f"{os.getenv('DB_HOST')}/"
            f"{os.getenv('DB_NAME')}",
            connect_args={"ssl_ca": "isrgrootx1.pem"},
        )
        self.connection = self.engine.connect()
        self.metadata = db.MetaData()
        self.temperature = db.Table(
            "temperature",
            self.metadata,
            db.Column("heure", db.DateTime(), nullable=False),
            db.Column("valeur", db.Numeric(), nullable=False),
        )
        self.evenements = db.Table(
            "evenements",
            self.metadata,
            db.Column("heure", db.DateTime(), nullable=False),
            db.Column("description", db.String(255), nullable=False),
        )

    def setup(self):
        self.setSensorHub()

    def start(self):
        self.setup()
        self._hub_connection.start()

        print("||| Press CTRL+C to exit.")
        while True:
            time.sleep(2)

        self._hub_connection.stop()
        sys.exit(0)

    def setSensorHub(self):
        self._hub_connection = (
            HubConnectionBuilder()
            .with_url(f"{self.HOST}/SensorHub?token={self.HVAC_TOKEN}")
            .configure_logging(logging.INFO)
            .with_automatic_reconnect(
                {
                    "type": "raw",
                    "keep_alive_interval": 10,
                    "reconnect_interval": 5,
                    "max_attempts": 999,
                }
            )
            .build()
        )

        self._hub_connection.on("ReceiveSensorData", self.onSensorDataReceived)
        self._hub_connection.on_open(lambda: print("||| Connection opened."))
        self._hub_connection.on_close(lambda: print("||| Connection closed."))
        self._hub_connection.on_error(
            lambda data: print(f"||| An exception was thrown closed: {data.error}")
        )

    def onSensorDataReceived(self, data):
        try:
            print(data[0]["date"] + " --> " + data[0]["data"])
            date = data[0]["date"]
            dp = float(data[0]["data"])
            self.connection.execute(
                db.insert(self.temperature).values(heure=date, valeur=dp)
            )
            self.analyzeDatapoint(date, dp)
        except Exception as err:
            print(err)

    def analyzeDatapoint(self, date, data):
        if data >= self.MAX_TEMP:
            self.sendActionToHvac(date, "TurnOnAc", self.NB_TICK)
        elif data <= self.MIN_TEMP:
            self.sendActionToHvac(date, "TurnOnHeater", self.NB_TICK)

    def sendActionToHvac(self, date, action, nbTick):
        r = requests.get(f"{self.HOST}/api/hvac/{self.HVAC_TOKEN}/{action}/{nbTick}")
        details = json.loads(r.text)
        self.connection.execute(
            db.insert(self.evenements).values(
                heure=date, description=details["Response"]
            )
        )
        print(details)


if __name__ == "__main__":
    main = Main()
    main.db_init()
    main.start()
