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
    # chassis originais com tolerância 1.5
    for ch in R.CHASSIS:
        if ch in ("Orbital", "Titã"):
            continue  # testa separado com tolerância maior
        for role in R.ROLE_BIAS:
            for ovr in (45, 55, 65, 75):
                for seed in (None, 1, 2, 3, 99):
                    r = R.from_overall(ovr, role, ch, seed)
                    m = sum(r.values()) / 8
                    assert abs(m - ovr) <= 1.5, (ch, role, ovr, seed, m)
    # teste dos novos chassis Orbital e Titã com tolerância maior (podem alcançar limites)
    for ch in ("Orbital", "Titã"):
        for role in R.ROLE_BIAS:
            for ovr in (50, 60, 70, 80):
                for seed in (None, 1, 2, 3, 99):
                    r = R.from_overall(ovr, role, ch, seed)
                    m = sum(r.values()) / 8
                    assert abs(m - ovr) <= 3.0, (ch, role, ovr, seed, m)
    # teste com atributos 20-99 cobertos
    for attr_val in (20, 30, 50, 70, 99):
        r = R.from_overall(attr_val, "MID", "Orbital", seed=42)
        assert all(R.ATTR_MIN <= v <= R.ATTR_MAX for v in r.values())


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
                    assert 300 <= f.catch_speed <= 750, ctx
                    assert 0 <= f.fumble <= 0.35, ctx
                    assert 0.05 <= f.tackle <= 1.0, ctx
                    assert 0.3 <= f.shield <= 1.5, ctx
                    assert 0.1 <= f.gk_save <= 1.0, ctx
                    assert 100 <= f.gk_speed <= 400, ctx
                    assert 0.2 <= f.gk_lead <= 1.2, ctx
                    assert 200 <= f.pass_range <= 750 and 10 <= f.lane_margin <= 80, ctx
                    assert 200 <= f.shoot_range <= 700, ctx
                    assert 0.1 <= f.think_mul <= 1.8 and 0 <= f.dec_err <= 0.5, ctx
                    assert 0.4 <= f.bat_drain_mul <= 2.0 and 0.2 <= f.bat_regen_mul <= 2.5, ctx
    # teste dos novos chassis com atributos 20-99 cobertos (limites ampliados)
    for ch in ("Orbital", "Titã"):
        for role in R.ROLE_BIAS:
            for ovr in range(32, 95, 10):
                for seed in (None, ovr):
                    r = R.from_overall(ovr, role, ch, seed)
                    assert all(R.ATTR_MIN <= v <= R.ATTR_MAX for v in r.values())
                    f = R.factors(r, R.TUNING)
                    ctx = (ch, role, ovr, f)
                    assert 0.5 <= f.speed <= 1.5, ctx
                    assert 2 <= f.accel <= 30 and 2 <= f.stop <= 30, ctx
                    assert 0.5 <= f.kick_pow <= 1.5, ctx
                    assert 0 <= f.shot_err <= 12, ctx
                    assert 0 <= f.pass_err <= 10, ctx
                    assert 0 <= f.reach <= 10, ctx
                    assert 200 <= f.catch_speed <= 800, ctx
                    assert 0 <= f.fumble <= 0.35, ctx
                    assert 0.05 <= f.tackle <= 1.0, ctx
                    assert 0.3 <= f.shield <= 1.5, ctx
                    assert 0.1 <= f.gk_save <= 1.0, ctx
                    assert 100 <= f.gk_speed <= 400, ctx
                    assert 0.2 <= f.gk_lead <= 1.2, ctx
                    assert 100 <= f.pass_range <= 800 and 5 <= f.lane_margin <= 80, ctx
                    assert 100 <= f.shoot_range <= 800, ctx
                    assert 0.1 <= f.think_mul <= 1.8 and 0 <= f.dec_err <= 0.5, ctx
                    assert 0.4 <= f.bat_drain_mul <= 2.0 and 0.2 <= f.bat_regen_mul <= 2.5, ctx


