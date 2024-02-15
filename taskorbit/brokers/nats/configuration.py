from dataclasses import dataclass


@dataclass
class NatsConfiguration:
    """
    The configuration of the broker.

    Args:
        url (str): The URL of the NATS server.
        stream (str): The name of the NATS stream.
        subject (str): The name of the NATS subject.
        durable (str): The name of the NATS durable.
    """
    url: str
    stream: str
    subject: str
    durable: str
