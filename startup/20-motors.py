from ophyd import EpicsSignal, EpicsMotor, Device, Component as Cpt


class MresMotor(EpicsMotor):
    mres = Cpt(EpicsSignal, ".MRES", kind="config")


class XYStage(Device):
    x = Cpt(MresMotor, "X}Mtr")
    y = Cpt(MresMotor, "Y}Mtr")
    z = Cpt(EpicsMotor, "Z}Mtr")


xy_stage = XYStage("XF:08BMES-OP{SM:1-Ax:", name="xy_stage")

xy_stage.x.velocity.kind = "normal"


class Mono(Device):
    # pseudo axis and configuration
    energy = Cpt(EpicsMotor, "x08bm:mon")
    cal = Cpt(EpicsSignal, "x08bm:mono_cal")
    e_back = Cpt(EpicsSignal, "x08bm:E_back")

    # linear drive
    linear = Cpt(MresMotor, "XF:08BMA-OP{Mono:1-Ax:Linear}Mtr")
    tilt = Cpt(MresMotor, "XF:08BMA-OP{Mono:1-Ax:Tilt}Mtr")


mono = Mono(name="mono")
mono.energy.settle_time = 2.0
#mono.settle_time = 2.0

dtt = EpicsSignal("XF:08BM-CT{MC:06}Asyn.AOUT", name="dtt", string=True)


class ToroidalMirror(Device):
    dsy = Cpt(EpicsMotor, "XD}Mtr")
    usy = Cpt(EpicsMotor, "XU}Mtr")
    dsh = Cpt(EpicsMotor, "YD}Mtr")  # Should move high to low
    ush = Cpt(EpicsMotor, "YU}Mtr")  # Should move high to low


toroidal_mirror = ToroidalMirror("XF:08BMA-OP{Mir:FM-Ax:", name="toroidal_mirror")
toroidal_mirror.kind = "hinted"
toroidal_mirror.dsy.kind = "hinted"
toroidal_mirror.usy.kind = "hinted"
toroidal_mirror.dsh.kind = "hinted"
toroidal_mirror.ush.kind = "hinted"

sd.baseline = [
    toroidal_mirror.dsy,
    toroidal_mirror.usy,
    toroidal_mirror.dsh,
    toroidal_mirror.ush
]