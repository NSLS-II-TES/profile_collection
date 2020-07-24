import datetime
import os.path
import pprint

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ophyd.utils import LimitError
from ophyd import Signal
import bluesky.plan_stubs as bps
import bluesky.preprocessors as bpp

from bluesky.callbacks import LiveGrid


# Testing VI with Yonghua


# TODO could also use check_value, but like the better error message here?
def _validate_motor_limits(motor, start, stop, k):
    # blow up on inverted values
    assert start < stop, (
        f"start ({start}) must be smaller than " f"stop ({stop}) for {k}"
    )
    limits = motor.limits
    if any(not (limits[0] < v < limits[1]) for v in (start, stop)):
        raise LimitError(
            f"your requested {k} values are out of limits for "
            "the motor "
            f"{limits[0]} < ({start}, {stop}) < {limits[1]}"
        )


def _get_v_with_dflt(sig, dflt):
    ret = yield from bps.read(sig)
    return ret[sig.name]["value"] if ret is not None else dflt


x_centers = Signal(value=[], name="x_centers", kind="normal")
x_centers.tolerance = 1e-15
y_centers = Signal(value=[], name="y_centers", kind="normal")
y_centers.tolerance = 1e-15
z_centers = Signal(value=[], name="z_centers", kind="normal")
z_centers.tolerance = 1e-15


