"""Future tracker boundary using caller-supplied IDs; no detector/tracker library bundled."""
import math
from dataclasses import dataclass

from app.ai.models import Identity
from app.behavior.models import Behavior


@dataclass(frozen=True)
class TrackEvidence:
    track_id: str
    identity: Identity
    behavior: Behavior
    overlap_ambiguous: bool = False


class TrackLedger:
    def __init__(self, ttl_seconds=3, max_tracks=32):
        if not math.isfinite(ttl_seconds) or ttl_seconds<=0 or not 1<=max_tracks<=128:
            raise ValueError("invalid track budget")
        self.ttl, self.maximum = ttl_seconds, max_tracks
        self.tracks, self.last = {}, -1.0

    def update(self, evidence, monotonic_seconds):
        if not math.isfinite(monotonic_seconds) or monotonic_seconds<self.last or monotonic_seconds<0:
            raise ValueError("invalid track time")
        if len(evidence)>self.maximum or len({x.track_id for x in evidence})!=len(evidence):
            raise ValueError("duplicate/oversized frame tracks")
        for item in evidence:
            if not item.track_id or len(item.track_id)>64 or not isinstance(item.identity,Identity) or not isinstance(item.behavior,Behavior):
                raise ValueError("invalid track evidence")
        retained={key:value for key,value in self.tracks.items() if monotonic_seconds-value["last_seen"]<=self.ttl}
        for item in evidence:
            retained[item.track_id]={"track_id":item.track_id,"first_seen":retained.get(item.track_id,{}).get("first_seen",monotonic_seconds),
                "last_seen":monotonic_seconds,"identity_estimate":item.identity.value,"behavior_estimate":item.behavior.value}
        if len(retained)>self.maximum:
            raise ValueError("active track budget exhausted")
        self.tracks, self.last=retained,monotonic_seconds
        return sorted(retained.values(),key=lambda x:x["track_id"])


def attribution(evidence):
    ambiguous=len(evidence)!=1 or any(x.overlap_ambiguous for x in evidence)
    known=not ambiguous and evidence[0].identity in (Identity.OWNER_CAT,Identity.OTHER_CAT)
    return {"subject_track":evidence[0].track_id if known else "AMBIGUOUS",
        "identity":evidence[0].identity.value if known else "UNKNOWN",
        "preference_eligible":known and evidence[0].identity==Identity.OWNER_CAT,
        "automatic_feed_authorized":False}