def test_factors_tuning_robots():
    """Testes de fatores sob TUNING_ROBOTS com inclinação 2x maior."""
    for ch in ("Disco", "Orbital", "Titã"):
        for role in R.ROLE_BIAS:
            for ovr in range(20, 100, 10):
                r = R.from_overall(ovr, role, ch, seed=ovr)
                assert all(R.ATTR_MIN <= v <= R.ATTR_MAX for v in r.values())
                f = R.factors(r, R.TUNING_ROBOTS)
                ctx = (ch, role, ovr, f)
                # com TUNING_ROBOTS (slope*2), as faixas são mais amplas
                assert 0.3 <= f.speed <= 1.8, ctx
                assert 1 <= f.accel <= 40 and 1 <= f.stop <= 40, ctx
                assert 0.3 <= f.kick_pow <= 1.7, ctx
                assert 0 <= f.shot_err <= 24, ctx
                assert 0 <= f.pass_err <= 16, ctx
                assert 0 <= f.reach <= 18, ctx
                assert 100 <= f.catch_speed <= 1200, ctx
                assert 0 <= f.fumble <= 0.7, ctx
                assert -0.2 <= f.tackle <= 1.2, ctx
                assert 0.0 <= f.shield <= 2.0, ctx
                assert -0.3 <= f.gk_save <= 1.5, ctx
                assert 0 <= f.gk_speed <= 600, ctx
                assert 0.0 <= f.gk_lead <= 1.2, ctx
                assert 0 <= f.pass_range <= 1200 and 0 <= f.lane_margin <= 120, ctx
                assert 0 <= f.shoot_range <= 1200, ctx
                assert -0.5 <= f.think_mul <= 2.2 and -0.3 <= f.dec_err <= 1.0, ctx
                assert 0.0 <= f.bat_drain_mul <= 2.6 and -0.6 <= f.bat_regen_mul <= 2.8, ctx


def test_scaled_tuning():
    """Testa scaled_tuning(k): cópia com slope multiplicado, âncoras e limites iguais."""
    # scaled_tuning(1.0) deve ser igual a TUNING
    scaled_1 = R.scaled_tuning(1.0)
    assert scaled_1["flat"] == R.TUNING["flat"]
    for name in R.TUNING["f"]:
        anchor_t, slope_t, lo_t, hi_t = R.TUNING["f"][name]
        anchor_s, slope_s, lo_s, hi_s = scaled_1["f"][name]
        assert anchor_t == anchor_s, (name, anchor_t, anchor_s)
        assert close(slope_t, slope_s), (name, slope_t, slope_s)
        assert lo_t == lo_s, (name, lo_t, lo_s)
        assert hi_t == hi_s, (name, hi_t, hi_s)

    # TUNING_ROBOTS deve ter slope*2
    assert R.TUNING_ROBOTS["flat"] == R.TUNING["flat"]
    for name in R.TUNING["f"]:
        anchor_t, slope_t, lo_t, hi_t = R.TUNING["f"][name]
        anchor_r, slope_r, lo_r, hi_r = R.TUNING_ROBOTS["f"][name]
        assert anchor_t == anchor_r, (name, anchor_t, anchor_r)
        assert close(slope_r, slope_t * 2.0), (name, slope_r, slope_t * 2.0)
        assert lo_t == lo_r, (name, lo_t, lo_r)
        assert hi_t == hi_r, (name, hi_t, hi_r)

    # TUNING não deve ter sido mutado
    original_tuning = R.scaled_tuning(1.0)
    R.scaled_tuning(2.0)
    for name in R.TUNING["f"]:
        anchor_o, slope_o, lo_o, hi_o = original_tuning["f"][name]
        anchor_t, slope_t, lo_t, hi_t = R.TUNING["f"][name]
        assert anchor_o == anchor_t, (name, anchor_o, anchor_t)
        assert close(slope_o, slope_t), (name, slope_o, slope_t)
        assert lo_o == lo_t, (name, lo_o, lo_t)
        assert hi_o == hi_t, (name, hi_o, hi_t)


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
