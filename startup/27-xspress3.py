import h5py

from ophyd.areadetector import (
    AreaDetector,
    PixiradDetectorCam,
    ImagePlugin,
    TIFFPlugin,
    StatsPlugin,
    HDF5Plugin,
    ProcessPlugin,
    ROIPlugin,
    TransformPlugin,
    OverlayPlugin,
)
from ophyd.areadetector.plugins import PluginBase
from ophyd.areadetector.cam import AreaDetectorCam
from ophyd.device import BlueskyInterface
from ophyd.areadetector.trigger_mixins import SingleTrigger
from ophyd.areadetector.filestore_mixins import (
    FileStoreIterativeWrite,
    FileStoreHDF5IterativeWrite,
    FileStoreTIFFSquashing,
    FileStoreTIFF,
    FileStoreHDF5,
    new_short_uid,
    FileStoreBase,
)
from databroker.assets.handlers import HandlerBase
from ophyd import Signal
from ophyd import Component as C
from hxntools.detectors.merlin import MerlinDetector
import itertools
from pathlib import PurePath
from nslsii.detectors.xspress3 import (
    XspressTrigger,
    Xspress3Detector,
    Xspress3Channel,
    Xspress3FileStore,
    logger,
)
from ophyd.signal import set_and_wait
from enum import Enum
from ophyd.signal import set_and_wait
from collections import OrderedDict
from ophyd import Staged
from ophyd.status import DeviceStatus


class TESMode(Enum):
    step = 1
    fly = 2


from ophyd.areadetector.filestore_mixins import FileStorePluginBase


