from __future__ import annotations

from dataclasses import dataclass, field
from math import hypot


VALID_COMMANDS = {"START", "RESET", "STOP", "ESTOP"}
GAME_STATES = {"IDLE", "PLAYING", "FINISHED", "EMERGENCY_STOP"}
CLOUD_STATES = {
    "DRIFT",
    "ATTRACT_RED",
    "ATTRACT_WHITE",
    "SHY_RED",
    "SHY_WHITE",
    "COMFORT_RED",
    "COMFORT_WHITE",
    "PANIC_RETURN",
    "COOLDOWN",
}


@dataclass(frozen=True)
class Point:
    x: float
    y: float


@dataclass
class GameConfig:
    game_duration_sec: float = 75.0
    comfort_score_per_sec: float = 1.0
    comfort_bonus_duration_sec: float = 3.0
    comfort_bonus_score: int = 3
    cooldown_sec: float = 4.0
    panic_hold_sec: float = 0.8
    shy_distance_m: float = 1.2
    comfort_min_distance_m: float = 0.0
    comfort_max_distance_m: float = 2.0
    return_arrival_distance_m: float = 0.18
    far_call_min: float = 0.65
    far_call_max: float = 0.85
    near_comfort_min: float = 0.35
    near_comfort_max: float = 0.55
    near_panic_min: float = 0.70
    voice_margin: float = 0.05
    red_team: Point = field(default_factory=lambda: Point(2.5, 0.0))
    white_team: Point = field(default_factory=lambda: Point(-2.5, 0.0))
    center: Point = field(default_factory=lambda: Point(0.0, 0.0))


@dataclass
class GameSnapshot:
    game_state: str
    cloud_state: str
    target_team: str
    red_score: int
    white_score: int
    red_comfort: float
    white_comfort: float
    time_remaining: float
    effect_mode: str
    event: str = "NONE"