def xy_fly(
        scan_title,
        *,
        beamline_operator,
        dwell_time,
        xstart,
        xstop,
        xstep_size,
        ystart,
        ystop,
        ystep_size=None,
        xspress3=None,
):
    """Do a x-y fly scan.

    The x-motor is the 'fast' direction.

    Parameters
    ----------
    scan_title : str
       A name for the scan.

    beamline_operator : str
       The individual responsible for this scan. Appears in output directory path.

    dwell_time : float
       Target time is s on each pixel

    xstart, xstop : float
       The start and stop values in the fast direction in mm

    xstep_size :
        xstep_size is step of x movement

    ystart, ystop : float
       The start and stop values in the slow direction in mm

    ystep_size :
        ystep_size use xstep_size if it isn't passed in

    scan_title : str
       Title of scan, required.
    """
    xy_fly_stage = xy_stage
    _validate_motor_limits(xy_fly_stage.x, xstart, xstop, "x")
    _validate_motor_limits(xy_fly_stage.y, ystart, ystop, "y")
    ystep_size = ystep_size if ystep_size is not None else xstep_size
    assert dwell_time > 0, f"dwell_time ({dwell_time}) must be more than 0"
    assert xstep_size > 0, f"xstep_size ({xstep_size}) must be more than 0"
    assert ystep_size > 0, f"ystep_size ({ystep_size}) must be more than 0"
    ret = yield from bps.read(xy_fly_stage.x.mres)  # (in mm)
    xmres = ret[xy_fly_stage.x.mres.name]["value"] if ret is not None else 0.0003125

    ret = yield from bps.read(xy_fly_stage.y.mres)  # (in mm)
    ymres = ret[xy_fly_stage.y.mres.name]["value"] if ret is not None else 0.0003125

    prescale = int(np.floor((xstep_size / (5 * xmres))))
    a_xstep_size = prescale * (5 * xmres)

    a_ystep_size = int(np.floor((ystep_size / (ymres)))) * ymres

    num_xpixels = int(np.floor((xstop - xstart) / a_xstep_size))
    num_ypixels = int(np.floor((ystop - ystart) / a_ystep_size))

    yield from bps.mv(
        x_centers, a_xstep_size / 2 + xstart + np.arange(num_xpixels) * a_xstep_size
    )

    # SRX original roi_key = getattr(xs.channel1.rois, roi_name).value.name
    roi_livegrid_key = xs.channel1.rois.roi01.value.name
    fig = plt.figure("xs")
    fig.clf()
    roi_livegrid = LiveGrid(
        (num_ypixels + 1, num_xpixels + 1),
        roi_livegrid_key,
        clim=None,
        cmap="inferno",
        xlabel="x (mm)",
        ylabel="y (mm)",
        extent=[xstart, xstop, ystart, ystop],
        x_positive="right",
        y_positive="down",
        ax=fig.gca(),
    )

    flyspeed = a_xstep_size / dwell_time  # this is in mm/s

    try:
        xy_fly_stage.x.velocity.check_value(flyspeed)
    except LimitError as e:
        raise LimitError(
            f"You requested a range of {xstop - xstart} with "
            f"{num_xpixels} pixels and a dwell time of "
            f"{dwell_time}.  This requires a "
            f"motor velocity of {flyspeed} which "
            "is out of range."
        ) from e

    # set up delta-tau trigger to fast motor
    for v in ["p1600=0", "p1607=1", "p1600=1"]:
        yield from bps.mv(dtt, v)
        yield from bps.sleep(0.1)

    # TODO make this a message?
    sclr.set_mode("flying")
    # poke the struck settings
    yield from bps.mv(sclr.mcas.prescale, prescale)
    yield from bps.mv(sclr.mcas.nuse, num_xpixels)
    if xspress3 is not None:
        yield from bps.mv(xs.external_trig, True)
        yield from bps.mv(xspress3.total_points, num_xpixels)
        yield from bps.mv(xspress3.hdf5.num_capture, num_xpixels)
        yield from bps.mv(xspress3.settings.num_images, num_xpixels)

    @bpp.reset_positions_decorator([xy_fly_stage.x, xy_fly_stage.y])
    @bpp.subs_decorator({"all": [roi_livegrid]})
    @bpp.monitor_during_decorator([xs.channel1.rois.roi01.value])
    @bpp.stage_decorator([sclr])
    @bpp.baseline_decorator([mono, xy_fly_stage])
    # TODO put is other meta data
    @bpp.run_decorator(
        md={
            "scan_title": scan_title,
            "operator": beamline_operator,
            "user_input": {
                "dwell_time": dwell_time,
                "xstart": xstart,
                "xstop": xstop,
                "xstep_size": xstep_size,
                "ystart": ystart,
                "ystep_size": ystep_size,
            },
            "derived_input": {
                "actual_ystep_size": a_ystep_size,
                "actual_xstep_size": a_xstep_size,
                "fly_velocity": flyspeed,
                "xpixels": num_xpixels,
                "ypixels": num_ypixels,
                "prescale": prescale,
            },
        }
    )
    def fly_body():

        yield from bps.mv(xy_fly_stage.x, xstart, xy_fly_stage.y, ystart)

        @bpp.stage_decorator([x for x in [xspress3] if x is not None])
        def fly_row():
            # go to start of row
            target_y = ystart + y * a_ystep_size
            yield from bps.mv(xy_fly_stage.x, xstart, xy_fly_stage.y, target_y)
            yield from bps.mv(
                y_centers, np.ones(num_xpixels) * target_y
            )  # set the fly speed

            ret = yield from bps.read(xy_fly_stage.z.user_readback)  # (in mm)
            zpos = (
                ret[xy_fly_stage.z.user_readback.name]["value"]
                if ret is not None
                else 0
            )
            yield from bps.mov(z_centers, np.ones(num_xpixels) * zpos)

            yield from bps.mv(xy_fly_stage.x.velocity, flyspeed)

            yield from bps.trigger_and_read([xy_fly_stage], name="row_ends")

            for v in ["p1600=0", "p1600=1"]:
                yield from bps.mv(dtt, v)
                yield from bps.sleep(0.1)

            # arm the struck
            yield from bps.trigger(sclr, group=f"fly_row_{y}")
            # maybe start the xspress3
            if xspress3 is not None:
                yield from bps.trigger(xspress3, group=f"fly_row_{y}")
            yield from bps.sleep(0.1)
            # fly the motor
            yield from bps.abs_set(
                xy_fly_stage.x, xstop + a_xstep_size, group=f"fly_row_{y}"
            )
            yield from bps.wait(group=f"fly_row_{y}")

            yield from bps.trigger_and_read([xy_fly_stage], name="row_ends")
            yield from bps.mv(xy_fly_stage.x.velocity, 5.0)
            yield from bps.sleep(0.1)
            # read and save the struck
            yield from bps.create(name="primary")
            #
            yield from bps.read(sclr)
            yield from bps.read(mono)
            yield from bps.read(x_centers)
            yield from bps.read(y_centers)
            yield from bps.read(z_centers)
            yield from bps.read(xy_fly_stage.y)
            yield from bps.read(xy_fly_stage.z)
            # and maybe the xspress3
            if xspress3 is not None:
                yield from bps.read(xspress3)
            yield from bps.save()

        for y in range(num_ypixels):
            if xspress3 is not None:
                yield from bps.mv(xspress3.fly_next, True)

            yield from fly_row()

    yield from fly_body()

    # save the start document to a file for the benefit of the user
    start = db[-1].start
    dt = datetime.datetime.fromtimestamp(start["time"])
    filepath = os.path.expanduser(
        f"~/Users/Data/{start['operator']}/{dt.date().isoformat()}/xy_fly/"
        f"{start['scan_title']}-{start['scan_id']}-{start['operator']}-{dt.time().isoformat()}.log"
    )
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "wt") as output_file:
        output_file.write(pprint.pformat(start))


E_centers = Signal(value=[], name="E_centers", kind="normal")
E_centers.tolerance = 1e-15


