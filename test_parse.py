import datetime
from dataclasses import dataclass, asdict

@dataclass
class VibeSession:
    vibe: str
    from_date: datetime.datetime | None
    to_date: datetime.datetime | None

@dataclass
class Party:
    name: str
    sessions: list[VibeSession]
    history: list
    id: str
    media_player_id: str | None = None
    active: bool = False

party = Party(
    id="123",
    name="Test Party",
    sessions=[VibeSession(vibe="Chill", from_date=datetime.datetime.now(), to_date=datetime.datetime.now())],
    history=[],
    media_player_id="media_player.test",
    active=True
)

d = asdict(party)
print("Saved dict:", d)

# simulate async_load
loaded_party = Party(
    id=d["id"],
    name=d["name"],
    active=d.get("active", False),
    media_player_id=d.get("media_player_id"),
    history=d.get("history", []),
    sessions=[
        VibeSession(
            vibe=s["vibe"],
            from_date=s["from_date"],
            to_date=s["to_date"]
        ) for s in d.get("sessions", [])
    ]
)
print("Loaded party:", loaded_party)
