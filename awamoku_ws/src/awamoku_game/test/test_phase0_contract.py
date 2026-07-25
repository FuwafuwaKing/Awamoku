from awamoku_game.phase0_contract_node import VALID_COMMANDS


def test_phase0_accepts_required_commands() -> None:
    assert VALID_COMMANDS == {"START", "RESET", "STOP", "ESTOP"}