class CloudGame:
    def __init__(self, config: GameConfig | None = None) -> None:
        self.config = config or GameConfig()
        self.red_voice = 0.0
        self.white_voice = 0.0
        self.robot_position = Point(0.0, 0.0)
        self._score_float = {"RED": 0.0, "WHITE": 0.0}
        self._comfort = {"RED": 0.0, "WHITE": 0.0}
        self._comfort_hold = {"RED": 0.0, "WHITE": 0.0}
        self._bonus_awarded = {"RED": False, "WHITE": False}
        self._panic_hold = 0.0
        self._cooldown_remaining = 0.0
        self.game_state = "IDLE"
        self.cloud_state = "DRIFT"
        self.target_team = "NONE"
        self.time_remaining = self.config.game_duration_sec
        self.effect_mode = "NORMAL"
        self.last_event = "NONE"

    def set_voice(self, red: float | None = None, white: float | None = None) -> None:
        if red is not None:
            self.red_voice = self._clamp01(red)
        if white is not None:
            self.white_voice = self._clamp01(white)

    def set_robot_position(self, x: float, y: float) -> None:
        self.robot_position = Point(float(x), float(y))

    def command(self, command: str) -> GameSnapshot:
        normalized = command.strip().upper()
        if normalized not in VALID_COMMANDS:
            self.last_event = "NONE"
            return self.snapshot()
        if normalized == "START":
            self._reset_scores()
            self.game_state = "PLAYING"
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.time_remaining = self.config.game_duration_sec
            self.effect_mode = "NORMAL"
            self.last_event = "GAME_START"
        elif normalized == "RESET":
            self._reset_scores()
            self.game_state = "IDLE"
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.time_remaining = self.config.game_duration_sec
            self.effect_mode = "NORMAL"
            self.last_event = "NONE"
        elif normalized == "STOP":
            self.game_state = "FINISHED"
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.effect_mode = "FINISHED"
            self.last_event = self._winner_event()
        elif normalized == "ESTOP":
            self.game_state = "EMERGENCY_STOP"
            self.cloud_state = "COOLDOWN"
            self.target_team = "NONE"
            self.effect_mode = "COOLDOWN"
            self.last_event = "NONE"
        return self.snapshot()

    def step(self, dt: float) -> GameSnapshot:
        dt = max(0.0, float(dt))
        self.last_event = "NONE"
        if self.game_state != "PLAYING":
            return self.snapshot()

        self.time_remaining = max(0.0, self.time_remaining - dt)
        if self.time_remaining <= 0.0:
            self.game_state = "FINISHED"
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.effect_mode = "FINISHED"
            self.last_event = self._winner_event()
            return self.snapshot()

        if self.cloud_state == "DRIFT":
            self._step_drift()
        elif self.cloud_state in {"ATTRACT_RED", "ATTRACT_WHITE"}:
            self._step_attract()
        elif self.cloud_state in {"SHY_RED", "SHY_WHITE", "COMFORT_RED", "COMFORT_WHITE"}:
            self._step_near_team(dt)
        elif self.cloud_state == "PANIC_RETURN":
            self._step_panic_return()
        elif self.cloud_state == "COOLDOWN":
            self._cooldown_remaining = max(0.0, self._cooldown_remaining - dt)
            if self._cooldown_remaining <= 0.0:
                self.cloud_state = "DRIFT"
                self.target_team = "NONE"
                self.effect_mode = "NORMAL"

        return self.snapshot()

    def snapshot(self) -> GameSnapshot:
        return GameSnapshot(
            game_state=self.game_state,
            cloud_state=self.cloud_state,
            target_team=self.target_team,
            red_score=int(self._score_float["RED"]),
            white_score=int(self._score_float["WHITE"]),
            red_comfort=self._comfort["RED"],
            white_comfort=self._comfort["WHITE"],
            time_remaining=self.time_remaining,
            effect_mode=self.effect_mode,
            event=self.last_event,
        )

    def _step_drift(self) -> None:
        red_calls = self._in_far_call(self.red_voice)
        white_calls = self._in_far_call(self.white_voice)
        if red_calls and self.red_voice >= self.white_voice + self.config.voice_margin:
            self._set_target("RED", "ATTRACT_RED", "ATTRACT_RED")
        elif white_calls and self.white_voice >= self.red_voice + self.config.voice_margin:
            self._set_target("WHITE", "ATTRACT_WHITE", "ATTRACT_WHITE")
        else:
            self.target_team = "NONE"
            self.effect_mode = "NORMAL"

    def _step_attract(self) -> None:
        team = self.target_team
        if team not in {"RED", "WHITE"}:
            self.cloud_state = "DRIFT"
            return
        voice = self._team_voice(team)
        if not self._in_far_call(voice) and self._distance_to_team(team) > self.config.comfort_max_distance_m:
            self.cloud_state = "DRIFT"
            self.target_team = "NONE"
            self.effect_mode = "NORMAL"
            return
        if self._distance_to_team(team) <= self.config.shy_distance_m:
            self.cloud_state = f"SHY_{team}"
            self.effect_mode = "SHY"

    def _step_near_team(self, dt: float) -> None:
        team = "RED" if self.cloud_state.endswith("RED") else "WHITE"
        voice = self._team_voice(team)
        distance = self._distance_to_team(team)

        if voice >= self.config.near_panic_min:
            self._panic_hold += dt
            if self._panic_hold >= self.config.panic_hold_sec:
                self.cloud_state = "PANIC_RETURN"
                self.target_team = "NONE"
                self.effect_mode = "PANIC"
                self._cooldown_remaining = self.config.cooldown_sec
                self._panic_hold = 0.0
                self.last_event = "BUBBLE_PANIC"
            return

        self._panic_hold = 0.0
        in_comfort_voice = self.config.near_comfort_min <= voice <= self.config.near_comfort_max
        in_comfort_distance = (
            self.config.comfort_min_distance_m <= distance <= self.config.comfort_max_distance_m
        )

        if in_comfort_voice and in_comfort_distance:
            self.cloud_state = f"COMFORT_{team}"
            self.effect_mode = "COMFORT"
            self._comfort[team] = self._clamp01(self._comfort[team] + dt / 3.0)
            self._comfort_hold[team] += dt
            self._score_float[team] += self.config.comfort_score_per_sec * dt
            if (
                self._comfort_hold[team] >= self.config.comfort_bonus_duration_sec
                and not self._bonus_awarded[team]
            ):
                self._score_float[team] += self.config.comfort_bonus_score
                self._bonus_awarded[team] = True
                self.last_event = "BUBBLE_REWARD"
        else:
            self.cloud_state = f"SHY_{team}"
            self.effect_mode = "SHY"
            self._comfort[team] = self._clamp01(self._comfort[team] - dt / 2.0)
            self._comfort_hold[team] = 0.0
            self._bonus_awarded[team] = False
            if voice <= 0.25 and self._comfort[team] <= 0.0 and distance > self.config.shy_distance_m:
                self.cloud_state = "DRIFT"
                self.target_team = "NONE"
                self.effect_mode = "NORMAL"

    def _step_panic_return(self) -> None:
        if self._distance(self.robot_position, self.config.center) <= self.config.return_arrival_distance_m:
            self.cloud_state = "COOLDOWN"
            self.target_team = "NONE"
            self.effect_mode = "COOLDOWN"
            self._cooldown_remaining = self.config.cooldown_sec

    def _set_target(self, team: str, cloud_state: str, effect_mode: str) -> None:
        self.target_team = team
        self.cloud_state = cloud_state
        self.effect_mode = effect_mode

    def _reset_scores(self) -> None:
        self._score_float = {"RED": 0.0, "WHITE": 0.0}
        self._comfort = {"RED": 0.0, "WHITE": 0.0}
        self._comfort_hold = {"RED": 0.0, "WHITE": 0.0}
        self._bonus_awarded = {"RED": False, "WHITE": False}
        self._panic_hold = 0.0
        self._cooldown_remaining = 0.0

    def _winner_event(self) -> str:
        red = int(self._score_float["RED"])
        white = int(self._score_float["WHITE"])
        if red > white:
            return "RED_WIN"
        if white > red:
            return "WHITE_WIN"
        return "DRAW"

    def _distance_to_team(self, team: str) -> float:
        return self._distance(self.robot_position, self._team_point(team))

    def _team_point(self, team: str) -> Point:
        return self.config.red_team if team == "RED" else self.config.white_team

    def _team_voice(self, team: str) -> float:
        return self.red_voice if team == "RED" else self.white_voice

    def _in_far_call(self, voice: float) -> bool:
        return self.config.far_call_min <= voice <= self.config.far_call_max

    @staticmethod
    def _distance(a: Point, b: Point) -> float:
        return hypot(a.x - b.x, a.y - b.y)

    @staticmethod
    def _clamp01(value: float) -> float:
        return max(0.0, min(1.0, float(value)))
