"""Testes puros (sem pygame) do modelo de robos: .venv/bin/python tests/test_robots.py"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "game"))
import robots as R  # noqa: E402


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_legacy_anchor():
    flat = R.from_overall(65, "MID", flat=True)
    f = R.factors(flat, R.LEGACY_TUNING)
    assert close(f.speed, 0.9925), f.speed
    assert close(f.tackle, 0.38), f.tackle
    assert close(f.gk_save, 0.432), f.gk_save
    assert close(f.shield, 1.2 - 0.4 * 0.65), f.shield
    assert close(f.shot_err, 12 * 0.35), f.shot_err
    for ovr in (20, 98):
        s = ovr / 100
        f = R.factors(R.from_overall(ovr, "MID", flat=True), R.LEGACY_TUNING)
        assert close(f.speed, 0.7 + 0.45 * s), (ovr, f.speed)
        assert close(f.tackle, 0.12 + 0.4 * s)
        assert close(f.gk_save, 0.12 + 0.48 * s)
        assert close(f.shield, 1.2 - 0.4 * s)
        assert close(f.shot_err, 12 * (1 - s))
    # mecanicas novas zeradas no legado
    f = R.factors(R.from_overall(80, "ATT", flat=True), R.LEGACY_TUNING)
    assert f.pass_err == 0 and f.fumble == 0 and f.dec_err == 0
    assert f.kick_pow == 1 and f.think_mul == 1 and f.catch_speed == 520
    assert f.reach == 3 and f.pass_range == 450 and f.shoot_range == 420 and f.lane_margin == 35


def test_deterministic():
    a = R.from_overall(70, "MID", "Disco", seed=123)
    b = R.from_overall(70, "MID", "Disco", seed=123)
    c = R.from_overall(70, "MID", "Disco", seed=124)
    assert a == b
    assert a != c
    n1 = R.from_overall(70, "MID", "Disco")
    n2 = R.from_overall(70, "MID", "Disco", seed=None)
    assert n1 == n2
    # sem random global
    random.seed(7)
    x = random.random()
    random.seed(7)
    R.from_overall(70, "ATT", seed=5)
    R.from_overall(70, "ATT")
    assert random.random() == x
    assert tuple(a) == R.ATTRS


def test_mean_close_to_ovr():
    for ch in R.CHASSIS:
        for role in R.ROLE_BIAS:
            for ovr in (45, 55, 65, 75):
                for seed in (None, 1, 2, 3, 99):
                    r = R.from_overall(ovr, role, ch, seed)
                    m = sum(r.values()) / 8
                    assert abs(m - ovr) <= 1.5, (ch, role, ovr, seed, m)


def test_factors_sane():
    for ch in R.CHASSIS:
        for role in R.ROLE_BIAS:
            for ovr in range(28, 96, 3):
                for seed in (None, ovr):
                    r = R.from_overall(ovr, role, ch, seed)
                    assert all(R.ATTR_MIN <= v <= R.ATTR_MAX for v in r.values())
                    f = R.factors(r, R.TUNING)
                    ctx = (ch, role, ovr, f)
                    assert 0.6 <= f.speed <= 1.35, ctx
                    assert 3 <= f.accel <= 25 and 3 <= f.stop <= 25, ctx
                    assert 0.7 <= f.kick_pow <= 1.4, ctx
                    assert 0 <= f.shot_err <= 12, ctx
                    assert 0 <= f.pass_err <= 8, ctx
                    assert 0 <= f.reach <= 9, ctx
                    assert 380 <= f.catch_speed <= 700, ctx
                    assert 0 <= f.fumble <= 0.35, ctx
                    assert 0.1 <= f.tackle <= 0.8, ctx
                    assert 0.5 <= f.shield <= 1.3, ctx
                    assert 0.2 <= f.gk_save <= 0.95, ctx
                    assert 150 <= f.gk_speed <= 330, ctx
                    assert 0.4 <= f.gk_lead <= 1.0, ctx
                    assert 250 <= f.pass_range <= 650 and 15 <= f.lane_margin <= 60, ctx
                    assert 250 <= f.shoot_range <= 600, ctx
                    assert 0.3 <= f.think_mul <= 1.4 and 0 <= f.dec_err <= 0.4, ctx
                    assert 0.6 <= f.bat_drain_mul <= 1.5 and 0.5 <= f.bat_regen_mul <= 1.8, ctx


def test_bat_mul():
    assert R.bat_mul(1.0) == 1.0 and R.bat_mul(0.30) == 1.0
    assert close(R.bat_mul(0.0), 0.62)
    assert R.bat_mul(0.15) < 1.0
    assert close(R.bat_mul(0.2999), 0.62 + 1.26 * 0.2999)


def test_chassis_character():
    tank = R.from_overall(70, "MID", "Tanque")
    fast = R.from_overall(70, "MID", "Velocista")
    assert fast["vel"] > tank["vel"] and tank["def"] > fast["def"]


if __name__ == "__main__":
    n = 0
    for k, fn in sorted(globals().items()):
        if k.startswith("test_") and callable(fn):
            fn()
            n += 1
            print("ok", k)
    print("%d testes passaram" % n)
