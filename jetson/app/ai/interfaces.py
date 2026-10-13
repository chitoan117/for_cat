"""Deployment-neutral model interfaces. Mocks never invent confidences."""

from typing import Protocol

from app.ai.models import Identity, Recognition
from app.behavior.models import Behavior, BehaviorObservation
from app.camera.base import CameraFrame


class IdentityModel(Protocol):
    def predict(self, frame: CameraFrame) -> Recognition: ...


class BehaviorModel(Protocol):
    def predict(self, frame: CameraFrame, identity: Identity) -> BehaviorObservation: ...


class MockIdentityModel:
    def load(self) -> bool:
        return True

    def health(self) -> str:
        return "MOCK"

    def close(self) -> None:
        pass

    def predict(self, frame: CameraFrame) -> Recognition:
        return Recognition(timestamp=frame.captured_at, identity=Identity.UNKNOWN)


class MockBehaviorModel:
    def load(self) -> bool:
        return True

    def health(self) -> str:
        return "MOCK"

    def close(self) -> None:
        pass

    def predict(self, frame: CameraFrame, identity: Identity) -> BehaviorObservation:
        return BehaviorObservation(timestamp=frame.captured_at, identity=identity,
                                   behavior=Behavior.UNKNOWN)


class FutureInferenceAdapter:
    """No runtime locked in until exact JetPack and real model are known."""

    def predict(self, frame: CameraFrame):
        raise NotImplementedError("model runtime and trained weights unavailable")

    def load(self) -> bool:
        return False

    def health(self) -> str:
        return "NOT_CONFIGURED"

    def close(self) -> None:
        pass
