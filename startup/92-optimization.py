import os
import sys
import textwrap
import traceback

from tabulate import tabulate


def _extract_tb():
    """Auxiliary function to provide a pretty-printed traceback of the exceptions.

    This is useful when used in the try..except blocks so that the printed
    exception traceback can be easily distinguished from the actual exceptions.

    Example:
    --------
    ╭──────────────────────────────────────────────────────────────────────────────────────────────────────╮
    │ Traceback                                                                                            │
    ├──────────────────────────────────────────────────────────────────────────────────────────────────────┤
    │ File ".../.ipython/profile_collection_tes/startup/92-optimization.py", line 43, in <module>     from │
    │ bloptools.de_opt_utils import run_hardware_fly                                                       │
    ╰──────────────────────────────────────────────────────────────────────────────────────────────────────╯
        ╭──────────────────────────────────────────╮
        │ Exception                                │
        ├──────────────────────────────────────────┤
        │ No module named 'bloptools.de_opt_utils' │
        ╰──────────────────────────────────────────╯

    """
    shared_kwargs = {"tablefmt": "rounded_grid"}
    traceback_kwargs = {**shared_kwargs}
    two_borders = 2 * 2
    indent = 4

    exc_type, exc_value, exc_traceback = sys.exc_info()
    tb = traceback.format_tb(exc_traceback)

    max_len = max([len(line) for line in tb])
    term_width = os.get_terminal_size().columns

    tb = "".join(tb)

    if max_len >= term_width - two_borders:
        traceback_kwargs.update({"maxcolwidths": term_width - two_borders})

    print(tabulate([[tb]], headers=("Traceback",), **traceback_kwargs))
    print(
        textwrap.indent(
            tabulate(
                [[exc_value]],
                headers=("Exception",),
                maxcolwidths=(term_width - two_borders - indent),
                **shared_kwargs,
            ),
            prefix=" " * indent,
        )
    )


# if auto_alignment_mode():  # defined in 00-startup.py
#     # Enable the auto-alignment mode.
#     # In this mode, the KB-mirror motors an optionally, toroidal mirror motors
#     # will be moved. For that to work, the I0 suspender will have to be disabled
#     # to avoid the interference with the mono feedback system
#     # (https://github.com/NSLS-II-TES/tes-horizontal-feedback).

#     try:
#         # Imports for bloptools < v0.0.2.
#         from bloptools.de_opt_utils import run_hardware_fly
#         from bloptools.de_optimization import optimization_plan
#     except (ImportError, ModuleNotFoundError):
#         _extract_tb()

#         print("\nFalling back to a newer version of bloptools...\n")
#         # The modules were moved to the `de` package in https://github.com/NSLS-II/bloptools/pull/5.
#         # To be released as v0.1.0 or newer.
#         try:
#             from bloptools import gp
#             from bloptools.de.de_opt_utils import run_hardware_fly
#             from bloptools.de.de_optimization import optimization_plan
#         except (ImportError, ModuleNotFoundError):
#             _extract_tb()
#             print(f"\nContinuing without bloptools...\n")

#     ###########################################################################
#     #                            DE optimization                              #
#     ###########################################################################

#     # motor_dict = {
#     #     sample_stage.x.name: {"position": sample_stage.x},
#     #     sample_stage.y.name: {"position": sample_stage.y},
#     #     # sample_stage.z.name: {'position': sample_stage.z},
#     # }

#     # bound_vals = [(43, 44), (34, 35)]
#     # motor_bounds = {}
#     # motor_dict_keys = list(motor_dict.keys())
#     # for k in range(len(motor_dict_keys)):
#     #     motor_bounds[motor_dict_keys[k]] = {"position": [bound_vals[k][0], bound_vals[k][1]]}

#     # instantiate plt.figure() before running optimization_plan
#     # import matplotlib.pyplot as plt
#     # plt.figure()

#     # Usage:
#     #
#     # RE(optimization_plan(fly_plan=run_hardware_fly, bounds=motor_bounds, db=db,
#     #                      motors=motor_dict, detector=xs, start_det=start_detector,
#     #                      read_det=read_detector, stop_det=stop_detector,
#     #                      watch_func=watch_function))

###########################################################################
#                            GP optimization                              #
###########################################################################


[0.1378487390625,
 0.10035915,
 2.5799511515624998,
 3.6510105187499997,
 -5.5692,
 -8.494,
 -9.58,
 -4.008]


