from .demo import DemoConnector
from .google_places import GooglePlacesConnector


def get_connector(name: str):
    return GooglePlacesConnector() if name == "google_places" else DemoConnector()