class Xspress3FileStoreFlyable(Xspress3FileStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # This soft signal must be set before staging.
        self.parent.total_points.set(1).wait()

    @property
    def filestore_res(self):
        raise Exception("don't want to be here")
        return self._filestore_res

    @property
    def filestore_spec(self):
        # Both "XPS3_FLY" and "XSP3_FLY" point to the same 
        # reader in area-detector handers. "XPS" seems like it
        # originated as a typo, but we'll leave it for consistency
        # of documents through time until / unless we do a migration
        # to "fix" the old documents in the database.
       return 'XPS3_FLY'

    def generate_datum(self, key, timestamp, datum_kwargs):
        if self.parent._mode is TESMode.step:
            return super().generate_datum(key, timestamp, datum_kwargs)
        elif self.parent._mode is TESMode.fly:
            # we are doing something _very_ dirty here to skip a level of the inheritance
            # this is brittle is if the MRO changes we may not hit all the level we expect to
            return FileStorePluginBase.generate_datum(
                self, key, timestamp, datum_kwargs
            )

    def warmup(self):
        """
        A convenience method for 'priming' the plugin.
        The plugin has to 'see' one acquisition before it is ready to capture.
        This sets the array size, etc.
        NOTE : this comes from:
            https://github.com/NSLS-II/ophyd/blob/master/ophyd/areadetector/plugins.py
        We had to replace "cam" with "settings" here.
        Also modified the stage sigs.
        """
        print("warming up the hdf5 plugin...")
        set_and_wait(self.enable, 1)
        sigs = OrderedDict(
            [
                (self.parent.settings.array_callbacks, 1),
                (self.parent.settings.image_mode, "Single"),
                (self.parent.settings.trigger_mode, "Internal"),
                # just in case tha acquisition time is set very long...
                (self.parent.settings.acquire_time, 1),
                # (self.parent.settings.acquire_period, 1),
                (self.parent.settings.acquire, 1),
            ]
        )

        original_vals = {sig: sig.get() for sig in sigs}

        for sig, val in sigs.items():
            ttime.sleep(0.1)  # abundance of caution
            set_and_wait(sig, val)

        ttime.sleep(0)  # wait for acquisition

        for sig, val in reversed(list(original_vals.items())):
            ttime.sleep(0.1)
            set_and_wait(sig, val)
        print("done")

    def describe(self):
        desc = super().describe()

        if self.parent._mode is TESMode.fly:
            spec = {
                "external": "FileStore:",
                "dtype": "array",
                # TODO do not hard code
                "shape": (self.parent.settings.num_images.get(), 2, 4096),
                "source": self.prefix,
            }
            return {"fluor": spec}
        else:
            return super().describe()


class TESXspressTrigger(XspressTrigger):
    def trigger(self):
        if self._staged != Staged.yes:
            raise RuntimeError("not staged")

        self._status = DeviceStatus(self)
        self.settings.erase.put(1)
        self._acquisition_signal.put(1, wait=False)
        trigger_time = ttime.time()
        if self._mode is TESMode.step:
            for sn in self.read_attrs:
                if sn.startswith("channel") and "." not in sn:
                    ch = getattr(self, sn)
                    self.dispatch(ch.name, trigger_time)
        elif self._mode is TESMode.fly:
            self.dispatch("fluor", trigger_time)
        else:
            raise Exception(f"unexpected mode {self._mode}")
        self._abs_trigger_count += 1
        return self._status


class TESXspress3Detector(TESXspressTrigger, Xspress3Detector):
    # TODO: garth, the ioc is missing some PVs?
    #   det_settings.erase_array_counters
    #       (XF:05IDD-ES{Xsp:1}:ERASE_ArrayCounters)
    #   det_settings.erase_attr_reset (XF:05IDD-ES{Xsp:1}:ERASE_AttrReset)
    #   det_settings.erase_proc_reset_filter
    #       (XF:05IDD-ES{Xsp:1}:ERASE_PROC_ResetFilter)
    #   det_settings.update_attr (XF:05IDD-ES{Xsp:1}:UPDATE_AttrUpdate)
    #   det_settings.update (XF:05IDD-ES{Xsp:1}:UPDATE)
    roi_data = Cpt(PluginBase, "ROIDATA:")

    # Currently only using three channels. Uncomment these to enable more
    #revised on 2/17/21#revised for ch1&2 xs 3/8/21
    channel1 = C(Xspress3Channel, "C1_", channel_num=1, read_attrs=["rois"])
    #channel2 = C(Xspress3Channel, "C2_", channel_num=2, read_attrs=["rois"])
    # channels:
    # channel3 = C(Xspress3Channel, 'C3_', channel_num=3, read_attrs=['rois'])
    # channel4 = C(Xspress3Channel, 'C4_', channel_num=4)
    # channel5 = C(Xspress3Channel, 'C5_', channel_num=5)
    # channel6 = C(Xspress3Channel, 'C6_', channel_num=6)
    # channel7 = C(Xspress3Channel, 'C7_', channel_num=7)
    # channel8 = C(Xspress3Channel, 'C8_', channel_num=8)

    hdf5 = Cpt(
        Xspress3FileStoreFlyable,
        "HDF5:",
        read_path_template="/nsls2/data/tes/legacy/raw/xspress3/%Y/%m/%d/",
        write_path_template="/DATA/%Y/%m/%d/",
        root="/nsls2/data/tes/legacy/raw/",
        #read_path_template="/nsls2/data/tes/assets/xspress3/%Y/%m/%d/",
        #write_path_template="/nsls2/data/tes/assets/xspress3/%Y/%m/%d/",
        #root="/nsls2/data/tes/assets/",
        #read_path_template="/nsls2/data/tes/legacy/raw/xspress3/%Y/%m/%d/",
        #write_path_template="/nsls2/data/tes/legacy/raw/xspress3/%Y/%m/%d/",
        #root="/nsls2/data/tes/legacy/raw/",
        #read_path_template="/tmp",
        #write_path_template="/tmp",
    )

    # this is used as a latch to put the xspress3 into 'bulk' mode
    # for fly scanning.  Do this is a signal (rather than as a local variable
    # or as a method so we can modify this as part of a plan
    fly_next = Cpt(Signal, value=False)

    energy_calibration = C(Signal, value=10.0, kind="config")

    def __init__(self, prefix, *, configuration_attrs=None, read_attrs=None, **kwargs):
        if configuration_attrs is None:
            configuration_attrs = [
                "external_trig",
                "total_points",
                "spectra_per_point",
                "settings",
                "rewindable",
            ]
        if read_attrs is None:
            #revised for ch1&2 xs 3/8/21
            #read_attrs = ["channel1", "channel2", "hdf5"]
            read_attrs = ["channel1", "hdf5"]
        super().__init__(
            prefix,
            configuration_attrs=configuration_attrs,
            read_attrs=read_attrs,
            **kwargs,
        )
        # this is possiblely one too many places to store this
        # in the parent class it looks at if the extrenal_trig signal is high
        self._mode = TESMode.step

    def stop(self, *, success=False):
        ret = super().stop()
        # todo move this into the stop method of the settings object?
        self.settings.acquire.put(0)
        self.hdf5.stop(success=success)
        return ret

    def stage(self):
        # do the latching
        if self.fly_next.get():
            self.fly_next.put(False)
            self._mode = TESMode.fly
        return super().stage()

    def unstage(self):
        try:
            ret = super().unstage()
        finally:
            self._mode = TESMode.step
        return ret

#revised for ch1&2 xs 3/8/21
xs = TESXspress3Detector("XF:08BM-ES{Xsp:1}:", name="xs")
xs.channel1.rois.read_attrs = ["roi{:02}".format(j) for j in [1, 2, 3, 4]]
#xs.channel2.rois.read_attrs = ["roi{:02}".format(j) for j in [1, 2, 3, 4]]
xs.hdf5.num_extra_dims.put(0)
xs.channel1.vis_enabled.put(1)
#xs.channel2.vis_enabled.put(1)
xs.settings.num_channels.put(1)

xs.settings.configuration_attrs = [
    "acquire_period",
    "acquire_time",
    "gain",
    "image_mode",
    "manufacturer",
    "model",
    "num_exposures",
    "num_images",
    "temperature",
    "temperature_actual",
    "trigger_mode",
    "config_path",
    "config_save_path",
    "invert_f0",
    "invert_veto",
    "xsp_name",
    "num_channels",
    "num_frames_config",
    "run_flags",
    "trigger_signal",
]
xs.energy_calibration.kind = "config"

# Warm-up the hdf5 plugins:
warmup_hdf5_plugins([xs])
