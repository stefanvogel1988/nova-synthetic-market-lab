from pathlib import Path

from nova_lab.settings import LabSettings


def test_loads_default_lab_settings(tmp_path: Path):
    config = tmp_path / "lab.yaml"
    config.write_text(
        "seed: 20260915\n"
        "parent_count: 150\n"
        "child_count: 30\n"
        "education_count: 20\n"
        "red_team_count: 12\n"
        "output_dir: outputs\n"
    )

    settings = LabSettings.load(config)

    assert settings.seed == 20260915
    assert settings.parent_count == 150
    assert settings.child_count == 30
    assert settings.education_count == 20
    assert settings.red_team_count == 12
    assert settings.output_dir == Path("outputs")