def E_fly(
        scan_title, *, operator, element, start, stop, step_size, num_scans, flyspeed=0.05, xspress3=None
):
    _validate_motor_limits(mono.energy, start, stop, "E")
    assert step_size > 0, f"step_size ({step_size}) must be more than 0"
    assert num_scans > 0, f"num_scans ({num_scans}) must be more than 0"

    e_back = yield from _get_v_with_dflt(mono.e_back, 1977.04)
    energy_cal = yield from _get_v_with_dflt(mono.cal, 0.40118)
    roi = rois(element)
    xs.channel1.rois.roi01.bin_low.set(roi[0])
    xs.channel1.rois.roi01.bin_high.set(roi[1])


    def _linear_to_energy(linear):
        linear = np.asarray(linear)
        return e_back / np.sin(
            np.deg2rad(45)
            + 0.5 * np.arctan((28.2474 - linear) / 35.02333)
            + np.deg2rad(energy_cal) / 2
        )

    def _energy_to_linear(energy):
        energy = np.asarray(energy)
        return 28.2474 + 35.02333 * np.tan(
            np.pi / 2 - 2 * np.arcsin(e_back / energy) + np.deg2rad(energy_cal)
        )

    # get limits in linear parameters
    l_start, l_stop = _energy_to_linear([start, stop])
    l_step_size = np.diff(_energy_to_linear([start, start + step_size]))

    # scale to match motor resolution
    lmres = yield from _get_v_with_dflt(mono.linear.mres, 0.0001666)

    prescale = int(np.floor((l_step_size / (5 * lmres))))
    a_l_step_size = prescale * (5 * lmres)

    num_pixels = int(np.floor((l_stop - l_start) / a_l_step_size))

    bin_edges = _linear_to_energy(l_start + a_l_step_size * np.arange(num_pixels + 1))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    yield from bps.mv(E_centers, bin_centers)

    # The flyspeed is set by Paul by edict
    # flyspeed = 0.05

    # set up delta-tau trigger to fast motor
    for v in ["p1600=0", "p1607=4", "p1601=5", "p1602 = 2", "p1604 = 0", "p1600=1"]:
        yield from bps.mv(dtt, v)
        yield from bps.sleep(0.1)

    # TODO make this a message?
    sclr.set_mode("flying")

    # SRX original roi_key = getattr(xs.channel1.rois, roi_name).value.name

    # roi_livegrid_key = xs.channel1.rois.roi01.value.name
    # roi_livegrid = LivePlot(y=roi_livegrid_key)

    # poke the struck settings
    yield from bps.mv(sclr.mcas.prescale, prescale)
    yield from bps.mv(sclr.mcas.nuse, num_pixels)

    if xspress3 is not None:
        yield from bps.mv(xs.external_trig, True)
        yield from mv(xspress3.total_points, num_pixels)
        yield from mv(xspress3.hdf5.num_capture, num_pixels)
        yield from mv(xspress3.settings.num_images, num_pixels)

    @bpp.reset_positions_decorator([mono.linear])
    @bpp.stage_decorator([sclr])
    # @bpp.subs_decorator({"all": [roi_livegrid]})
    @bpp.monitor_during_decorator([xs.channel1.rois.roi01.value])
    @bpp.baseline_decorator([mono, xy_stage])
    # TODO put is other meta data
    @bpp.run_decorator(
        md={
            "scan_title": scan_title,
            "operator": operator,
            "user_input": {
                "element": element,
                "start": start,
                "stop": stop,
                "step_size": step_size,
            },
            "derived_input": {
                "l_start": l_start,
                "l_stop": l_stop,
                "l_step_size": l_step_size,
                "lmres": lmres,
                "actual_l_step_size": a_l_step_size,
                "fly_velocity": flyspeed,
                "num_pixels": num_pixels,
                "prescale": prescale,
            },
        }
    )
    def fly_body():
        yield from bps.trigger_and_read([E_centers], name="energy_bins")

        @bpp.stage_decorator([x for x in [xspress3] if x is not None])
        def fly_once(y):
            # for y in range(num_scans):
            # go to start of row

            yield from bps.checkpoint()
            yield from bps.mv(mono.linear, l_start)

            # set the fly speed
            yield from bps.mv(mono.linear.velocity, flyspeed)

            yield from bps.trigger_and_read([mono], name="row_ends")

            for v in ["p1600=0", "p1600=1"]:
                yield from bps.mv(dtt, v)
                yield from bps.sleep(0.1)

            # arm the Struck
            yield from bps.trigger(sclr, group=f"fly_energy_{y}")
            if xspress3 is not None:
                yield from bps.trigger(xspress3, group=f"fly_energy_{y}")

            # fly the motor
            yield from bps.abs_set(
                mono.linear, l_stop + a_l_step_size, group=f"fly_energy_{y}"
            )
            yield from bps.wait(group=f"fly_energy_{y}")

            yield from bps.trigger_and_read([mono], name="row_ends")

            yield from bps.mv(mono.linear.velocity, 0.5)
            # hard coded to let the sclr count its fingers and toes
            yield from bps.sleep(0.1)
            # read and save the struck
            yield from bps.create(name="primary")
            yield from bps.read(sclr)
            if xspress3 is not None:
                yield from bps.read(xspress3)

            yield from bps.save()

        for scan_iter in range(num_scans):
            if xspress3 is not None:
                yield from bps.mv(xspress3.fly_next, True)
            yield from fly_once(scan_iter)

    yield from fly_body()

    print("Waiting for files... ...")
    yield from bps.sleep(15)
    artifacts = e_fly_export(db[-1])
    pprint.pprint(artifacts)


