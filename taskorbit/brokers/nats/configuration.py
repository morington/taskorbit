from dataclasses import dataclass


@dataclass
class NatsConfiguration:
    url: str
    stream: str
    subject: str
    durable: str