dofs = [
    {"device": kbv.ush, "limits": 0.24 + 0.2 * np.array([-1.,1.]), "kind": "active", "tags": ["kb", "kbv"], "latent_group": "kbv"},
    {"device": kbv.dsh, "limits": 0.18 + 0.2 * np.array([-1.,1.]), "kind": "active", "tags": ["kb", "kbv"], "latent_group": "kbv"},
    {"device": kbh.ush, "limits": 2.67 + 0.2 * np.array([-1.,1.]), "kind": "active", "tags": ["kb", "kbh"], "latent_group": "kbh"},
    {"device": kbh.dsh, "limits": 3.75 + 0.2 * np.array([-1.,1.]), "kind": "active", "tags": ["kb", "kbh"], "latent_group": "kbh"},
    {"device": toroidal_mirror.usy, "limits": -5.569 + 0.5 * np.array([-1.,1.]), "kind": "active", "tags": ["toroid"]},
    {"device": toroidal_mirror.dsy, "limits": -8.494 + 0.5 * np.array([-1.,1.]), "kind": "active", "tags": ["toroid"]},
    {"device": toroidal_mirror.ush, "limits": -9.58 + 0.05 * np.array([-1.,1.]), "kind": "active", "tags": ["toroid"]},
    {"device": toroidal_mirror.dsh, "limits": -4.008 + 0.05 * np.array([-1.,1.]), "kind": "active", "tags": ["toroid"]},
]





from bloptools.bayesian import Agent
from bloptools.utils import get_beam_bounding_box, get_principal_component_bounds, best_image_feedback

tasks = [
    {"key": "I0", "kind": "maximize", "limits": (0.001, np.inf), "transform": "log"},
    {"key": "xw", "kind": "minimize", "transform": "log"},
    {"key": "yw", "kind": "minimize", "transform": "log"},
]

def tes_digestion(db, uid):

    products = db[uid].table(fill=True)

    for key in ["x0", "xw", "y0", "yw"]:
        products.loc[:, key] = np.nan

    BUFFER_PIXELS = 16

    for index, entry in products.iterrows():

        ny, nx = entry.vstream_image.shape

        x0, xw, y0, yw = best_image_feedback(entry.vstream_image)

        xmin, xmax = x0 - xw, x0 + xw
        ymin, ymax = y0 - yw, y0 + yw

        # products.loc[index, "xmin"] = xmin
        # products.loc[index, "xmax"] = xmax
        # products.loc[index, "ymin"] = ymin
        # products.loc[index, "ymax"] = ymax

        if ((xmin > BUFFER_PIXELS) 
            and (xmax < nx - BUFFER_PIXELS)
            and (ymin > BUFFER_PIXELS)
            and (ymax < ny - BUFFER_PIXELS)
        ):

            products.loc[index, "x0"] = x0
            products.loc[index, "xw"] = xw
            products.loc[index, "y0"] = y0
            products.loc[index, "yw"] = yw

    return products

bec.disable_plots()

agent = Agent(
            dofs=dofs, 
            tasks=tasks, 
            dets=[I0, vstream],
            digestion=tes_digestion,
            db=db,
            allow_acquisition_errors=False,
                )

agent.deactivate_dofs(tags=["kb", "toroid"])

agent.dofs[0]["mode"] = "on"
agent.dofs[1]["mode"] = "on"
agent.dofs[2]["mode"] = "on"
agent.dofs[3]["mode"] = "on"

agent.dofs[4]["mode"] = "on"
agent.dofs[5]["mode"] = "on"



#agent.activate_dofs(tags=["toroid"])

#agent.deactivate_dofs(tags=["kb"])
# gpo = gp.Optimizer(init_scheme='quasi-random', n_init=4, run_engine=RE, db=db, shutter=psh, detector=vstream, detector_type='image', dofs=dofs, dof_bounds=hard_bounds, fitness_model='max_sep_density', training_iter=256, verbose=True)

true_limits = {dof["name"]:dof["limits"] for dof in agent.dofs}

def benchmark(n=1):

    for i in range(n):

        try:

            RE(agent.go_to(agent._acq_func_bounds.mean(axis=0)))

            print("using dof limits:")
            for dof in agent._subset_dofs(mode="on"):
                dof["limits"] = true_limits[dof["name"]] + np.ptp(dof["limits"]) * np.random.uniform(low=-0.25, high=0.25)
                print(dof["limits"])

            agent.reset()

            RE(agent.go_to(agent._acq_func_bounds.mean(axis=0)))
            #agent.deactivate_dofs(tags=["kb", "toroid"])
            #agent.activate_dofs(tags=["kb"])

            RE(agent.initialize("qr", n_init=16, upsample=8))
            RE(agent.learn("em", n_iter=16, upsample=4))

            tag = str(int(ttime.time()))
            agent.save_data(f"/nsls2/data/tes/legacy/blop/run-tes-6dofs-{tag}.h5")

            if i == 0:
                agent.plot_history(show_all_tasks=True)

        except:
            continue
