print(f"Loading {__file__!r} ...")

from ophyd import EpicsSignal, EpicsSignalRO

# Those parameters are used by suspenders in 98-suspenders.py:
ring_current = EpicsSignalRO('SR:OPS-BI{DCCT:1}I:Real-I', name="ring_current")
solenoid_v = EpicsSignal('XF:08BMES-BI{PSh:1-BPM:4}V-I', name="solenoid_v")
#I0 = EpicsSignal("XF:08BM-ES{IO:2}AI:1-I")
I0 = EpicsSignal("XF:08BMES-BI{PSh:1-BPM:3}V-I", name="I0")
#H_feedback_top = EpicsSignal('XF:08BM-ES{IO:2}AI:2-I')
#H_feedback_bottom = EpicsSignal('XF:08BM-ES{IO:2}AI:3-I')
