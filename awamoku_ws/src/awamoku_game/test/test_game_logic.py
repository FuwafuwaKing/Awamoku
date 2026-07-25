from awamoku_game.game_logic import CloudGame, GameConfig


def test_start_resets_game_state() -> None:
    game = CloudGame(GameConfig(game_duration_sec=10.0))
    snapshot = game.command("START")
    assert snapshot.game_state == "PLAYING"
    assert snapshot.cloud_state == "DRIFT"
    assert snapshot.red_score == 0
    assert snapshot.time_remaining == 10.0
    assert snapshot.event == "GAME_START"


def test_far_red_voice_attracts_red() -> None:
    game = CloudGame()
    game.command("START")
    game.set_voice(red=0.75, white=0.10)
    snapshot = game.step(0.2)
    assert snapshot.cloud_state == "ATTRACT_RED"
    assert snapshot.target_team == "RED"


def test_near_comfort_scores_red_and_bonus_once() -> None:
    game = CloudGame(GameConfig(comfort_bonus_duration_sec=3.0, comfort_bonus_score=3))
    game.command("START")
    game.set_voice(red=0.75, white=0.10)
    game.step(0.2)
    game.set_robot_position(1.4, 0.0)
    game.step(0.2)
    game.set_voice(red=0.45)

    snapshot = game.step(1.0)
    assert snapshot.cloud_state == "COMFORT_RED"
    assert snapshot.red_score == 1

    snapshot = game.step(2.1)
    assert snapshot.red_score >= 6
    assert snapshot.event == "BUBBLE_REWARD"

    snapshot = game.step(1.0)
    assert snapshot.event == "NONE"


def test_near_loud_voice_panics_and_cools_down() -> None:
    game = CloudGame(GameConfig(panic_hold_sec=0.8, cooldown_sec=1.0))
    game.command("START")
    game.set_voice(red=0.75, white=0.0)
    game.step(0.1)
    game.set_robot_position(1.4, 0.0)
    game.step(0.1)
    game.set_voice(red=0.80)

    snapshot = game.step(0.4)
    assert snapshot.cloud_state == "SHY_RED"

    snapshot = game.step(0.5)
    assert snapshot.cloud_state == "PANIC_RETURN"
    assert snapshot.event == "BUBBLE_PANIC"

    game.set_robot_position(0.0, 0.0)
    snapshot = game.step(0.1)
    assert snapshot.cloud_state == "COOLDOWN"

    snapshot = game.step(1.1)
    assert snapshot.cloud_state == "DRIFT"


def test_timeout_finishes_with_draw() -> None:
    game = CloudGame(GameConfig(game_duration_sec=1.0))
    game.command("START")
    snapshot = game.step(1.2)
    assert snapshot.game_state == "FINISHED"
    assert snapshot.event == "DRAW"


def test_estop_stops_state_updates() -> None:
    game = CloudGame()
    game.command("START")
    snapshot = game.command("ESTOP")
    assert snapshot.game_state == "EMERGENCY_STOP"
    assert snapshot.cloud_state == "COOLDOWN"
    snapshot = game.step(10.0)
    assert snapshot.game_state == "EMERGENCY_STOP"
